from solution import is_palindrome


def main():
    assert is_palindrome("racecar") is True, "racecar"
    assert is_palindrome("level") is True, "level"
    assert is_palindrome("hello") is False, "hello"
    assert is_palindrome("") is True, "empty"
    print("OK")


if __name__ == "__main__":
    main()
