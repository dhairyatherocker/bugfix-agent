from search import binary_search

def test_found():
    assert binary_search([1, 3, 5, 7], 7) == 3
    assert binary_search([1, 3, 5, 7], 1) == 0

def test_single():
    assert binary_search([5], 5) == 0

def test_missing():
    assert binary_search([1, 3], 4) == -1
