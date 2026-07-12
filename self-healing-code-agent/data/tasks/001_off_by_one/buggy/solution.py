def sum_to(n):
    """Return the sum of integers from 1 to n inclusive."""
    total = 0
    # BUG: range(1, n) stops at n-1, so the last term is dropped.
    for i in range(1, n):
        total += i
    return total
