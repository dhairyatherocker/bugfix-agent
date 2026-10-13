from calc import average, is_palindrome

def test_average():
    assert average([2, 4, 6]) == 4

def test_palindrome():
    assert is_palindrome("Racecar")
