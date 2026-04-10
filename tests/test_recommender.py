import pytest
from src.recommender import (
    Song, UserProfile, Recommender,
    score_song, recommend_songs, _build_explanation,
)

def make_small_recommender() -> Recommender:
    songs = [
        Song(
            id=1,
            title="Test Pop Track",
            artist="Test Artist",
            genre="pop",
            mood="happy",
            energy=0.8,
            tempo_bpm=120,
            valence=0.9,
            danceability=0.8,
            acousticness=0.2,
        ),
        Song(
            id=2,
            title="Chill Lofi Loop",
            artist="Test Artist",
            genre="lofi",
            mood="chill",
            energy=0.4,
            tempo_bpm=80,
            valence=0.6,
            danceability=0.5,
            acousticness=0.9,
        ),
    ]
    return Recommender(songs)


def test_recommend_returns_songs_sorted_by_score():
    user = UserProfile(
        favorite_genre="pop",
        favorite_mood="happy",
        target_energy=0.8,
        likes_acoustic=False,
    )
    rec = make_small_recommender()
    results = rec.recommend(user, k=2)

    assert len(results) == 2
    # Starter expectation: the pop, happy, high energy song should score higher
    assert results[0].genre == "pop"
    assert results[0].mood == "happy"


def test_explain_recommendation_returns_non_empty_string():
    user = UserProfile(
        favorite_genre="pop",
        favorite_mood="happy",
        target_energy=0.8,
        likes_acoustic=False,
    )
    rec = make_small_recommender()
    song = rec.songs[0]

    explanation = rec.explain_recommendation(user, song)
    assert isinstance(explanation, str)
    assert explanation.strip() != ""


# ---------------------------------------------------------------------------
# Helpers for functional-API tests
# make_song / make_prefs let each test declare only what it cares about.
# ---------------------------------------------------------------------------

def make_song(**overrides) -> dict:
    base = {
        "id": 1, "title": "Test Song", "artist": "Test Artist",
        "genre": "pop", "mood": "happy",
        "energy": 0.80, "tempo_bpm": 120.0,
        "valence": 0.75, "danceability": 0.80, "acousticness": 0.20,
    }
    return {**base, **overrides}


def make_prefs(**overrides) -> dict:
    base = {
        "favorite_genre": "pop", "favorite_mood": "happy",
        "target_energy": 0.80, "target_valence": 0.75,
        "target_acousticness": 0.20, "target_danceability": 0.80,
        "target_tempo_bpm": 120.0,
    }
    return {**base, **overrides}


# ---------------------------------------------------------------------------
# score_song
# ---------------------------------------------------------------------------

def test_score_song_perfect_match_returns_max():
    # Song identical to every preference — all numeric diffs are 0, both
    # categorical bonuses fire: 2.0 + 1.0 + 1.5 + 1.0 + 0.75 + 0.75 + 0.5 = 7.50
    assert score_song(make_song(), make_prefs()) == pytest.approx(7.50)


def test_score_song_genre_match_adds_two_points():
    prefs = make_prefs(favorite_genre="pop")
    diff = score_song(make_song(genre="pop"), prefs) \
         - score_song(make_song(genre="rock"), prefs)
    assert diff == pytest.approx(2.0)


def test_score_song_mood_match_adds_one_point():
    prefs = make_prefs(favorite_mood="happy")
    diff = score_song(make_song(mood="happy"), prefs) \
         - score_song(make_song(mood="chill"), prefs)
    assert diff == pytest.approx(1.0)


def test_score_song_no_categorical_match_scores_numeric_only():
    # No genre or mood bonus; all numeric targets match exactly → 4.50
    song  = make_song(genre="metal", mood="angry")
    prefs = make_prefs(favorite_genre="pop", favorite_mood="happy")
    assert score_song(song, prefs) == pytest.approx(4.50)


def test_score_song_closer_energy_scores_higher():
    prefs      = make_prefs(target_energy=0.80)
    song_close = make_song(energy=0.82)   # diff 0.02
    song_far   = make_song(energy=0.50)   # diff 0.30
    assert score_song(song_close, prefs) > score_song(song_far, prefs)


def test_score_song_is_never_negative():
    # Worst case: no categorical match, every numeric attribute is opposite
    song  = make_song(genre="metal", mood="angry",
                      energy=0.0, danceability=0.0,
                      valence=0.0, acousticness=1.0, tempo_bpm=0.0)
    prefs = make_prefs(favorite_genre="pop", favorite_mood="happy",
                       target_energy=1.0, target_danceability=1.0,
                       target_valence=1.0, target_acousticness=0.0,
                       target_tempo_bpm=200.0)
    assert score_song(song, prefs) >= 0.0


def test_score_song_never_exceeds_max():
    assert score_song(make_song(), make_prefs()) <= 7.50


# ---------------------------------------------------------------------------
# recommend_songs
# ---------------------------------------------------------------------------

def test_recommend_songs_returns_exactly_k_results():
    songs   = [make_song(id=i) for i in range(10)]
    results = recommend_songs(make_prefs(), songs, k=3)
    assert len(results) == 3


def test_recommend_songs_sorted_descending_by_score():
    songs   = [make_song(id=i) for i in range(5)]
    results = recommend_songs(make_prefs(), songs, k=5)
    scores  = [score for _, score, _ in results]
    assert scores == sorted(scores, reverse=True)


def test_recommend_songs_best_match_ranked_first():
    prefs   = make_prefs(favorite_genre="pop", favorite_mood="happy")
    perfect = make_song(id=1, genre="pop",   mood="happy")
    poor    = make_song(id=2, genre="metal", mood="angry",
                        energy=0.0, danceability=0.0)
    results = recommend_songs(prefs, [poor, perfect], k=2)  # poor listed first
    assert results[0][0]["id"] == 1


def test_recommend_songs_result_shape():
    # Each element must be (dict, float, str)
    results = recommend_songs(make_prefs(), [make_song()], k=1)
    song, score, explanation = results[0]
    assert isinstance(song, dict)
    assert isinstance(score, float)
    assert isinstance(explanation, str)


# ---------------------------------------------------------------------------
# _build_explanation
# ---------------------------------------------------------------------------

def test_build_explanation_includes_genre_match_label():
    assert "genre match" in _build_explanation(
        make_song(genre="pop"), make_prefs(favorite_genre="pop")
    )


def test_build_explanation_omits_genre_match_when_different():
    assert "genre match" not in _build_explanation(
        make_song(genre="rock"), make_prefs(favorite_genre="pop")
    )


def test_build_explanation_includes_mood_match_label():
    assert "mood match" in _build_explanation(
        make_song(mood="happy"), make_prefs(favorite_mood="happy")
    )


def test_build_explanation_always_shows_energy():
    assert "energy" in _build_explanation(make_song(), make_prefs())


def test_build_explanation_always_shows_danceability():
    assert "danceability" in _build_explanation(make_song(), make_prefs())
