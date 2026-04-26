"""
End-to-end evaluation script for Music4u.

Run from project root:
    python tests/eval.py              # full eval with Claude
    python tests/eval.py --no-claude  # algorithmic-only checks
    python tests/eval.py --rag-only   # run RAG comparison section only

Output:
  - Pass/fail + confidence rating per test case
  - RAG quality comparison: baseline (song features only) vs enhanced (+ genre/mood profiles)
"""
import sys
import os

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "src"))

from recommender import load_songs, recommend_songs

SONGS_CSV = os.path.join(os.path.dirname(__file__), "..", "data", "songs.csv")

TEST_CASES = [
    {
        "id": "upbeat_pop_party",
        "query": "upbeat pop music to dance to at a party",
        "checks": {
            "expected_genres": ["pop", "latin", "hip-hop", "r&b"],
            "min_energy": 0.55,
            "min_danceability": 0.55,
        },
    },
    {
        "id": "chill_lofi_study",
        "query": "chill lofi music for studying late at night",
        "checks": {
            "expected_genres": ["lofi", "ambient", "classical", "jazz"],
            "max_energy": 0.55,
        },
    },
    {
        "id": "intense_workout",
        "query": "angry intense music for an intense workout",
        "checks": {
            "expected_genres": ["metal", "rock"],
            "min_energy": 0.7,
        },
    },
    {
        "id": "sad_acoustic_rainy",
        "query": "sad acoustic songs for a rainy day",
        "checks": {
            "min_acousticness": 0.45,
            "expected_moods": ["sad", "melancholic", "moody", "nostalgic"],
        },
    },
    {
        "id": "unknown_genre_graceful",
        "query": "reggae music with good vibes",
        "checks": {
            "min_results": 5,
        },
    },
]

# Queries used for the RAG quality comparison (no Claude parse needed — prefs are inline)
RAG_COMPARISON_CASES = [
    {
        "query": "chill lofi music for studying late at night",
        "prefs": {
            "favorite_genre": "lofi", "favorite_mood": "chill",
            "target_energy": 0.35, "target_valence": 0.55,
            "target_acousticness": 0.80, "target_danceability": 0.55,
            "target_tempo_bpm": 75,
        },
    },
    {
        "query": "angry intense music for a heavy workout",
        "prefs": {
            "favorite_genre": "metal", "favorite_mood": "angry",
            "target_energy": 0.95, "target_valence": 0.20,
            "target_acousticness": 0.05, "target_danceability": 0.60,
            "target_tempo_bpm": 160,
        },
    },
    {
        "query": "upbeat pop songs for a party",
        "prefs": {
            "favorite_genre": "pop", "favorite_mood": "happy",
            "target_energy": 0.85, "target_valence": 0.80,
            "target_acousticness": 0.10, "target_danceability": 0.88,
            "target_tempo_bpm": 115,
        },
    },
]


def _avg(songs: list, field: str) -> float:
    return sum(s[field] for s in songs) / len(songs)


def _bar(score: float, total: int = 10, width: int = 20) -> str:
    filled = round((score / total) * width)
    return "#" * filled + "." * (width - filled)


def _fallback_prefs(query: str) -> dict:
    q = query.lower()
    if any(w in q for w in ["chill", "lofi", "study", "relax", "calm"]):
        return {"favorite_genre": "lofi", "favorite_mood": "chill",
                "target_energy": 0.35, "target_valence": 0.55,
                "target_acousticness": 0.7, "target_danceability": 0.5,
                "target_tempo_bpm": 80}
    if any(w in q for w in ["hype", "party", "dance", "pop", "upbeat"]):
        return {"favorite_genre": "pop", "favorite_mood": "happy",
                "target_energy": 0.8, "target_valence": 0.75,
                "target_acousticness": 0.1, "target_danceability": 0.85,
                "target_tempo_bpm": 120}
    if any(w in q for w in ["intense", "angry", "metal", "workout", "rage"]):
        return {"favorite_genre": "metal", "favorite_mood": "angry",
                "target_energy": 0.95, "target_valence": 0.2,
                "target_acousticness": 0.05, "target_danceability": 0.6,
                "target_tempo_bpm": 160}
    return {"favorite_genre": "pop", "favorite_mood": "chill",
            "target_energy": 0.5, "target_valence": 0.5,
            "target_acousticness": 0.5, "target_danceability": 0.5,
            "target_tempo_bpm": 100}


