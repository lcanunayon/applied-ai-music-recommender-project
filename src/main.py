"""
Command line runner for the Music Recommender Simulation.

This file helps you quickly run and test your recommender.

You will implement the functions in recommender.py:
- load_songs
- score_song
- recommend_songs
"""

from src.recommender import load_songs, recommend_songs


def main() -> None:
    songs = load_songs("data/songs.csv")
    print(f"Loaded songs: {len(songs)}")

    # Full taste profile — target values used for similarity scoring
    user_prefs = {
        # Categorical preferences (used for bonus matching, not distance math)
        "favorite_genre": "hip-hop",
        "favorite_mood":  "hype",

        # Numeric targets (0.0 – 1.0 scale, used in score_song distance formula)
        "target_energy":       0.85,  # high energy — prefers upbeat, driving songs
        "target_valence":      0.75,  # mostly positive/happy emotional tone
        "target_acousticness": 0.10,  # prefers produced/electronic over acoustic
        "target_danceability": 0.88,  # strong preference for groovy, rhythmic tracks

        # Tempo stored in BPM — normalize to 0–1 inside score_song before scoring
        "target_tempo_bpm":    110,   # mid-to-fast tempo sweet spot
    }

    recommendations = recommend_songs(user_prefs, songs, k=5)

    print("\nTop recommendations:\n")
    for rec in recommendations:
        # You decide the structure of each returned item.
        # A common pattern is: (song, score, explanation)
        song, score, explanation = rec
        print(f"{song['title']} - Score: {score:.2f}")
        print(f"Because: {explanation}")
        print()


if __name__ == "__main__":
    main()
