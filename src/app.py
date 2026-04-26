"""
Music4u — AI-powered music recommender
Run: streamlit run src/app.py
"""
import sys
import os
import time
from datetime import datetime

# Make src/ importable regardless of where streamlit is launched from
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

try:
    from dotenv import load_dotenv
    load_dotenv()
except ImportError:
    pass

import streamlit as st
from recommender import load_songs, recommend_songs

SONGS_CSV = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "data", "songs.csv")
MAX_SCORE = 7.5  # genre(2) + mood(1) + energy(1.5) + dance(1) + valence(0.75) + acoustic(0.75) + tempo(0.5)

# ---------------------------------------------------------------------------
# Claude integration (graceful fallback if key not set)
# ---------------------------------------------------------------------------
CLAUDE_AVAILABLE = False
try:
    from llm import parse_user_input, generate_explanations, evaluate_recommendations
    CLAUDE_AVAILABLE = bool(os.getenv("ANTHROPIC_API_KEY"))
except Exception:
    pass

from logger import get_logger, log_event

# ---------------------------------------------------------------------------
# Page config — MUST be first Streamlit call
# ---------------------------------------------------------------------------
st.set_page_config(
    page_title="Music4u",
    page_icon="🎵",
    layout="centered",
    initial_sidebar_state="collapsed",
)

# ---------------------------------------------------------------------------
# CSS
# ---------------------------------------------------------------------------
CSS = """
<style>
/* ── reset & background ─────────────────────────────────────────────────── */
#MainMenu, footer, header { visibility: hidden; }
body, .stApp {
    background-color: #0a0a0f;
    color: #e2e8f0;
    font-family: 'Inter', -apple-system, BlinkMacSystemFont, sans-serif;
}
section[data-testid="stMain"] > div { padding-top: 3rem !important; }
.block-container { max-width: 760px; padding: 2rem 1.5rem 3rem; }

/* ── input ──────────────────────────────────────────────────────────────── */
.stTextInput input {
    background: rgba(255,255,255,0.05) !important;
    border: 1px solid rgba(124,58,237,0.4) !important;
    border-radius: 12px !important;
    color: #0a0a0f !important;
    font-size: 16px !important;
    padding: 14px 18px !important;
    caret-color: #7c3aed;
    transition: border-color 0.3s, box-shadow 0.3s !important;
}
.stTextInput input:focus {
    border-color: rgba(124,58,237,0.85) !important;
    box-shadow: 0 0 0 3px rgba(124,58,237,0.2) !important;
}
.stTextInput input::placeholder { color: #4a4a6a !important; }
.stTextInput label { display: none !important; }

/* ── button ─────────────────────────────────────────────────────────────── */
.stFormSubmitButton > button, .stButton > button {
    width: 100% !important;
    background: linear-gradient(135deg, #7c3aed, #06b6d4) !important;
    color: white !important;
    border: none !important;
    border-radius: 12px !important;
    padding: 14px 32px !important;
    font-weight: 700 !important;
    font-size: 15px !important;
    letter-spacing: 0.5px !important;
    cursor: pointer !important;
    animation: btnPulse 3s ease-in-out infinite !important;
    transition: transform 0.2s, box-shadow 0.2s !important;
}
.stFormSubmitButton > button:hover, .stButton > button:hover {
    transform: translateY(-2px) !important;
    box-shadow: 0 8px 28px rgba(124,58,237,0.45) !important;
}
@keyframes btnPulse {
    0%, 100% { box-shadow: 0 4px 18px rgba(124,58,237,0.3); }
    50%       { box-shadow: 0 4px 28px rgba(124,58,237,0.55); }
}

/* ── waveform bars ───────────────────────────────────────────────────────── */
@keyframes wave {
    0%, 100% { transform: scaleY(0.35); }
    50%       { transform: scaleY(1.5); }
}
.m4u-wave-bar {
    display: inline-block;
    width: 5px;
    height: 36px;
    border-radius: 3px;
    background: linear-gradient(to top, #7c3aed, #06b6d4);
    margin: 0 2px;
    transform-origin: bottom;
    animation: wave 1.3s ease-in-out infinite;
}

/* ── card animations ─────────────────────────────────────────────────────── */
@keyframes slideUp {
    from { opacity: 0; transform: translateY(22px); }
    to   { opacity: 1; transform: translateY(0); }
}
.m4u-card {
    background: linear-gradient(135deg, rgba(16,16,30,0.95), rgba(20,20,40,0.95));
    border: 1px solid rgba(124,58,237,0.22);
    border-radius: 16px;
    padding: 20px 24px;
    margin: 12px 0;
    opacity: 0;
    animation: slideUp 0.55s ease forwards;
    transition: border-color 0.3s, box-shadow 0.3s;
}
.m4u-card:hover {
    border-color: rgba(124,58,237,0.5);
    box-shadow: 0 8px 36px rgba(124,58,237,0.14);
}

/* ── score bar ───────────────────────────────────────────────────────────── */
@keyframes fillBar {
    from { transform: scaleX(0); }
    to   { transform: scaleX(1); }
}
.m4u-track {
    height: 6px;
    background: rgba(255,255,255,0.08);
    border-radius: 4px;
    overflow: hidden;
    margin: 8px 0;
}
.m4u-fill-wrap {
    height: 100%;
    overflow: hidden;
}
.m4u-fill {
    height: 100%;
    width: 100%;
    transform-origin: left;
    border-radius: 4px;
    background: linear-gradient(90deg, #7c3aed, #06b6d4);
    animation: fillBar 1.1s ease forwards;
    transform: scaleX(0);
}

/* ── tags & badges ───────────────────────────────────────────────────────── */
.m4u-tag {
    display: inline-block;
    padding: 3px 10px;
    border-radius: 20px;
    font-size: 11px;
    font-weight: 600;
    text-transform: uppercase;
    letter-spacing: 0.4px;
    margin-right: 5px;
}
.m4u-genre { background: rgba(124,58,237,0.18); color: #a78bfa; border: 1px solid rgba(124,58,237,0.3); }
.m4u-mood  { background: rgba(6,182,212,0.14);  color: #67e8f9; border: 1px solid rgba(6,182,212,0.3); }
.m4u-badge {
    display: inline-block;
    padding: 2px 9px;
    border-radius: 20px;
    font-size: 10px;
    font-weight: 700;
    letter-spacing: 0.3px;
    margin-left: 8px;
    vertical-align: middle;
}
.m4u-pass    { background: rgba(16,185,129,0.14); color: #34d399; border: 1px solid rgba(16,185,129,0.3); }
.m4u-rerank  { background: rgba(245,158,11,0.14); color: #fbbf24; border: 1px solid rgba(245,158,11,0.3); }
.m4u-fallback{ background: rgba(107,114,128,0.14); color: #9ca3af; border: 1px solid rgba(107,114,128,0.3); }

/* ── status message ──────────────────────────────────────────────────────── */
.m4u-status {
    text-align: center;
    color: #94a3b8;
    font-size: 15px;
    padding: 24px 0;
    letter-spacing: 0.3px;
}

/* ── divider ─────────────────────────────────────────────────────────────── */
hr { border-color: rgba(124,58,237,0.15) !important; margin: 24px 0 !important; }

/* ── alert / info ────────────────────────────────────────────────────────── */
.stAlert { border-radius: 12px !important; }
</style>
"""

