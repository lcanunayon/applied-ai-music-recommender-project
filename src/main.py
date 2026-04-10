"""
Command line runner for the Music Recommender Simulation.

This file helps you quickly run and test your recommender.

You will implement the functions in recommender.py:
- load_songs
- score_song
- recommend_songs
"""

from src.recommender import load_songs, recommend_songs


# ---------------------------------------------------------------------------
# Standard User Preference Profiles
# Each dict maps to the keys expected by score_song() in recommender.py.
# The extra "label" key is only used for display — score_song ignores it.
# ---------------------------------------------------------------------------

HIGH_ENERGY_POP = {
    "label":               "High-Energy Pop",
    # Categorical (each match gives a bonus: +2.0 genre, +1.0 mood)
    "favorite_genre":      "pop",
    "favorite_mood":       "happy",
    # Numeric targets (0.0-1.0) — closer to song values = higher score
    "target_energy":       0.85,   # wants driving, upbeat songs
    "target_valence":      0.75,   # mostly positive emotional tone
    "target_acousticness": 0.10,   # prefers produced/electronic over acoustic
    "target_danceability": 0.88,   # strong preference for groovy, rhythmic tracks
    # Tempo in BPM — normalized to 0-1 inside score_song (cap: 200 BPM)
    "target_tempo_bpm":    110,    # mid-to-fast tempo sweet spot
}

CHILL_LOFI = {
    "label":               "Chill Lofi",
    "favorite_genre":      "lofi",
    "favorite_mood":       "chill",
    "target_energy":       0.35,   # low-key, background listening
    "target_valence":      0.55,   # neutral-to-warm emotional tone
    "target_acousticness": 0.80,   # loves warm, organic textures
    "target_danceability": 0.55,   # gentle groove, not a dance floor
    "target_tempo_bpm":    75,     # slow, laid-back tempo
}

DEEP_INTENSE_ROCK = {
    "label":               "Deep Intense Rock",
    "favorite_genre":      "rock",
    "favorite_mood":       "intense",
    "target_energy":       0.92,   # high-voltage energy is a must
    "target_valence":      0.30,   # darker, heavier emotional tone
    "target_acousticness": 0.08,   # fully amplified — no acoustic here
    "target_danceability": 0.60,   # rhythmic but not pop-groovy
    "target_tempo_bpm":    155,    # fast, aggressive tempo
}


# ---------------------------------------------------------------------------
# Adversarial / Edge-Case Profiles
# These are designed to stress-test the scoring logic and reveal unexpected
# behavior. Each comment explains the specific tension being introduced.
# ---------------------------------------------------------------------------

# Edge Case 1 — Conflicting energy vs. mood
# energy=0.9 (pulls toward metal/rock) but mood="sad" and genre="folk"
# (categorical bonuses pull toward "Candle and Rain").
# Watch: does the +2.0 genre / +1.0 mood bonus override the large energy
# distance penalty for folk songs? A folk/sad song (energy ≈ 0.31) will
# lose ~0.89 × 1.5 = 1.34 pts on energy alone but gain 3.0 from categories.
CONFLICTED_SOUL = {
    "label":               "[EDGE] Conflicted Soul — high energy + sad mood",
    "favorite_genre":      "folk",
    "favorite_mood":       "sad",
    "target_energy":       0.90,   # contradicts a typical folk/sad listener
    "target_valence":      0.20,   # low positivity (consistent with sad mood)
    "target_acousticness": 0.85,   # consistent with folk
    "target_danceability": 0.40,
    "target_tempo_bpm":    68,
}

# Edge Case 2 — Genre completely absent from the dataset
# "ska" matches no song, so the +2.0 genre bonus NEVER fires.
# Tests whether numeric-only scoring still produces sensible rankings or
# whether the recommender silently degrades to noise.
UNKNOWN_GENRE_FAN = {
    "label":               "[EDGE] Unknown Genre — 'ska' not in dataset",
    "favorite_genre":      "ska",
    "favorite_mood":       "happy",
    "target_energy":       0.75,
    "target_valence":      0.80,
    "target_acousticness": 0.20,
    "target_danceability": 0.85,
    "target_tempo_bpm":    130,
}

