"""
End-to-end evaluation script for Music4u.

Run from project root:
    python tests/eval.py

Tests the full pipeline: NL input → Claude parse → scoring → Claude eval.
Each test case checks both algorithmic correctness and Claude's own judgment.
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
            # reggae not in catalog — system should still return 5 results
            "min_results": 5,
        },
    },
]


def _avg(songs: list, field: str) -> float:
    return sum(s[field] for s in songs) / len(songs)


def run_eval(use_claude: bool = True) -> tuple[int, int]:
    songs = load_songs(SONGS_CSV)
    passed = 0
    failed = 0

    # Conditional Claude imports
    if use_claude:
        try:
            from llm import parse_user_input, evaluate_recommendations
            claude_ok = True
        except Exception as e:
            print(f"[WARN] Claude unavailable: {e}. Running algorithmic-only checks.")
            claude_ok = False
    else:
        claude_ok = False

    for case in TEST_CASES:
        print(f"\n{'=' * 54}")
        print(f"  Test : {case['id']}")
        print(f"  Query: \"{case['query']}\"")

        try:
            # --- Parse prefs (Claude or fallback) ---
            if claude_ok:
                prefs = parse_user_input(case["query"])
            else:
                prefs = _fallback_prefs(case["query"])

            # --- Score catalog ---
            results = recommend_songs(prefs, songs, k=5)
            top_songs = [s for s, _, _ in results]
            scores = [sc for _, sc, _ in results]

            print(f"  Top  : {[s['title'] for s in top_songs]}")
            print(f"  Score: {[round(sc, 2) for sc in scores]}")

            # --- Run checks ---
            errors: list[str] = []
            checks = case["checks"]

            if "min_results" in checks and len(results) < checks["min_results"]:
                errors.append(f"expected ≥{checks['min_results']} results, got {len(results)}")

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
                    errors.append(
                        f"top result genre '{top_genre}' not in {checks['expected_genres']}"
                    )

            if "expected_moods" in checks:
                top_mood = top_songs[0]["mood"]
                if top_mood not in checks["expected_moods"]:
                    errors.append(
                        f"top result mood '{top_mood}' not in {checks['expected_moods']}"
                    )

            # --- Claude evaluation ---
            if claude_ok:
                eval_result = evaluate_recommendations(case["query"], top_songs[:3])
                claude_verdict = f"Claude eval: pass={eval_result.get('pass')} | {eval_result.get('reason', '')}"
            else:
                claude_verdict = "Claude eval: skipped"

            if errors:
                print(f"  FAIL : {'; '.join(errors)}")
                print(f"  {claude_verdict}")
                failed += 1
            else:
                print(f"  PASS")
                print(f"  {claude_verdict}")
                passed += 1

        except Exception as e:
            print(f"  ERROR: {e}")
            failed += 1

    print(f"\n{'=' * 54}")
    print(f"  Results: {passed}/{passed + failed} passed")
    return passed, failed


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


if __name__ == "__main__":
    use_claude = "--no-claude" not in sys.argv
    run_eval(use_claude=use_claude)
