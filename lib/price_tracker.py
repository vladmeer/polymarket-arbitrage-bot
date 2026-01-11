"""
Price Tracker - Price History and Flash Crash Detection

Provides:
- Price history storage with timestamps
- Flash crash detection (absolute probability drops)
- Price point data structures
- Configurable lookback windows

Usage:
    from lib import PriceTracker, FlashCrashEvent

    tracker = PriceTracker(lookback_seconds=10, drop_threshold=0.30)

    # Record prices
    tracker.record("up", 0.55)
    tracker.record("down", 0.45)

    # Check for flash crash
    event = tracker.detect_flash_crash()
    if event:
        print(f"Crash on {event.side}: {event.old_price} -> {event.new_price}")
"""

import time
from collections import deque
from dataclasses import dataclass, field
from typing import Optional, Dict, Deque, List


@dataclass
class PricePoint:
    """A price observation at a specific time."""

    timestamp: float
    price: float
    side: str  # "up" or "down"


@dataclass
class FlashCrashEvent:
    """Detected flash crash event."""

    side: str  # "up" or "down"
    old_price: float
    new_price: float
    drop: float  # Absolute drop amount
    timestamp: float

    @property
    def drop_percent(self) -> float:
        """Calculate percentage drop."""
        if self.old_price > 0:
            return (self.old_price - self.new_price) / self.old_price * 100
        return 0.0


@dataclass
class PriceTracker:
    """
    Tracks price history and detects flash crashes.

    A flash crash is when the probability drops by more than the threshold
    within the lookback window (e.g., 0.30 means price drops from 0.5 to 0.2).
    """

    lookback_seconds: int = 10
    drop_threshold: float = 0.30
    max_history: int = 100

    # Price history per side
    _history: Dict[str, Deque[PricePoint]] = field(default_factory=dict)

    def __post_init__(self):
        """Initialize history deques."""
        self._history = {
            "up": deque(maxlen=self.max_history),
            "down": deque(maxlen=self.max_history),
        }

    def record(self, side: str, price: float, timestamp: Optional[float] = None) -> None:
        """
        Record a price point.

        Args:
            side: "up" or "down"
            price: Current price (0-1)
            timestamp: Optional timestamp (defaults to now)
        """
        if side not in self._history:
            return

        if price <= 0:
            return

        ts = timestamp if timestamp is not None else time.time()
        self._history[side].append(PricePoint(timestamp=ts, price=price, side=side))

    def record_prices(self, prices: Dict[str, float]) -> None:
        """
        Record multiple prices at once.

        Args:
            prices: Dictionary of {side: price}
        """
        now = time.time()
        for side, price in prices.items():
            self.record(side, price, now)

    def get_history(self, side: str) -> List[PricePoint]:
        """Get price history for a side."""
        if side in self._history:
            return list(self._history[side])
        return []

    def get_history_count(self, side: str) -> int:
        """Get number of recorded prices for a side."""
        if side in self._history:
            return len(self._history[side])
        return 0

    def get_current_price(self, side: str) -> float:
        """Get most recent price for a side."""
        if side in self._history and self._history[side]:
            return self._history[side][-1].price
        return 0.0

    def get_price_at(self, side: str, seconds_ago: float) -> Optional[float]:
        """
        Get price from N seconds ago.

        Args:
            side: "up" or "down"
            seconds_ago: How far back to look

        Returns:
            Price at that time or None
        """
        if side not in self._history:
            return None

        now = time.time()
        target_time = now - seconds_ago

        for point in self._history[side]:
            if point.timestamp >= target_time:
                return point.price

        return None

    def detect_flash_crash(self, side: Optional[str] = None) -> Optional[FlashCrashEvent]:
        """
        Detect if a flash crash occurred.

        Args:
            side: Specific side to check, or None to check both

        Returns:
            FlashCrashEvent if crash detected, None otherwise
        """
        sides_to_check = [side] if side else ["up", "down"]
        now = time.time()

        for s in sides_to_check:
            if s not in self._history:
                continue

            history = self._history[s]
            if len(history) < 2:
                continue

            # Get current price
            current_price = history[-1].price

            # Find price from lookback_seconds ago
            old_price = None
            for point in history:
                if now - point.timestamp <= self.lookback_seconds:
                    old_price = point.price
                    break

            if old_price is None:
                continue

            # Calculate absolute drop
            drop = old_price - current_price

            if drop >= self.drop_threshold:
                return FlashCrashEvent(
                    side=s,
                    old_price=old_price,
                    new_price=current_price,
                    drop=drop,
                    timestamp=now,
                )

        return None

    def detect_all_crashes(self) -> List[FlashCrashEvent]:
        """
        Detect flash crashes on all sides.

        Returns:
            List of FlashCrashEvent for all detected crashes
        """
        events = []
        for side in ["up", "down"]:
            event = self.detect_flash_crash(side)
            if event:
                events.append(event)
        return events

    def clear(self, side: Optional[str] = None) -> None:
        """
        Clear price history.

        Args:
            side: Specific side to clear, or None to clear all
        """
        if side:
            if side in self._history:
                self._history[side].clear()
        else:
            for s in self._history:
                self._history[s].clear()

    def get_price_range(self, side: str, seconds: float) -> tuple[float, float]:
        """
        Get min/max price over the last N seconds.

        Args:
            side: "up" or "down"
            seconds: Lookback window

        Returns:
            Tuple of (min_price, max_price), or (0, 0) if no data
        """
        if side not in self._history:
            return (0.0, 0.0)

        now = time.time()
        cutoff = now - seconds

        prices = [p.price for p in self._history[side] if p.timestamp >= cutoff]

        if not prices:
            return (0.0, 0.0)

        return (min(prices), max(prices))

    def get_volatility(self, side: str, seconds: float) -> float:
        """
        Calculate price volatility (max - min) over the last N seconds.

        Args:
            side: "up" or "down"
            seconds: Lookback window

        Returns:
            Price range (max - min)
        """
        min_price, max_price = self.get_price_range(side, seconds)
        return max_price - min_price
