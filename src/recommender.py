from typing import List, Dict, Tuple, Optional
from dataclasses import dataclass

@dataclass
class Song:
    """
    Represents a song and its attributes.
    Required by tests/test_recommender.py
    """
    id: int
    title: str
    artist: str
    genre: str
    mood: str
    energy: float
    tempo_bpm: float
    valence: float
    danceability: float
    acousticness: float

@dataclass
class UserProfile:
    """
    Represents a user's taste preferences.
    Required by tests/test_recommender.py
    """
    favorite_genre: str
    favorite_mood: str
    target_energy: float
    likes_acoustic: bool

class Recommender:
    """
    OOP implementation of the recommendation logic.
    Required by tests/test_recommender.py
    """
    def __init__(self, songs: List[Song]):
        self.songs = songs

    def recommend(self, user: UserProfile, k: int = 5) -> List[Song]:
        def _score(song: Song) -> float:
            s = 0.0
            if song.genre == user.favorite_genre:
                s += 2.0
            if song.mood == user.favorite_mood:
                s += 1.0
            s += 1.5 * (1 - abs(song.energy - user.target_energy))
            if user.likes_acoustic:
                s += 0.75 * song.acousticness
            else:
                s += 0.75 * (1 - song.acousticness)
            return s

        return sorted(self.songs, key=_score, reverse=True)[:k]

    def explain_recommendation(self, user: UserProfile, song: Song) -> str:
        parts = []
        if song.genre == user.favorite_genre:
            parts.append(f"genre match ({song.genre})")
        if song.mood == user.favorite_mood:
            parts.append(f"mood match ({song.mood})")
        parts.append(f"energy {song.energy} vs target {user.target_energy}")
        acoustic_label = "acoustic" if user.likes_acoustic else "produced"
        parts.append(f"acousticness {song.acousticness} ({acoustic_label} preference)")
        return " · ".join(parts)

def load_songs(csv_path: str) -> List[Dict]:
    """Read songs.csv and return a list of dicts with numeric fields cast to float/int."""
    import csv

    songs = []
    with open(csv_path, newline="", encoding="utf-8") as f:
        reader = csv.DictReader(f)
        for row in reader:
            songs.append({
                "id":           int(row["id"]),
                "title":        row["title"],
                "artist":       row["artist"],
                "genre":        row["genre"],
                "mood":         row["mood"],
                "energy":       float(row["energy"]),
                "tempo_bpm":    float(row["tempo_bpm"]),
                "valence":      float(row["valence"]),
                "danceability": float(row["danceability"]),
                "acousticness": float(row["acousticness"]),
            })
    return songs

# ---------------------------------------------------------------------------
# EXPERIMENT: double energy weight, halve genre weight
# Max score changes: 2.0+1.0+1.5+1.0+0.75+0.75+0.5 = 7.5  (original)
#                   1.0+1.0+3.0+1.0+0.75+0.75+0.5 = 8.0  (experiment)
# To revert, comment the EXPERIMENT lines and uncomment the ORIGINAL lines.
# ---------------------------------------------------------------------------
#_W_GENRE        = 1.0   # EXPERIMENT: halved  — original: 2.0
_W_GENRE     = 2.0   # ORIGINAL
#_W_ENERGY       = 3.0   # EXPERIMENT: doubled — original: 1.50
_W_ENERGY     = 1.50  # ORIGINAL
_W_MOOD         = 1.0
_W_DANCEABILITY = 1.0
_W_VALENCE      = 0.75
_W_ACOUSTICNESS = 0.75
_W_TEMPO        = 0.50
# ---------------------------------------------------------------------------

def score_song(song: Dict, user_prefs: Dict) -> float:
    """Return a 0.0–8.0 match score: +genre, +1.0 mood, up to +6.0 numeric similarity."""
    score = 0.0

    # Categorical bonuses
    if song["genre"] == user_prefs["favorite_genre"]:
        score += _W_GENRE
    if song["mood"] == user_prefs["favorite_mood"]:
        score += _W_MOOD

    # Numeric similarity — each term is weight × (1 − absolute difference)
    score += _W_ENERGY       * (1 - abs(song["energy"]       - user_prefs["target_energy"]))
    score += _W_DANCEABILITY * (1 - abs(song["danceability"]  - user_prefs["target_danceability"]))
    score += _W_VALENCE      * (1 - abs(song["valence"]       - user_prefs["target_valence"]))
    score += _W_ACOUSTICNESS * (1 - abs(song["acousticness"]  - user_prefs["target_acousticness"]))

    # Normalize tempo to 0–1 before differencing (cap assumed at 200 BPM)
    tempo_norm   = song["tempo_bpm"]              / 200
    target_tempo = user_prefs["target_tempo_bpm"] / 200
    score += _W_TEMPO * (1 - abs(tempo_norm - target_tempo))

    return round(score, 4)


def _build_explanation(song: Dict, user_prefs: Dict) -> str:
    """Build a human-readable reason string listing categorical matches and key numeric targets."""
    parts = []
    if song["genre"] == user_prefs["favorite_genre"]:
        parts.append(f"genre match ({song['genre']})")
    if song["mood"] == user_prefs["favorite_mood"]:
        parts.append(f"mood match ({song['mood']})")
    parts.append(f"energy {song['energy']} vs target {user_prefs['target_energy']}")
    parts.append(f"danceability {song['danceability']} vs target {user_prefs['target_danceability']}")
    return " · ".join(parts)


def recommend_songs(user_prefs: Dict, songs: List[Dict], k: int = 5) -> List[Tuple[Dict, float, str]]:
    """Score all songs, sort by score descending, and return the top k as (song, score, explanation) tuples."""
    # Score every song with a list comprehension — Pythonic single-pass loop
    scored = [
        (song, score_song(song, user_prefs))
        for song in songs
    ]

    # sorted() returns a NEW list sorted by score descending.
    # We use this instead of .sort() to avoid mutating the original songs list.
    ranked = sorted(scored, key=lambda item: item[1], reverse=True)

    # Slice the top k, then attach an explanation string to each result
    return [
        (song, score, _build_explanation(song, user_prefs))
        for song, score in ranked[:k]
    ]
