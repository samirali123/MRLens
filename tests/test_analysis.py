from analysis.user_signals import classify_comp
from analysis.enemy_signals import aggregate_enemy_vulnerabilities
from analysis.meta_signals import compute_personal_vs_community_delta


def test_classify_comp_dive():
    assert classify_comp(["Spider-Man", "Black Panther", "Luna Snow"]) == "dive"


def test_classify_comp_mixed():
    assert classify_comp(["Hawkeye", "Hulk", "Loki"]) == "mixed"


def test_aggregate_vulnerabilities():
    weakness_map = {
        "PlayerA": {"worst_heroes": [{"hero": "Storm", "games": 10, "win_rate": 0.3}], "best_heroes": []},
        "PlayerB": {"worst_heroes": [{"hero": "Storm", "games": 8, "win_rate": 0.35}, {"hero": "Thor", "games": 5, "win_rate": 0.4}], "best_heroes": []},
    }
    result = aggregate_enemy_vulnerabilities(weakness_map)
    assert result["Storm"] == 2
    assert result.get("Thor") == 1


def test_personal_vs_community_delta():
    personal = {"Storm": {"win_rate": 0.68, "games": 23}}
    community = {"Storm": {"win_rate": 0.51, "pick_rate": 0.08}}
    result = compute_personal_vs_community_delta(personal, community)
    assert abs(result["Storm"]["delta"] - 0.17) < 0.001
    assert result["Storm"]["community"] == 0.51