# ---------------------------------------------------------------------------
# Main eval loop
# ---------------------------------------------------------------------------

def run_eval(use_claude: bool = True) -> tuple[int, int]:
    songs = load_songs(SONGS_CSV)
    passed = 0
    failed = 0
    confidence_scores: list[float] = []

    claude_ok = False
    if use_claude:
        try:
            from llm import parse_user_input, evaluate_recommendations
            claude_ok = True
        except Exception as e:
            print(f"[WARN] Claude unavailable: {e}. Running algorithmic-only checks.")

    for case in TEST_CASES:
        print(f"\n{'-' * 54}")
        print(f"  Test  : {case['id']}")
        print(f"  Query : \"{case['query']}\"")

        try:
            prefs = parse_user_input(case["query"]) if claude_ok else _fallback_prefs(case["query"])

            results = recommend_songs(prefs, songs, k=5)
            top_songs = [s for s, _, _ in results]
            scores    = [sc for _, sc, _ in results]

            print(f"  Top   : {[s['title'] for s in top_songs]}")
            print(f"  Scores: {[round(sc, 2) for sc in scores]}")

            errors: list[str] = []
            checks = case["checks"]

            if "min_results" in checks and len(results) < checks["min_results"]:
                errors.append(f"expected >={checks['min_results']} results, got {len(results)}")
            if "min_energy" in checks:
                avg = _avg(top_songs, "energy")
                if avg < checks["min_energy"]:
                    errors.append(f"avg energy {avg:.2f} < {checks['min_energy']}")
            if "max_energy" in checks:
                avg = _avg(top_songs, "energy")
                if avg > checks["max_energy"]:
                    errors.append(f"avg energy {avg:.2f} > {checks['max_energy']}")
            if "min_danceability" in checks:
                avg = _avg(top_songs, "danceability")
                if avg < checks["min_danceability"]:
                    errors.append(f"avg danceability {avg:.2f} < {checks['min_danceability']}")
            if "min_acousticness" in checks:
                avg = _avg(top_songs, "acousticness")
                if avg < checks["min_acousticness"]:
                    errors.append(f"avg acousticness {avg:.2f} < {checks['min_acousticness']}")
            if "expected_genres" in checks:
                top_genre = top_songs[0]["genre"]
                if top_genre not in checks["expected_genres"]:
                    errors.append(f"top genre '{top_genre}' not in {checks['expected_genres']}")
            if "expected_moods" in checks:
                top_mood = top_songs[0]["mood"]
                if top_mood not in checks["expected_moods"]:
                    errors.append(f"top mood '{top_mood}' not in {checks['expected_moods']}")

            if claude_ok:
                eval_result = evaluate_recommendations(case["query"], top_songs[:3])
                confidence  = eval_result.get("confidence", 0.5)
                confidence_scores.append(confidence)
                verdict = (
                    f"  Claude: pass={eval_result.get('pass')} | "
                    f"confidence={confidence:.0%} {_bar(confidence * 10)} | "
                    f"{eval_result.get('reason', '')}"
                )
            else:
                verdict = "  Claude: skipped (no API key)"

            if errors:
                print(f"  FAIL  : {'; '.join(errors)}")
                failed += 1
            else:
                print(f"  PASS")
                passed += 1
            print(verdict)

        except Exception as e:
            print(f"  ERROR : {e}")
            failed += 1

    print(f"\n{'=' * 54}")
    print(f"  Algorithmic checks : {passed}/{passed + failed} passed")
    if confidence_scores:
        avg_conf = sum(confidence_scores) / len(confidence_scores)
        print(f"  Avg Claude confidence : {avg_conf:.0%} {_bar(avg_conf * 10)}")
    print(f"{'=' * 54}")

    return passed, failed


