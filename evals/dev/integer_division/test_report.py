from report import percentage

def test_quarter():
    assert percentage(1, 4) == 25.0

def test_third():
    assert percentage(1, 3) == 33.3

def test_zero_whole():
    assert percentage(5, 0) == 0.0
