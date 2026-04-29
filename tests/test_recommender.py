from llm.recommender import _parse_hero_names


def test_parse_hero_names():
    response = """1. Storm — Great personal WR and strong vs dive.
2. Spider-Man — Exploits 3/6 enemies who struggle against him.
3. Thor — Best map win rate on Tokyo 2099 at Gold."""
    heroes = _parse_hero_names(response)
    assert heroes == ["Storm", "Spider-Man", "Thor"]


def test_parse_hero_names_empty():
    assert _parse_hero_names("No recommendations available.") == []
