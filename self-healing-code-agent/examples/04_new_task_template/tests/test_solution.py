from solution import fizzbuzz


def main():
    assert fizzbuzz(1) == "1", fizzbuzz(1)
    assert fizzbuzz(3) == "Fizz", fizzbuzz(3)
    assert fizzbuzz(5) == "Buzz", fizzbuzz(5)
    assert fizzbuzz(15) == "FizzBuzz", fizzbuzz(15)
    print("OK")


if __name__ == "__main__":
    main()