st.markdown(CSS, unsafe_allow_html=True)


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

@st.cache_resource
def _get_songs():
    return load_songs(SONGS_CSV)


def _loosen_prefs(prefs: dict) -> dict:
    """Move numeric targets 20% toward 0.5 to broaden catalog matches."""
    loosened = dict(prefs)
    for key in ("target_energy", "target_valence", "target_danceability", "target_acousticness"):
        loosened[key] = loosened[key] + 0.2 * (0.5 - loosened[key])
    return loosened


def _fallback_parse(query: str) -> dict:
    """Keyword-based fallback when Claude is unavailable."""
    q = query.lower()
    if any(w in q for w in ("chill", "lofi", "study", "relax", "calm", "focus")):
        return {"favorite_genre": "lofi",  "favorite_mood": "chill",
                "target_energy": 0.35, "target_valence": 0.55,
                "target_acousticness": 0.75, "target_danceability": 0.5,
                "target_tempo_bpm": 78}
    if any(w in q for w in ("intense", "angry", "metal", "workout", "rage", "hard")):
        return {"favorite_genre": "metal", "favorite_mood": "angry",
                "target_energy": 0.95, "target_valence": 0.20,
                "target_acousticness": 0.05, "target_danceability": 0.6,
                "target_tempo_bpm": 165}
    if any(w in q for w in ("sad", "melancholy", "acoustic", "rain", "cry", "heartbreak")):
        return {"favorite_genre": "folk",  "favorite_mood": "sad",
                "target_energy": 0.35, "target_valence": 0.25,
                "target_acousticness": 0.85, "target_danceability": 0.35,
                "target_tempo_bpm": 70}
    # default: happy pop
    return {"favorite_genre": "pop",   "favorite_mood": "happy",
            "target_energy": 0.75, "target_valence": 0.70,
            "target_acousticness": 0.15, "target_danceability": 0.80,
            "target_tempo_bpm": 115}


