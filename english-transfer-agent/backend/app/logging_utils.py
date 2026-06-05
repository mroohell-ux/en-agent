from __future__ import annotations

import os

RED = "\033[31m"
RESET = "\033[0m"


def color_request_log(message: str) -> str:
    """Mark request-related log messages red in terminals that support ANSI colors."""
    if os.getenv("NO_COLOR"):
        return message
    return f"{RED}{message}{RESET}"
