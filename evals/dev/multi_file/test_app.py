from app import is_same_name, unique_names

def test_same_name():
    assert is_same_name("  Alice", "alice")

def test_unique():
    assert unique_names(["Bob", "bob ", " BOB"]) == ["bob"]
