"""
Console Utilities - Terminal Output Helpers

Provides:
- ANSI color codes
- Colored print functions
- In-place terminal updates
- Log formatting

Usage:
    from lib.terminal_utils import Colors, log, clear_screen

    log("Order placed!", level="success")
    print(f"{Colors.GREEN}Connected{Colors.RESET}")
"""

from datetime import datetime
from collections import deque
from dataclasses import dataclass, field


class Colors:
    """ANSI color codes for terminal output."""

    # Regular colors
    BLACK = "\033[30m"
    RED = "\033[91m"
    GREEN = "\033[92m"
    YELLOW = "\033[93m"
    BLUE = "\033[94m"
    MAGENTA = "\033[95m"
    CYAN = "\033[96m"
    WHITE = "\033[97m"

    # Styles
    BOLD = "\033[1m"
    DIM = "\033[2m"
    UNDERLINE = "\033[4m"

    # Reset
    RESET = "\033[0m"

    # Shortcuts for common uses
    SUCCESS = GREEN
    WARNING = YELLOW
    ERROR = RED
    INFO = BLUE
    TRADE = MAGENTA


# Log level configuration
LOG_SYMBOLS = {
    "info": ("ℹ", Colors.BLUE),
    "success": ("✓", Colors.GREEN),
    "warning": ("⚠", Colors.YELLOW),
    "error": ("✗", Colors.RED),
    "trade": ("$", Colors.MAGENTA),
    "debug": ("·", Colors.DIM),
}


def get_timestamp() -> str:
    """Get current timestamp string."""
    return datetime.now().strftime("%H:%M:%S.%f")[:-3]


def log(msg: str, level: str = "info", show_timestamp: bool = True) -> str:
    """
    Format and print a log message.

    Args:
        msg: Message to log
        level: Log level (info, success, warning, error, trade, debug)
        show_timestamp: Whether to include timestamp

    Returns:
        Formatted message string
    """
    formatted = format_log(msg, level, show_timestamp)
    print(formatted)
    return formatted


def format_log(msg: str, level: str = "info", show_timestamp: bool = True) -> str:
    """
    Format a log message without printing.

    Args:
        msg: Message to format
        level: Log level
        show_timestamp: Whether to include timestamp

    Returns:
        Formatted message string
    """
    symbol, color = LOG_SYMBOLS.get(level, ("·", ""))
    ts = get_timestamp()

    if show_timestamp:
        return f"{Colors.CYAN}[{ts}]{Colors.RESET} {color}{symbol}{Colors.RESET} {msg}"
    return f"{color}{symbol}{Colors.RESET} {msg}"


def clear_screen() -> None:
    """Clear terminal screen."""
    print("\033[2J\033[H", end="", flush=True)


def move_cursor_home() -> None:
    """Move cursor to top-left position."""
    print("\033[H", end="", flush=True)


def clear_and_print(lines: list[str]) -> None:
    """
    Clear screen and print lines (for in-place updates).

    Args:
        lines: List of lines to print
    """
    output = "\033[H\033[J" + "\n".join(lines)
    print(output, flush=True)


def format_price(price: float, width: int = 9) -> str:
    """Format price with fixed width."""
    return f"{price:>{width}.4f}"


def format_size(size: float, width: int = 9) -> str:
    """Format size with fixed width."""
    return f"{size:>{width}.1f}"


def format_pnl(pnl: float, include_sign: bool = True) -> str:
    """Format PnL with color."""
    color = Colors.GREEN if pnl >= 0 else Colors.RED
    if include_sign:
        return f"{color}${pnl:+.2f}{Colors.RESET}"
    return f"{color}${abs(pnl):.2f}{Colors.RESET}"


def format_countdown(minutes: int, seconds: int) -> str:
    """
    Format countdown with color based on time remaining.

    Args:
        minutes: Minutes remaining
        seconds: Seconds remaining

    Returns:
        Colored countdown string
    """
    if minutes < 0:
        return "--:--"

    total_secs = minutes * 60 + seconds

    if total_secs <= 0:
        return f"{Colors.RED}ENDED{Colors.RESET}"
    elif total_secs <= 60:
        color = Colors.RED
    elif total_secs <= 180:
        color = Colors.YELLOW
    else:
        color = Colors.GREEN

    return f"{color}{minutes:02d}:{seconds:02d}{Colors.RESET}"


@dataclass
class LogBuffer:
    """
    Buffer for storing recent log messages.

    Useful for displaying recent events in a TUI.
    """

    max_size: int = 5
    messages: deque = field(default_factory=lambda: deque(maxlen=5))

    def __post_init__(self):
        self.messages = deque(maxlen=self.max_size)

    def add(self, msg: str, level: str = "info") -> None:
        """Add a formatted message to buffer."""
        formatted = format_log(msg, level, show_timestamp=True)
        self.messages.append(formatted)

    def get_messages(self) -> list[str]:
        """Get all buffered messages."""
        return list(self.messages)

    def clear(self) -> None:
        """Clear all messages."""
        self.messages.clear()


class StatusDisplay:
    """
    Helper for building multi-line status displays.

    Usage:
        display = StatusDisplay()
        display.add_header("Trading Bot")
        display.add_line("Status: Connected")
        display.add_separator()
        display.render()
    """

    def __init__(self, width: int = 80):
        self.width = width
        self.lines: list[str] = []

    def add_line(self, line: str) -> "StatusDisplay":
        """Add a line."""
        self.lines.append(line)
        return self

    def add_header(self, text: str) -> "StatusDisplay":
        """Add a bold header line."""
        self.lines.append(f"{Colors.BOLD}{text}{Colors.RESET}")
        return self

    def add_separator(self, char: str = "-") -> "StatusDisplay":
        """Add a separator line."""
        self.lines.append(char * self.width)
        return self

    def add_bold_separator(self, char: str = "=") -> "StatusDisplay":
        """Add a bold separator line."""
        self.lines.append(f"{Colors.BOLD}{char * self.width}{Colors.RESET}")
        return self

    def add_blank(self) -> "StatusDisplay":
        """Add a blank line."""
        self.lines.append("")
        return self

    def render(self, in_place: bool = True) -> str:
        """
        Render and print the display.

        Args:
            in_place: If True, clear screen first for in-place updates

        Returns:
            The rendered output string
        """
        output = "\n".join(self.lines)
        if in_place:
            print("\033[H\033[J" + output, flush=True)
        else:
            print(output, flush=True)
        return output

    def clear(self) -> "StatusDisplay":
        """Clear all lines."""
        self.lines = []
        return self

    def get_lines(self) -> list[str]:
        """Get all lines."""
        return self.lines.copy()
