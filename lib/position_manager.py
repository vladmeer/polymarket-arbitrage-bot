"""
Position Manager - Position Tracking with TP/SL

Provides:
- Position tracking with entry price and size
- Take profit and stop loss calculation
- PnL tracking (unrealized and realized)
- Position state management

Usage:
    from lib import PositionManager, Position

    manager = PositionManager(take_profit=0.10, stop_loss=0.05)

    # Open position
    pos = manager.open_position(
        side="up",
        token_id="12345",
        entry_price=0.35,
        size=10.0
    )

    # Check exit conditions
    exit_type, pnl = manager.check_exit(pos.id, current_price=0.45)
    if exit_type == "take_profit":
        manager.close_position(pos.id, realized_pnl=pnl)
"""

import time
import uuid
from dataclasses import dataclass, field
from typing import Optional, Dict, List, Literal


ExitType = Literal["take_profit", "stop_loss", None]


@dataclass
class Position:
    """Active trading position."""

    id: str
    side: str  # "up" or "down"
    token_id: str
    entry_price: float
    size: float
    entry_time: float
    order_id: Optional[str] = None

    # TP/SL config (set by PositionManager)
    take_profit_delta: float = 0.10
    stop_loss_delta: float = 0.05

    @property
    def take_profit_price(self) -> float:
        """Target price for take profit."""
        return self.entry_price + self.take_profit_delta

    @property
    def stop_loss_price(self) -> float:
        """Target price for stop loss."""
        return self.entry_price - self.stop_loss_delta

    def get_pnl(self, current_price: float) -> float:
        """Calculate unrealized PnL."""
        return (current_price - self.entry_price) * self.size

    def get_pnl_percent(self, current_price: float) -> float:
        """Calculate PnL as percentage."""
        if self.entry_price > 0:
            return (current_price - self.entry_price) / self.entry_price * 100
        return 0.0

    def get_hold_time(self) -> float:
        """Get time held in seconds."""
        return time.time() - self.entry_time

    def check_take_profit(self, current_price: float) -> bool:
        """Check if take profit is triggered."""
        return current_price >= self.take_profit_price

    def check_stop_loss(self, current_price: float) -> bool:
        """Check if stop loss is triggered."""
        return current_price <= self.stop_loss_price


