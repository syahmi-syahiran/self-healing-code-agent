def average(nums):
    """Return the mean of nums, or 0.0 for an empty list."""
    # BUG: divides by len(nums) with no guard, so [] raises ZeroDivisionError.
    return sum(nums) / len(nums)
