import random
import unittest
from fractions import Fraction
from efc.stage2 import (EventDrivenFeatureEngine, MarketEvent,
                        ReferenceFeatureEngine, replay)


class Stage2Tests(unittest.TestCase):
    def compare(self, events, window=5):
        a = replay(ReferenceFeatureEngine(window), events)
        b = replay(EventDrivenFeatureEngine(window), events)
        self.assertEqual(a, b)

    def test_hand_calculated_trade_and_book_features(self):
        events = [
            MarketEvent(0, 100, 2, 99, 101, 10, 5),
            MarketEvent(1, 102, 3),
            MarketEvent(2, 101, 4, 100, 103, 4, 8),
        ]
        out = replay(EventDrivenFeatureEngine(3), events)
        self.assertEqual(out[0].rolling_mean_ticks, Fraction(100))
        self.assertEqual(out[0].rolling_variance_ticks_squared, Fraction(0))
        self.assertEqual(out[0].rolling_volume, 2)
        self.assertEqual(out[0].book_imbalance, Fraction(1, 3))
        self.assertEqual(out[0].spread_ticks, 2)
        self.assertEqual(out[1].price_change_ticks, 2)
        self.assertEqual(out[2].price_change_ticks, -1)
        self.assertEqual(out[2].rolling_mean_ticks, Fraction(101))
        self.assertEqual(out[2].rolling_variance_ticks_squared, Fraction(2, 3))
        self.assertEqual(out[2].rolling_volume, 9)
        self.assertEqual(out[2].book_imbalance, Fraction(-1, 3))
        self.assertEqual(out[2].spread_ticks, 3)

    def test_random_mixed_streams_exact_equivalence(self):
        rng = random.Random(20261106)
        for case in range(100):
            events = []
            seq = 0
            price = 100_000
            for _ in range(rng.randint(1, 500)):
                kind = rng.randrange(3)
                if kind in (0, 2):
                    price = max(1, price + rng.randint(-5, 5))
                    if kind == 2:
                        events.append(MarketEvent(seq, price, rng.randint(1, 50),
                                                  99_999, 100_001,
                                                  rng.randint(1, 100), rng.randint(1, 100)))
                    else:
                        events.append(MarketEvent(seq, price, rng.randint(1, 50)))
                else:
                    bid_size, ask_size = rng.randint(1, 100), rng.randint(1, 100)
                    events.append(MarketEvent(seq, bid_price_ticks=99_999,
                                              ask_price_ticks=100_001,
                                              bid_size=bid_size, ask_size=ask_size))
                seq += 1
            for window in (1, 2, 7, 32):
                with self.subTest(case=case, window=window):
                    self.compare(events, window)

    def test_trade_only_does_not_update_book_feature_group(self):
        engine = EventDrivenFeatureEngine(4)
        engine.on_event(MarketEvent(0, 100, 1))
        engine.on_event(MarketEvent(1, 101, 1))
        self.assertEqual(engine.metrics.trade_payload_events, 2)
        self.assertEqual(engine.metrics.book_payload_events, 0)

    def test_book_only_does_not_update_trade_feature_group(self):
        engine = EventDrivenFeatureEngine(4)
        engine.on_event(MarketEvent(0, bid_price_ticks=99, ask_price_ticks=101,
                                    bid_size=10, ask_size=8))
        self.assertEqual(engine.metrics.trade_payload_events, 0)
        self.assertEqual(engine.metrics.book_payload_events, 1)

    def test_out_of_order_rejected(self):
        engine = EventDrivenFeatureEngine(3)
        engine.on_event(MarketEvent(2, 100, 1))
        with self.assertRaises(ValueError):
            engine.on_event(MarketEvent(2, 101, 1))

    def test_invalid_events_rejected(self):
        with self.assertRaises(ValueError):
            MarketEvent(0)
        with self.assertRaises(ValueError):
            MarketEvent(0, 100, None)
        with self.assertRaises(ValueError):
            MarketEvent(0, bid_price_ticks=100, ask_price_ticks=99,
                        bid_size=1, ask_size=1)
        with self.assertRaises(ValueError):
            MarketEvent(0, bid_price_ticks=100, ask_price_ticks=101,
                        bid_size=1)

    def test_arithmetic_reduction_for_trade_windows(self):
        events = [MarketEvent(i, 100_000 + (i % 13), (i % 7) + 1)
                  for i in range(10_000)]
        ref, inc = ReferenceFeatureEngine(100), EventDrivenFeatureEngine(100)
        self.assertEqual(replay(ref, events), replay(inc, events))
        self.assertLess(inc.metrics.counted_arithmetic_operations,
                        ref.metrics.counted_arithmetic_operations)

    def test_quote_state_persists_on_trade_events(self):
        events = [MarketEvent(0, bid_price_ticks=99, ask_price_ticks=102,
                              bid_size=7, ask_size=3),
                  MarketEvent(1, 100, 2)]
        out = replay(EventDrivenFeatureEngine(4), events)
        self.assertEqual(out[1].book_imbalance, Fraction(2, 5))
        self.assertEqual(out[1].spread_ticks, 3)

    def test_incremental_recalculates_only_affected_feature_groups(self):
        events = [
            MarketEvent(0, 100, 2, 99, 101, 10, 5),
            MarketEvent(1, bid_price_ticks=99, ask_price_ticks=101, bid_size=8, ask_size=6),
            MarketEvent(2, 101, 3),
        ]
        reference = ReferenceFeatureEngine(4)
        incremental = EventDrivenFeatureEngine(4)
        self.assertEqual(replay(reference, events), replay(incremental, events))
        self.assertEqual(reference.metrics.trade_feature_recalculations, 3)
        self.assertEqual(reference.metrics.book_feature_recalculations, 3)
        self.assertEqual(incremental.metrics.trade_feature_recalculations, 2)
        self.assertEqual(incremental.metrics.book_feature_recalculations, 2)


if __name__ == "__main__":
    unittest.main()
