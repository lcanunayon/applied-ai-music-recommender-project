import os
import re
import json
import time
import logging
import anthropic

_PROFILES_PATH = os.path.join(os.path.dirname(__file__), "..", "data", "genre_profiles.json")
_profiles_cache: dict | None = None

_client: anthropic.Anthropic | None = None

# ---------------------------------------------------------------------------
# System prompts (static — eligible for prompt caching)
# ---------------------------------------------------------------------------

PARSE_SYSTEM = """You are a music preference parser. Convert a natural language music request into structured JSON preferences.

Output ONLY valid JSON with these exact keys:
{
  "favorite_genre": string — pick the closest from: pop, lofi, rock, ambient, jazz, synthwave, indie pop, classical, hip-hop, r&b, country, metal, latin, folk, dream pop,
  "favorite_mood": string — pick the closest from: happy, chill, intense, focused, relaxed, moody, melancholic, hype, romantic, nostalgic, angry, uplifting, sad, dreamy,
  "target_energy": float 0.0–1.0,
  "target_valence": float 0.0–1.0,
  "target_acousticness": float 0.0–1.0,
  "target_danceability": float 0.0–1.0,
  "target_tempo_bpm": integer 60–200
}

Infer reasonable values for any preferences not explicitly stated. Return ONLY the JSON object, no explanation, no markdown fences."""

EXPLAIN_SYSTEM = """You are a friendly, enthusiastic music recommendation assistant. Given a user's request and retrieved songs with their audio features, write a short 1–2 sentence explanation for why each song fits. Be specific, casual, and fun. Reference actual features from the song data (energy, mood, tempo, etc.)."""

EVAL_SYSTEM = """You are a music recommendation quality evaluator. Given a user's request and the recommended songs, judge whether the recommendations are a good fit.

Respond with ONLY this JSON (no markdown, no extra text):
{
  "pass": boolean,
  "confidence": float 0.0–1.0,
  "reason": string — one concise sentence
}"""

RATE_SYSTEM = """You are evaluating the quality of a single music recommendation explanation.

Score it 1–10 using these criteria:
- Specificity: does it reference actual song features (energy, tempo, mood, genre)?
- Relevance: does it clearly connect to what the user asked for?
- Helpfulness: would it give the user a real reason to want to listen?

Respond with ONLY this JSON (no markdown, no extra text):
{"score": integer 1-10, "reason": "one sentence"}"""


def _get_client() -> anthropic.Anthropic:
    global _client
    if _client is None:
        _client = anthropic.Anthropic()
    return _client


def _load_profiles() -> dict:
    global _profiles_cache
    if _profiles_cache is None:
        try:
            with open(_PROFILES_PATH, encoding="utf-8") as f:
                _profiles_cache = json.load(f)
        except Exception:
            _profiles_cache = {"genres": {}, "moods": {}}
    return _profiles_cache


def _build_profile_context(top_songs: list) -> str:
    """Return genre/mood profile text for the unique genres and moods present in top_songs."""
    profiles = _load_profiles()
    seen_genres: dict[str, str] = {}
    seen_moods: dict[str, str] = {}
    for s in top_songs:
        g, m = s["genre"], s["mood"]
        if g not in seen_genres and g in profiles["genres"]:
            seen_genres[g] = profiles["genres"][g]["description"]
        if m not in seen_moods and m in profiles["moods"]:
            seen_moods[m] = profiles["moods"][m]["description"]
    lines = [f"Genre '{g}': {d}" for g, d in seen_genres.items()]
    lines += [f"Mood '{m}': {d}" for m, d in seen_moods.items()]
    return "\n".join(lines)


def parse_user_input(text: str, logger: logging.Logger | None = None) -> dict:
    """Parse natural language into a structured user preferences dict."""
    t0 = time.time()
    client = _get_client()

    msg = client.messages.create(
        model="claude-haiku-4-5-20251001",
        max_tokens=300,
        system=[{"type": "text", "text": PARSE_SYSTEM, "cache_control": {"type": "ephemeral"}}],
        messages=[{"role": "user", "content": text}],
    )
    raw = msg.content[0].text.strip()
    raw = _strip_fences(raw)
    prefs = json.loads(raw)

    if logger:
        from logger import log_event
        log_event(logger, "PARSE", {
            "input": text,
            "prefs": prefs,
            "latency_ms": round((time.time() - t0) * 1000),
            "cache_read": msg.usage.cache_read_input_tokens,
        })
    return prefs


