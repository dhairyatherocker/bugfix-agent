from text import count_vowels

def test_mixed_case():
    assert count_vowels("Education") == 5

def test_none():
    assert count_vowels("xyz") == 0

def test_upper():
    assert count_vowels("AEIOU") == 5
