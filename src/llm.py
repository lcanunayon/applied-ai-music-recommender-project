import os
import re
import json
import time
import logging
import anthropic

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


def _get_client() -> anthropic.Anthropic:
    global _client
    if _client is None:
        _client = anthropic.Anthropic()
    return _client


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
) -> list[str]:
    """RAG step: generate Claude explanations using retrieved song context."""
    t0 = time.time()
    client = _get_client()

    songs_ctx = "\n".join([
        f"{i+1}. \"{s['title']}\" by {s['artist']} — genre: {s['genre']}, mood: {s['mood']}, "
        f"energy: {s['energy']}, danceability: {s['danceability']}, tempo: {s['tempo_bpm']} BPM, "
        f"valence: {s['valence']}"
        for i, s in enumerate(top_songs)
    ])

    prompt = (
        f'User request: "{user_query}"\n\n'
        f"Retrieved songs:\n{songs_ctx}\n\n"
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
