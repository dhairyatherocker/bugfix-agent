from text_utils import normalize


def is_same_name(a, b):
    return normalize(a) == normalize(b)


def unique_names(names):
    seen, out = set(), []
    for n in names:
        key = normalize(n)
        if key not in seen:
            seen.add(key)
            out.append(key)
    return out
