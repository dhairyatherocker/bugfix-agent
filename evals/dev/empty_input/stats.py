def average_length(words):
    """Average word length; 0 for an empty list."""
    return sum(len(w) for w in words) / len(words)