# ---------------------------------------------------------------------------
# RAG quality comparison
# ---------------------------------------------------------------------------

def run_rag_comparison() -> None:
    """
    Demonstrates measurable RAG improvement.

    For each sample query, runs generate_explanations twice:
      - Baseline : song features only (enrich=False)
      - Enhanced : song features + genre/mood profiles (enrich=True)

    Claude rates each top-song explanation 1–10. The delta shows improvement.
    """
    if not os.getenv("ANTHROPIC_API_KEY"):
        print("\n[SKIP] RAG comparison requires ANTHROPIC_API_KEY - skipped.")
        return
    try:
        from llm import generate_explanations, rate_explanation_quality
    except Exception as e:
        print(f"\n[SKIP] RAG comparison import failed: {e}")
        return

    songs = load_songs(SONGS_CSV)

    print(f"\n{'=' * 54}")
    print("  RAG QUALITY COMPARISON")
    print("  Baseline  = song features only")
    print("  Enhanced  = song features + genre/mood profiles")
    print(f"{'=' * 54}")

    total_baseline = 0
    total_enhanced = 0

    for case in RAG_COMPARISON_CASES:
        results   = recommend_songs(case["prefs"], songs, k=3)
        top_songs = [s for s, _, _ in results]
        top_song  = top_songs[0]

        baseline_exps = generate_explanations(case["query"], top_songs, enrich=False)
        enhanced_exps = generate_explanations(case["query"], top_songs, enrich=True)

        b_rating = rate_explanation_quality(case["query"], top_song, baseline_exps[0])
        e_rating = rate_explanation_quality(case["query"], top_song, enhanced_exps[0])

        b_score = b_rating.get("score", 5)
        e_score = e_rating.get("score", 5)
        delta   = e_score - b_score
        total_baseline += b_score
        total_enhanced += e_score

        print(f"\n  Query   : \"{case['query']}\"")
        print(f"  Song    : \"{top_song['title']}\" ({top_song['genre']}, {top_song['mood']})")
        print(f"  Baseline [{b_score}/10] {_bar(b_score)}")
        print(f"    \"{baseline_exps[0][:90]}{'…' if len(baseline_exps[0]) > 90 else ''}\"")
        print(f"  Enhanced [{e_score}/10] {_bar(e_score)}")
        print(f"    \"{enhanced_exps[0][:90]}{'…' if len(enhanced_exps[0]) > 90 else ''}\"")
        sign = "+" if delta >= 0 else ""
        print(f"  Delta   : {sign}{delta} pts — {e_rating.get('reason', '')}")

    n = len(RAG_COMPARISON_CASES)
    avg_b = total_baseline / n
    avg_e = total_enhanced / n
    avg_d = avg_e - avg_b

    print(f"\n{'-' * 54}")
    print(f"  Avg baseline score : {avg_b:.1f}/10  {_bar(avg_b)}")
    print(f"  Avg enhanced score : {avg_e:.1f}/10  {_bar(avg_e)}")
    sign = "+" if avg_d >= 0 else ""
    print(f"  Overall delta      : {sign}{avg_d:.1f} pts across {n} queries")
    print(f"{'=' * 54}")


# ---------------------------------------------------------------------------
# Entry point
# ---------------------------------------------------------------------------

if __name__ == "__main__":
    rag_only   = "--rag-only"   in sys.argv
    no_claude  = "--no-claude"  in sys.argv

    if rag_only:
        run_rag_comparison()
    else:
        run_eval(use_claude=not no_claude)
        run_rag_comparison()