def _waveform_html(bars: int = 7) -> str:
    delays = [0.0, 0.12, 0.24, 0.36, 0.48, 0.36, 0.24][:bars]
    bar_tags = "".join(
        f'<div class="m4u-wave-bar" style="animation-delay:{d:.2f}s"></div>'
        for d in delays
    )
    return f'<div style="text-align:center;margin-bottom:6px">{bar_tags}</div>'


def _card_html(rank: int, song: dict, score: float, explanation: str,
               badge: str, delay: float) -> str:
    score_pct = round((score / MAX_SCORE) * 100, 1)
    badge_map = {
        "pass":     ('<span class="m4u-badge m4u-pass">✓ AI Verified</span>', ""),
        "rerank":   ('<span class="m4u-badge m4u-rerank">↻ Re-ranked</span>', ""),
        "fallback": ('<span class="m4u-badge m4u-fallback">⚡ Algorithmic</span>', ""),
    }
    badge_html, _ = badge_map.get(badge, ("", ""))

    return f"""
<div class="m4u-card" style="animation-delay:{delay:.2f}s">
  <div style="display:flex;justify-content:space-between;align-items:flex-start;margin-bottom:10px">
    <div style="display:flex;align-items:center;gap:14px">
      <span style="font-size:30px;font-weight:800;background:linear-gradient(135deg,#7c3aed,#06b6d4);
                   -webkit-background-clip:text;-webkit-text-fill-color:transparent;line-height:1">
        #{rank}
      </span>
      <div>
        <div style="font-size:17px;font-weight:700;color:#e2e8f0;margin-bottom:2px">{song['title']}</div>
        <div style="font-size:13px;color:#94a3b8">{song['artist']}</div>
      </div>
    </div>
    <div style="text-align:right;white-space:nowrap">
      <span style="font-size:18px;font-weight:700;color:#e2e8f0">{score:.2f}</span>
      <span style="font-size:12px;color:#4a4a6a"> / {MAX_SCORE}</span>
      {badge_html}
    </div>
  </div>
  <div style="margin-bottom:10px">
    <span class="m4u-tag m4u-genre">{song['genre']}</span>
    <span class="m4u-tag m4u-mood">{song['mood']}</span>
  </div>
  <div class="m4u-track">
    <div class="m4u-fill-wrap" style="width:{score_pct}%">
      <div class="m4u-fill" style="animation-delay:{delay + 0.15:.2f}s"></div>
    </div>
  </div>
  <div style="font-size:13px;color:#8892a4;line-height:1.65;margin-top:12px;font-style:italic">
    "{explanation}"
  </div>
</div>
"""


# ---------------------------------------------------------------------------
# Pipeline
# ---------------------------------------------------------------------------

