from solution import average


def main():
    assert average([2, 4, 6]) == 4.0, average([2, 4, 6])
    assert average([10]) == 10.0, average([10])
    assert average([]) == 0.0, "empty list should return 0.0"
    print("OK")


if __name__ == "__main__":
    main()
