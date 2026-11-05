import unittest
from efc.synthetic import generate_events


class SyntheticDataTests(unittest.TestCase):
    def test_reproducible(self) -> None:
        self.assertEqual(list(generate_events(100, seed=42)),
                         list(generate_events(100, seed=42)))

    def test_sequences_and_positive_prices(self) -> None:
        events = list(generate_events(500))
        self.assertEqual([e.sequence for e in events], list(range(500)))
        self.assertTrue(all(e.price_ticks > 0 for e in events))

    def test_zero_count(self) -> None:
        self.assertEqual(list(generate_events(0)), [])

    def test_invalid_count(self) -> None:
        with self.assertRaises(ValueError):
            list(generate_events(-1))
        with self.assertRaises(TypeError):
            list(generate_events(True))


if __name__ == "__main__":
    unittest.main()
