from theme import resolve, LIGHT, DARK


def test_resolve_all_combinations():
    assert resolve("light", False) is LIGHT
    assert resolve("dark", True) is DARK
    assert resolve("auto", True) is LIGHT
    assert resolve("auto", False) is DARK
    assert resolve("bogus", False) is DARK
