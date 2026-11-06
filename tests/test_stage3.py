import random
import unittest
from efc.stage3 import (BookEvent, EventDrivenBookEngine, ReferenceBookEngine,
                        replay)


class Stage3Tests(unittest.TestCase):
    def compare(self, events, depth=5):
        self.assertEqual(replay(ReferenceBookEngine(depth), events),
                         replay(EventDrivenBookEngine(depth), events))

    def test_hand_calculated_book_and_ofi(self):
        events = [
            BookEvent(0, 10, "ADD", "b1", "B", 99, 10),
            BookEvent(1, 11, "ADD", "a1", "S", 103, 8),
            BookEvent(2, 12, "ADD", "b2", "B", 100, 4),
            BookEvent(3, 13, "ADD", "a2", "S", 102, 6),
            BookEvent(4, 14, "EXECUTE", "b2", quantity=2),
            BookEvent(5, 15, "CANCEL", "a2", quantity=3),
        ]
        out = replay(EventDrivenBookEngine(3), events)
        self.assertEqual(out[3].best_bid_ticks, 100)
        self.assertEqual(out[3].best_ask_ticks, 102)
        self.assertEqual(out[3].spread_ticks, 2)
        self.assertEqual(out[3].best_bid_size, 4)
        self.assertEqual(out[3].best_ask_size, 6)
        self.assertEqual(out[4].best_bid_size, 2)
        self.assertEqual(out[4].executed_quantity, 2)
        self.assertEqual(out[5].best_ask_size, 3)
        self.compare(events, depth=3)

    def test_partial_and_full_cancel_execution(self):
        events = [
            BookEvent(0, 1, "ADD", "b", "B", 100, 10),
            BookEvent(1, 2, "ADD", "a", "S", 105, 10),
            BookEvent(2, 3, "EXECUTE", "b", quantity=4),
            BookEvent(3, 4, "CANCEL", "a", quantity=10),
            BookEvent(4, 5, "CANCEL", "b", quantity=6),
        ]
        self.compare(events)

    def test_randomized_valid_event_streams(self):
        rng = random.Random(20261107)
        for case in range(50):
            events = []
            live = {}
            seq = 0
            for _ in range(300):
                choice = rng.random()
                if not live or choice < 0.45:
                    side = rng.choice(("B", "S"))
                    price = rng.randint(90, 99) if side == "B" else rng.randint(101, 110)
                    oid = f"{case}-{seq}"
                    qty = rng.randint(1, 100)
                    events.append(BookEvent(seq, seq + 1, "ADD", oid, side, price, qty))
                    live[oid] = [side, price, qty]
                else:
                    oid = rng.choice(list(live))
                    side, price, remaining = live[oid]
                    qty = rng.randint(1, remaining)
                    action = rng.choice(("CANCEL", "EXECUTE"))
                    events.append(BookEvent(seq, seq + 1, action, oid, quantity=qty))
                    if qty == remaining:
                        del live[oid]
                    else:
                        live[oid][2] -= qty
                seq += 1
            with self.subTest(case=case):
                self.compare(events, depth=7)

    def test_invalid_order_events(self):
        engine = EventDrivenBookEngine()
        with self.assertRaises(ValueError):
            engine.on_event(BookEvent(0, 1, "CANCEL", "missing", quantity=1))
        engine.on_event(BookEvent(0, 1, "ADD", "b", "B", 100, 5))
        with self.assertRaises(ValueError):
            engine.on_event(BookEvent(1, 2, "ADD", "b", "B", 99, 1))
        with self.assertRaises(ValueError):
            engine.on_event(BookEvent(1, 2, "EXECUTE", "b", quantity=6))
        with self.assertRaises(ValueError):
            engine.on_event(BookEvent(1, 2, "ADD", "cross", "S", 100, 1))

    def test_sequence_and_timestamp_validation(self):
        engine = EventDrivenBookEngine()
        engine.on_event(BookEvent(2, 10, "ADD", "b", "B", 99, 1))
        with self.assertRaises(ValueError):
            engine.on_event(BookEvent(2, 11, "ADD", "b2", "B", 98, 1))
        with self.assertRaises(ValueError):
            engine.on_event(BookEvent(3, 9, "ADD", "b3", "B", 98, 1))

    def test_ofi_baseline_and_cumulative(self):
        events = [
            BookEvent(0, 1, "ADD", "b", "B", 99, 10),
            BookEvent(1, 2, "ADD", "a", "S", 105, 8),
            BookEvent(2, 3, "ADD", "b2", "B", 99, 5),
            BookEvent(3, 4, "CANCEL", "b2", quantity=2),
        ]
        out = replay(EventDrivenBookEngine(), events)
        self.assertIsNone(out[0].event_ofi)
        self.assertIsNone(out[1].event_ofi)
        self.assertEqual(out[2].event_ofi, 5)
        self.assertEqual(out[3].event_ofi, -2)
        self.assertEqual(out[3].cumulative_ofi, 3)
        self.compare(events)

    def test_metrics_distinguish_incremental_from_rebuild(self):
        events = [
            BookEvent(0, 1, "ADD", "b", "B", 99, 10),
            BookEvent(1, 2, "ADD", "a", "S", 105, 10),
            BookEvent(2, 3, "ADD", "b2", "B", 98, 5),
            BookEvent(3, 4, "EXECUTE", "b", quantity=2),
        ]
        ref, inc = ReferenceBookEngine(), EventDrivenBookEngine()
        self.assertEqual(replay(ref, events), replay(inc, events))
        self.assertEqual(ref.metrics.full_book_rebuilds, 4)
        self.assertEqual(inc.metrics.full_book_rebuilds, 0)
        self.assertGreater(inc.metrics.level_updates, 0)


if __name__ == "__main__":
    unittest.main()
