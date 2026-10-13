from voting import is_adult, can_vote

def test_boundary():
    assert is_adult(18)

def test_minor():
    assert not is_adult(17)

def test_vote():
    assert can_vote(18, True)
    assert not can_vote(30, False)
