"""Clock abstraction for deterministic, testable timing.

``WallClock`` is used in production; ``ManualClock`` lets tests advance time explicitly so
every millisecond deadline (100/200/300/500/1000/2000 ms) is asserted deterministically.
"""