# Edge Case 3 — All numeric targets at 0.5 (perfect middle)
# Every song is "equally mediocre" for numeric similarity.
# The categorical bonuses (+2.0 genre, +1.0 mood) become the ONLY
# differentiator. Do genre/mood matches dominate the rankings? Is
# the ordering between non-matching songs stable?
PERFECTLY_AVERAGE = {
    "label":               "[EDGE] Perfectly Average — all numeric targets = 0.5",
    "favorite_genre":      "pop",
    "favorite_mood":       "happy",
    "target_energy":       0.50,
    "target_valence":      0.50,
    "target_acousticness": 0.50,
    "target_danceability": 0.50,
    "target_tempo_bpm":    100,    # 100/200 = 0.5 normalized
}

# Edge Case 4 — Extreme maximalist (all targets pushed to their limits)
# target_tempo_bpm=200 hits the normalization ceiling (200/200 = 1.0).
# Only "Iron Curtain" (metal, angry, energy=0.97, tempo=178) is anywhere
# close. Checks whether the scoring function handles boundary values
# gracefully and whether one song dominates by a wide margin.
EXTREME_MAXIMALIST = {
    "label":               "[EDGE] Extreme Maximalist — all targets at ceiling",
    "favorite_genre":      "metal",
    "favorite_mood":       "angry",
    "target_energy":       1.00,
    "target_valence":      0.00,
    "target_acousticness": 0.00,
    "target_danceability": 1.00,
    "target_tempo_bpm":    200,    # at the 200 BPM normalization cap
}

# Edge Case 5 — Acoustic Beast (high energy + high acousticness)
# Almost no song in the 18-track dataset is BOTH highly energetic AND
# highly acoustic. The scorer has to find the least-bad compromise.
# Tests whether the recommender surfaces a reasonable "closest match"
# or returns wildly inconsistent results when the preference is a unicorn.
ACOUSTIC_BEAST = {
    "label":               "[EDGE] Acoustic Beast — high energy + high acousticness",
    "favorite_genre":      "folk",
    "favorite_mood":       "intense",
    "target_energy":       0.88,   # wants loud and raw
    "target_valence":      0.45,
    "target_acousticness": 0.95,   # but fully acoustic — very rare combo
    "target_danceability": 0.65,
    "target_tempo_bpm":    140,
}


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def print_recommendations(user_prefs: dict, songs: list, k: int = 5) -> None:
    """Run the recommender for one profile and pretty-print the results."""
    recommendations = recommend_songs(user_prefs, songs, k=k)
    label = user_prefs.get("label", user_prefs["favorite_genre"])

    print("\n" + "=" * 58)
    print(f"  Profile : {label}")
    print(f"  Genre   : {user_prefs['favorite_genre']}  |  Mood: {user_prefs['favorite_mood']}")
    print("=" * 58)

    for rank, (song, score, explanation) in enumerate(recommendations, start=1):
        print(f"\n#{rank}  {song['title']}  —  {song['artist']}")
        print(f"    Score  : {score:.2f} / 7.50")
        print(f"    Genre  : {song['genre']}  |  Mood: {song['mood']}")
        print(f"    Why    : {explanation}")

    print()


# ---------------------------------------------------------------------------
# Main entry point
# ---------------------------------------------------------------------------

def main() -> None:
    songs = load_songs("data/songs.csv")
    print(f"Loaded {len(songs)} songs.\n")

    # --- Standard profiles ---
    print("=" * 58)
    print("  STANDARD PROFILES")
    print("=" * 58)

    for profile in [HIGH_ENERGY_POP, CHILL_LOFI, DEEP_INTENSE_ROCK]:
        print_recommendations(profile, songs)

    # --- Adversarial / edge-case profiles ---
    print("\n" + "#" * 58)
    print("  ADVERSARIAL / EDGE-CASE PROFILES")
    print("  (designed to stress-test scoring logic)")
    print("#" * 58)

    for profile in [
        CONFLICTED_SOUL,
        UNKNOWN_GENRE_FAN,
        PERFECTLY_AVERAGE,
        EXTREME_MAXIMALIST,
        ACOUSTIC_BEAST,
    ]:
        print_recommendations(profile, songs)


if __name__ == "__main__":
    main()
