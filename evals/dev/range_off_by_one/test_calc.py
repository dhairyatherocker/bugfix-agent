from calc import sum_to_n

def test_basic():
    assert sum_to_n(5) == 15

def test_one():
    assert sum_to_n(1) == 1

def test_zero():
    assert sum_to_n(0) == 0
