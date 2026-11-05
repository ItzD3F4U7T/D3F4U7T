from __future__ import annotations
import random
import unittest
from fractions import Fraction
from efc.engine import EventDrivenEngine, ReferenceEngine, run_engine
from efc.events import TradeEvent
from efc.synthetic import generate_events


class EngineEquivalenceTests(unittest.TestCase):
    def compare_engines(self, prices: list[int], window: int) -> None:
        events = [TradeEvent(i, p) for i, p in enumerate(prices)]
        self.assertEqual(run_engine(ReferenceEngine(window), events),
                         run_engine(EventDrivenEngine(window), events))

    def test_hand_calculated_example(self) -> None:
        events = [TradeEvent(i, p) for i, p in enumerate([10, 12, 11, 13, 14, 15])]
        ref = run_engine(ReferenceEngine(3), events)
        inc = run_engine(EventDrivenEngine(3), events)
        self.assertEqual(ref, inc)
        self.assertEqual([x.average_ticks for x in ref],
                         [Fraction(10), Fraction(11), Fraction(11),
                          Fraction(12), Fraction(38, 3), Fraction(14)])

    def test_synthetic_streams_multiple_windows(self) -> None:
        events = list(generate_events(25_000, seed=7))
        for window in (1, 2, 3, 10, 50, 257):
            with self.subTest(window=window):
                self.assertEqual(run_engine(ReferenceEngine(window), events),
                                 run_engine(EventDrivenEngine(window), events))

    def test_random_streams(self) -> None:
        rng = random.Random(12345)
        for case in range(30):
            count, window = rng.randint(0, 300), rng.randint(1, 40)
            prices = [rng.randint(1, 1_000_000) for _ in range(count)]
            with self.subTest(case=case):
                self.compare_engines(prices, window)

    def test_warmup_and_rollover(self) -> None:
        engine = EventDrivenEngine(4)
        results = [engine.on_event(TradeEvent(i, p))
                   for i, p in enumerate([100, 200, 300, 400, 500])]
        self.assertEqual([x.samples for x in results], [1, 2, 3, 4, 4])
        self.assertEqual(results[-1].average_ticks, Fraction(350))

    def test_window_size_one(self) -> None:
        self.compare_engines([9, 2, 500, 7], 1)

    def test_empty_stream(self) -> None:
        for cls in (ReferenceEngine, EventDrivenEngine):
            self.assertEqual(run_engine(cls(5), []), [])

    def test_operation_reduction(self) -> None:
        events = list(generate_events(10_000, seed=9))
        ref, inc = ReferenceEngine(10), EventDrivenEngine(10)
        self.assertEqual(run_engine(ref, events), run_engine(inc, events))
        self.assertLess(inc.metrics.sum_arithmetic_operations,
                        ref.metrics.sum_arithmetic_operations)

    def test_operation_counter_formulas(self) -> None:
        n, w = 20, 4
        events = list(generate_events(n, seed=11))
        ref, inc = ReferenceEngine(w), EventDrivenEngine(w)
        self.assertEqual(run_engine(ref, events), run_engine(inc, events))
        warm, steady = min(n, w), max(0, n - w)
        self.assertEqual(ref.metrics.sum_additions,
                         warm * (warm - 1) // 2 + steady * (w - 1))
        self.assertEqual(inc.metrics.sum_additions, max(0, warm - 1) + steady)
        self.assertEqual(inc.metrics.sum_subtractions, steady)

    def test_reset(self) -> None:
        engine = EventDrivenEngine(3)
        engine.on_event(TradeEvent(10, 100))
        engine.on_event(TradeEvent(11, 200))
        engine.reset()
        result = engine.on_event(TradeEvent(0, 7))
        self.assertEqual(result.average_ticks, Fraction(7))
        self.assertEqual(engine.metrics.events_processed, 1)

    def test_rejects_duplicate_and_out_of_order(self) -> None:
        for cls in (ReferenceEngine, EventDrivenEngine):
            engine = cls(3)
            engine.on_event(TradeEvent(5, 100))
            with self.assertRaises(ValueError):
                engine.on_event(TradeEvent(5, 200))
            with self.assertRaises(ValueError):
                engine.on_event(TradeEvent(4, 200))

    def test_invalid_window_sizes(self) -> None:
        for value in (0, -1):
            with self.assertRaises(ValueError):
                EventDrivenEngine(value)
        for value in (True, 1.5, "10"):
            with self.assertRaises(TypeError):
                EventDrivenEngine(value)


if __name__ == "__main__":
    unittest.main()
