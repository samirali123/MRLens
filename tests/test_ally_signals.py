from analysis.user_signals import classify_comp


def test_classify_comp_dive_heavy():
    allies = ["Spider-Man", "Black Panther", "Wolverine", "Luna Snow"]
    assert classify_comp(allies) == "dive"


def test_classify_comp_mixed_allies():
    allies = ["Thor", "Hawkeye", "Luna Snow"]
    assert classify_comp(allies) == "mixed"


def test_classify_comp_brawl():
    allies = ["Hulk", "Thor", "Captain America", "Groot"]
    assert classify_comp(allies) == "brawl"
