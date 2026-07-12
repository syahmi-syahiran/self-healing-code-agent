def is_palindrome(s):
    """Return True if s reads the same forwards and backwards."""
    # BUG: uses != so it returns True only for NON-palindromes.
    return s != s[::-1]
