from typing import Any


DEBUG_LOG_ENABLED = True
DEBUG_LOG_VERBOSE_ENABLED = False


class DebugLogger:
    """Provides debug-constant logging functionality."""

    @classmethod
    def logDebug(cls, msg: Any):
        """Prints a message to the console if debug logging is enabled.

        Args:
            msg (Any): The message to print (can be anything accepted by the print() function).
        """
        if DEBUG_LOG_ENABLED:
            print(msg)

    @classmethod
    def logDebugVerbose(cls, msg: Any):
        """Prints a message to the console if verbose debug logging is enabled.

        Args:
            msg (Any): The message to print (can be anything accepted by the print() function).
        """
        if DEBUG_LOG_VERBOSE_ENABLED:
            print(msg)