def generate_explanations(
    user_query: str,
    top_songs: list,
    logger: logging.Logger | None = None,
    enrich: bool = True,
) -> list[str]:
    """RAG step: generate Claude explanations using retrieved song context.

    When enrich=True, genre/mood profiles from genre_profiles.json are injected
    into the context before Claude generates explanations (enhanced RAG).
    """
    t0 = time.time()
    client = _get_client()

    songs_ctx = "\n".join([
        f"{i+1}. \"{s['title']}\" by {s['artist']} — genre: {s['genre']}, mood: {s['mood']}, "
        f"energy: {s['energy']}, danceability: {s['danceability']}, tempo: {s['tempo_bpm']} BPM, "
        f"valence: {s['valence']}"
        for i, s in enumerate(top_songs)
    ])

    if enrich:
        profile_ctx = _build_profile_context(top_songs)
        if profile_ctx:
            songs_ctx = (
                f"Genre & mood reference (use this to write more informed explanations):\n"
                f"{profile_ctx}\n\n"
                f"Retrieved songs:\n{songs_ctx}"
            )

    prompt = (
        f'User request: "{user_query}"\n\n'
        f"Retrieved context:\n{songs_ctx}\n\n"
        f"Write a numbered explanation for each song in the same order. "
        f"Each should be 1–2 sentences referencing the song's actual features."
    )

    msg = client.messages.create(
        model="claude-haiku-4-5-20251001",
        max_tokens=700,
        system=[{"type": "text", "text": EXPLAIN_SYSTEM, "cache_control": {"type": "ephemeral"}}],
        messages=[{"role": "user", "content": prompt}],
    )
    raw = msg.content[0].text.strip()

    if logger:
        from logger import log_event
        log_event(logger, "EXPLAIN", {
            "songs": [s["title"] for s in top_songs],
            "latency_ms": round((time.time() - t0) * 1000),
            "cache_read": msg.usage.cache_read_input_tokens,
        })

    return _parse_numbered_list(raw, len(top_songs))


def evaluate_recommendations(
    user_query: str,
    top_songs: list,
    logger: logging.Logger | None = None,
) -> dict:
    """Agentic step: Claude self-evaluates the recommendations."""
    t0 = time.time()
    client = _get_client()

    songs_summary = ", ".join([
        f'"{s["title"]}" ({s["genre"]}, {s["mood"]}, energy={s["energy"]})'
        for s in top_songs
    ])
    prompt = f'User request: "{user_query}"\nRecommended: {songs_summary}\n\nAre these a good fit?'

    try:
        msg = client.messages.create(
            model="claude-haiku-4-5-20251001",
            max_tokens=150,
            system=[{"type": "text", "text": EVAL_SYSTEM, "cache_control": {"type": "ephemeral"}}],
            messages=[{"role": "user", "content": prompt}],
        )
        raw = _strip_fences(msg.content[0].text.strip())
        result = json.loads(raw)

        if logger:
            from logger import log_event
            log_event(logger, "EVAL", {
                "pass": result.get("pass"),
                "confidence": result.get("confidence"),
                "reason": result.get("reason"),
                "latency_ms": round((time.time() - t0) * 1000),
            })
        return result
    except Exception as e:
        if logger:
            logger.warning(f"EVAL_PARSE_FAILED | {e}")
        return {"pass": True, "confidence": 0.5, "reason": "Evaluation unavailable"}


def rate_explanation_quality(
    user_query: str,
    song: dict,
    explanation: str,
) -> dict:
    """Ask Claude to score a single explanation 1–10 for specificity, relevance, helpfulness."""
    client = _get_client()
    prompt = (
        f'User request: "{user_query}"\n'
        f'Song: "{song["title"]}" by {song["artist"]} ({song["genre"]}, {song["mood"]}, '
        f'energy={song["energy"]}, tempo={song["tempo_bpm"]} BPM)\n'
        f'Explanation: "{explanation}"\n\n'
        f"Rate this explanation."
    )
    try:
        msg = client.messages.create(
            model="claude-haiku-4-5-20251001",
            max_tokens=100,
            system=[{"type": "text", "text": RATE_SYSTEM, "cache_control": {"type": "ephemeral"}}],
            messages=[{"role": "user", "content": prompt}],
        )
        raw = _strip_fences(msg.content[0].text.strip())
        return json.loads(raw)
    except Exception:
        return {"score": 5, "reason": "Rating unavailable"}


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _strip_fences(text: str) -> str:
    """Remove markdown code fences if Claude wraps its response in them."""
    text = text.strip()
    if text.startswith("```"):
        parts = text.split("```")
        # parts[1] is the content between first pair of fences
        content = parts[1] if len(parts) > 1 else text
        content = re.sub(r"^json\s*", "", content)
        return content.strip()
    return text


def _parse_numbered_list(text: str, n: int) -> list[str]:
    """Extract n numbered items from Claude's response."""
    items = re.split(r"\n\s*\d+[.)]\s+", text)
    # First split item may be empty if text starts with "1."
    items = [item.strip() for item in items if item.strip()]
    # If no numbered split happened, try line splitting
    if len(items) < n:
        lines = [l.strip() for l in text.split("\n") if l.strip()]
        cleaned = []
        for line in lines:
            stripped = re.sub(r"^\d+[.)]\s+", "", line).strip()
            if stripped:
                cleaned.append(stripped)
        items = cleaned if len(cleaned) >= len(items) else items
    while len(items) < n:
        items.append("A solid pick for your vibe.")
    return items[:n]