@dataclass
class PositionManager:
    """
    Manages trading positions with TP/SL.

    Tracks:
    - Open positions
    - Realized and unrealized PnL
    - Trade statistics
    """

    take_profit: float = 0.10  # +10 cents
    stop_loss: float = 0.05  # -5 cents
    max_positions: int = 1  # Max concurrent positions

    # State
    _positions: Dict[str, Position] = field(default_factory=dict)
    _positions_by_side: Dict[str, str] = field(default_factory=dict)  # side -> position_id

    # Stats
    trades_opened: int = 0
    trades_closed: int = 0
    total_pnl: float = 0.0
    winning_trades: int = 0
    losing_trades: int = 0

    def __post_init__(self):
        """Initialize state."""
        self._positions = {}
        self._positions_by_side = {}

    @property
    def position_count(self) -> int:
        """Number of open positions."""
        return len(self._positions)

    @property
    def can_open_position(self) -> bool:
        """Check if we can open a new position."""
        return self.position_count < self.max_positions

    @property
    def win_rate(self) -> float:
        """Calculate win rate percentage."""
        total = self.winning_trades + self.losing_trades
        if total > 0:
            return self.winning_trades / total * 100
        return 0.0

    def open_position(
        self,
        side: str,
        token_id: str,
        entry_price: float,
        size: float,
        order_id: Optional[str] = None,
    ) -> Optional[Position]:
        """
        Open a new position.

        Args:
            side: "up" or "down"
            token_id: Token identifier
            entry_price: Entry price
            size: Position size
            order_id: Optional order ID

        Returns:
            Position if opened, None if at max positions
        """
        if not self.can_open_position:
            return None

        # Check if already have position on this side
        if side in self._positions_by_side:
            return None

        pos_id = str(uuid.uuid4())[:8]

        position = Position(
            id=pos_id,
            side=side,
            token_id=token_id,
            entry_price=entry_price,
            size=size,
            entry_time=time.time(),
            order_id=order_id,
            take_profit_delta=self.take_profit,
            stop_loss_delta=self.stop_loss,
        )

        self._positions[pos_id] = position
        self._positions_by_side[side] = pos_id
        self.trades_opened += 1

        return position

    def close_position(self, position_id: str, realized_pnl: float = 0.0) -> Optional[Position]:
        """
        Close and remove a position.

        Args:
            position_id: Position ID to close
            realized_pnl: Actual PnL realized from the trade

        Returns:
            Closed position or None
        """
        if position_id not in self._positions:
            return None

        position = self._positions.pop(position_id)

        # Remove from side mapping
        if position.side in self._positions_by_side:
            if self._positions_by_side[position.side] == position_id:
                del self._positions_by_side[position.side]

        # Update stats
        self.trades_closed += 1
        self.total_pnl += realized_pnl

        if realized_pnl >= 0:
            self.winning_trades += 1
        else:
            self.losing_trades += 1

        return position

    def get_position(self, position_id: str) -> Optional[Position]:
        """Get position by ID."""
        return self._positions.get(position_id)

    def get_position_by_side(self, side: str) -> Optional[Position]:
        """Get position by side."""
        pos_id = self._positions_by_side.get(side)
        if pos_id:
            return self._positions.get(pos_id)
        return None

    def get_all_positions(self) -> List[Position]:
        """Get all open positions."""
        return list(self._positions.values())

    def has_position(self, side: str) -> bool:
        """Check if there's a position on a side."""
        return side in self._positions_by_side

    def check_exit(
        self, position_id: str, current_price: float
    ) -> tuple[ExitType, float]:
        """
        Check if position should exit.

        Args:
            position_id: Position ID
            current_price: Current market price

        Returns:
            Tuple of (exit_type, pnl)
            exit_type is "take_profit", "stop_loss", or None
        """
        position = self._positions.get(position_id)
        if not position:
            return (None, 0.0)

        pnl = position.get_pnl(current_price)

        if position.check_take_profit(current_price):
            return ("take_profit", pnl)

        if position.check_stop_loss(current_price):
            return ("stop_loss", pnl)

        return (None, pnl)

    def check_all_exits(
        self, prices: Dict[str, float]
    ) -> List[tuple[Position, ExitType, float]]:
        """
        Check exit conditions for all positions.

        Args:
            prices: Dictionary of {side: price}

        Returns:
            List of (position, exit_type, pnl) for positions that should exit
        """
        exits = []

        for position in self._positions.values():
            price = prices.get(position.side, 0)
            if price <= 0:
                continue

            exit_type, pnl = self.check_exit(position.id, price)
            if exit_type:
                exits.append((position, exit_type, pnl))

        return exits

    def get_unrealized_pnl(self, prices: Dict[str, float]) -> float:
        """
        Calculate total unrealized PnL.

        Args:
            prices: Dictionary of {side: price}

        Returns:
            Total unrealized PnL
        """
        total = 0.0
        for position in self._positions.values():
            price = prices.get(position.side, 0)
            if price > 0:
                total += position.get_pnl(price)
        return total

    def get_total_pnl(self, prices: Dict[str, float]) -> float:
        """Get total PnL (realized + unrealized)."""
        return self.total_pnl + self.get_unrealized_pnl(prices)

    def get_stats(self) -> Dict:
        """Get trading statistics."""
        return {
            "trades_opened": self.trades_opened,
            "trades_closed": self.trades_closed,
            "open_positions": self.position_count,
            "total_pnl": self.total_pnl,
            "winning_trades": self.winning_trades,
            "losing_trades": self.losing_trades,
            "win_rate": self.win_rate,
        }

    def clear(self) -> None:
        """Clear all positions (without updating stats)."""
        self._positions.clear()
        self._positions_by_side.clear()

    def reset_stats(self) -> None:
        """Reset all statistics."""
        self.trades_opened = 0
        self.trades_closed = 0
        self.total_pnl = 0.0
        self.winning_trades = 0
        self.losing_trades = 0
