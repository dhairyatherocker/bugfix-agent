def is_adult(age):
    """18 or older counts as an adult."""
    return age > 18


def can_vote(age, citizen):
    return is_adult(age) and citizen
