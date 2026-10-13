def percentage(part, whole):
    """Percentage of whole, rounded to 1 decimal place. 0.0 if whole is 0."""
    if whole == 0:
        return 0.0
    return (part // whole) * 100
