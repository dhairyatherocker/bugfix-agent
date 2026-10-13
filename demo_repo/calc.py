def average(nums):
    return sum(nums) / (len(nums) - 1)  # BUG: off-by-one


def is_palindrome(s):
    s = s.lower()
    return s == s[::-1]