def run_pipeline(query: str, songs: list, logger) -> dict:
    """
    Full recommendation pipeline:
      1. NL parse  (Claude or fallback keyword matching)
      2. Score + retrieve (scoring engine)
      3. RAG explain (Claude uses retrieved song features)
      4. Agentic eval (Claude checks own recommendations)
      5. Optional re-rank if eval fails
    """
    result = {
        "user_prefs": None,
        "results": [],
        "explanations": [],
        "eval": {"pass": True, "reason": ""},
        "reranked": False,
        "claude_used": CLAUDE_AVAILABLE,
        "error": None,
    }

    try:
        # Step 1 — Parse
        if CLAUDE_AVAILABLE:
            result["user_prefs"] = parse_user_input(query, logger)
        else:
            result["user_prefs"] = _fallback_parse(query)
        log_event(logger, "PREFS", result["user_prefs"])

        # Step 2 — Score & retrieve
        raw_results = recommend_songs(result["user_prefs"], songs, k=5)
        top_songs = [s for s, _, _ in raw_results]
        scores = [sc for _, sc, _ in raw_results]
        fallback_exps = [ex for _, _, ex in raw_results]

        # Step 3 — RAG explanations
        if CLAUDE_AVAILABLE:
            result["explanations"] = generate_explanations(query, top_songs, logger)
        else:
            result["explanations"] = fallback_exps

        # Step 4 — Agentic evaluation
        if CLAUDE_AVAILABLE:
            eval_result = evaluate_recommendations(query, top_songs, logger)
            result["eval"] = eval_result

            # Step 5 — Re-rank if eval fails
            if not eval_result.get("pass", True):
                log_event(logger, "RERANK_TRIGGER", {"reason": eval_result.get("reason")})
                loosened = _loosen_prefs(result["user_prefs"])
                raw_results = recommend_songs(loosened, songs, k=5)
                top_songs = [s for s, _, _ in raw_results]
                scores = [sc for _, sc, _ in raw_results]
                result["explanations"] = generate_explanations(query, top_songs, logger)
                result["eval"] = evaluate_recommendations(query, top_songs, logger)
                result["reranked"] = True
                log_event(logger, "RERANKED", {"new_top": top_songs[0]["title"]})

        # Pack results
        result["results"] = list(zip(top_songs, scores))

    except Exception as e:
        logger.error(f"PIPELINE_ERROR | {e}")
        result["error"] = str(e)
        # Hard fallback — run pure algorithmic mode
        try:
            prefs = _fallback_parse(query)
            raw_results = recommend_songs(prefs, songs, k=5)
            result["results"] = [(s, sc) for s, sc, _ in raw_results]
            result["explanations"] = [ex for _, _, ex in raw_results]
            result["claude_used"] = False
        except Exception as e2:
            logger.error(f"FALLBACK_ERROR | {e2}")

    return result


# ---------------------------------------------------------------------------
# UI
# ---------------------------------------------------------------------------

songs = _get_songs()

# ── Header ────────────────────────────────────────────────────────────────
st.markdown(_waveform_html(), unsafe_allow_html=True)
st.markdown(
    """
    <div style="text-align:center;padding:0 0 28px">
      <h1 style="font-size:2.8rem;font-weight:800;margin:0;
                 background:linear-gradient(135deg,#7c3aed,#06b6d4);
                 -webkit-background-clip:text;-webkit-text-fill-color:transparent">
        Music4u
      </h1>
      <p style="color:#64748b;font-size:15px;margin-top:6px">
        Describe your vibe — we'll find your perfect soundtrack
      </p>
    </div>
    """,
    unsafe_allow_html=True,
)

if not CLAUDE_AVAILABLE:
    st.markdown(
        """
        <style>
          #m4u-chk { display:none }
          #m4u-chk:checked ~ #m4u-panel { display:block !important }
          #m4u-info-wrap label { cursor:pointer }
          #m4u-info-wrap label:hover { transform:scale(1.08); box-shadow:0 6px 22px rgba(124,58,237,0.6) !important }
        </style>
        <div id="m4u-info-wrap" style="
            position:fixed;bottom:22px;right:22px;z-index:9999;
            font-family:'Inter',-apple-system,BlinkMacSystemFont,sans-serif;
            display:flex;flex-direction:column;align-items:flex-end">
          <input type="checkbox" id="m4u-chk">
          <div id="m4u-panel" style="
              display:none;
              background:rgba(12,12,24,0.97);
              border:1px solid rgba(124,58,237,0.35);
              border-radius:14px;
              padding:16px 18px;
              margin-bottom:10px;
              max-width:270px;
              font-size:12.5px;
              color:#94a3b8;
              line-height:1.65;
              box-shadow:0 8px 32px rgba(0,0,0,0.5)">
            <div style="color:#a78bfa;font-weight:700;margin-bottom:6px;font-size:13px">
              ⚡ Algorithmic Mode
            </div>
            <div>
              <code style="color:#e2e8f0;background:rgba(255,255,255,0.07);
                           padding:1px 5px;border-radius:4px">ANTHROPIC_API_KEY</code>
              not set — running on the scoring engine only.<br><br>
              Add your key to <code style="color:#e2e8f0;background:rgba(255,255,255,0.07);
              padding:1px 5px;border-radius:4px">.env</code> for full Claude-powered
              NL parsing, explanations &amp; agentic eval.
            </div>
          </div>
          <label for="m4u-chk" title="API status" style="
              width:40px;height:40px;border-radius:50%;
              background:linear-gradient(135deg,#7c3aed,#06b6d4);
              border:none;color:white;font-size:17px;
              box-shadow:0 4px 16px rgba(124,58,237,0.45);
              display:flex;align-items:center;justify-content:center;
              transition:transform 0.2s,box-shadow 0.2s;
              user-select:none">
            ℹ
          </label>
        </div>
        """,
        unsafe_allow_html=True,
    )

