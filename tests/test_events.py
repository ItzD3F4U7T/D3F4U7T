import unittest
from efc.events import TradeEvent


class TradeEventTests(unittest.TestCase):
    def test_valid_event(self) -> None:
        self.assertEqual(TradeEvent(0, 12345).price_ticks, 12345)

    def test_invalid_sequence(self) -> None:
        for value in (-1, True, 1.2, "1"):
            with self.subTest(value=value):
                with self.assertRaises((TypeError, ValueError)):
                    TradeEvent(value, 100)

    def test_invalid_price(self) -> None:
        for value in (0, -1):
            with self.assertRaises(ValueError):
                TradeEvent(0, value)
        for value in (True, 1.2, "100"):
            with self.assertRaises(TypeError):
                TradeEvent(0, value)


if __name__ == "__main__":
    unittest.main()
