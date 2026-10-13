from stats import average_length

def test_normal():
    assert average_length(["ab", "abcd"]) == 3

def test_empty():
    assert average_length([]) == 0