# ── Input form ────────────────────────────────────────────────────────────
with st.form("rec_form", clear_on_submit=False):
    query = st.text_input(
        "query",
        placeholder='Try "chill lofi for studying" or "hype songs for a workout"…',
        label_visibility="collapsed",
    )
    submitted = st.form_submit_button("✦  Get My Recommendations")

# ── Pipeline ──────────────────────────────────────────────────────────────
if submitted and query.strip():
    session_id = datetime.now().strftime("%Y%m%d_%H%M%S")
    logger = get_logger(session_id)
    log_event(logger, "SESSION_START", {"query": query, "claude": CLAUDE_AVAILABLE})

    status = st.empty()

    def update(msg: str):
        status.markdown(f'<div class="m4u-status">{msg}</div>', unsafe_allow_html=True)

    update("🎧&nbsp; Parsing your vibe…")
    if CLAUDE_AVAILABLE:
        time.sleep(0.1)

    update("🎵&nbsp; Searching the catalog…")
    pipeline_result = run_pipeline(query, songs, logger)

    if CLAUDE_AVAILABLE:
        update("✨&nbsp; Crafting personalized explanations…")
        time.sleep(0.2)
        update("🤖&nbsp; Running quality check…")
        time.sleep(0.15)

    if pipeline_result.get("reranked"):
        update("🔄&nbsp; Re-ranking for better matches…")
        time.sleep(0.2)

    status.empty()

    # ── Results ───────────────────────────────────────────────────────────
    if pipeline_result["error"] and not pipeline_result["results"]:
        st.error(f"Something went wrong: {pipeline_result['error']}")
    else:
        eval_passed = pipeline_result["eval"].get("pass", True)
        reranked = pipeline_result["reranked"]
        claude_used = pipeline_result["claude_used"]

        # Summary bar
        eval_reason = pipeline_result["eval"].get("reason", "")
        if claude_used:
            if reranked:
                note = f"🔄 Re-ranked — {eval_reason}"
                color = "#f59e0b"
            elif eval_passed:
                note = f"✓ AI Verified — {eval_reason}" if eval_reason else "✓ AI Verified"
                color = "#34d399"
            else:
                note = f"⚡ Showing best matches — {eval_reason}"
                color = "#94a3b8"
        else:
            note = "⚡ Algorithmic recommendations — add your API key for AI-powered results"
            color = "#6b7280"

        st.markdown(
            f'<div style="text-align:center;color:{color};font-size:13px;'
            f'padding:8px 0 18px;font-weight:500">{note}</div>',
            unsafe_allow_html=True,
        )
        st.markdown("<hr>", unsafe_allow_html=True)

        # Determine badge for each card
        if not claude_used:
            badge = "fallback"
        elif reranked:
            badge = "rerank"
        else:
            badge = "pass"

        # Render cards
        results = pipeline_result["results"]
        explanations = pipeline_result["explanations"]

        # Pad explanations if needed
        while len(explanations) < len(results):
            explanations.append("A great pick for your vibe.")

        cards_html = "".join(
            _card_html(
                rank=i + 1,
                song=song,
                score=score,
                explanation=explanations[i] if i < len(explanations) else "A great pick.",
                badge=badge,
                delay=i * 0.1,
            )
            for i, (song, score) in enumerate(results)
        )
        st.markdown(cards_html, unsafe_allow_html=True)

        log_event(logger, "SESSION_END", {
            "top_song": results[0][0]["title"] if results else "none",
            "reranked": reranked,
            "badge": badge,
        })

elif submitted and not query.strip():
    st.warning("Please type something to describe your vibe!")

# ── Footer ────────────────────────────────────────────────────────────────
st.markdown(
    """
    <div style="text-align:center;color:#2d2d4a;font-size:12px;padding:32px 0 8px">
        Music4u · Powered by Claude · 18 tracks · Applied AI Final Project
    </div>
    """,
    unsafe_allow_html=True,
)
