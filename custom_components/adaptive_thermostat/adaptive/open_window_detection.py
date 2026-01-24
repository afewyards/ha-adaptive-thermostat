"""Open window detection module for adaptive thermostat."""
from collections import deque
from datetime import datetime, timedelta
from typing import Tuple

from ..const import DEFAULT_OWD_DETECTION_WINDOW, DEFAULT_OWD_TEMP_DROP


class OpenWindowDetector:
    """Detects open windows based on rapid temperature drops.

    Uses a ring buffer to track recent temperature history and detect
    patterns consistent with an open window (rapid temperature drop).
    """

    def __init__(
        self,
        detection_window: int = DEFAULT_OWD_DETECTION_WINDOW,
        temp_drop: float = DEFAULT_OWD_TEMP_DROP,
    ):
        """Initialize the open window detector.

        Args:
            detection_window: Time window in seconds to maintain temperature history.
                            Defaults to DEFAULT_OWD_DETECTION_WINDOW (180 seconds).
            temp_drop: Temperature drop threshold in °C to trigger open window detection.
                      Defaults to DEFAULT_OWD_TEMP_DROP (0.5°C).
        """
        self._detection_window = detection_window
        self._temp_drop = temp_drop
        self._temp_history: deque[Tuple[datetime, float]] = deque()

    def record_temperature(self, timestamp: datetime, temp: float) -> None:
        """Record a temperature reading and prune old entries.

        Adds the new temperature reading to the ring buffer and removes
        entries older than the detection window.

        Args:
            timestamp: The time of the temperature reading.
            temp: The temperature value.
        """
        # Add new entry
        self._temp_history.append((timestamp, temp))

        # Prune entries older than detection_window
        cutoff_time = timestamp - timedelta(seconds=self._detection_window)

        # Remove old entries from the left (oldest first)
        while self._temp_history and self._temp_history[0][0] < cutoff_time:
            self._temp_history.popleft()

    def check_for_drop(self) -> bool:
        """Check if temperature has dropped significantly within detection window.

        Compares the oldest temperature reading in the buffer to the current (most recent)
        reading. If the drop exceeds the configured threshold, returns True.

        Returns:
            True if (oldest_temp - current_temp) >= temp_drop threshold, False otherwise.
            Also returns False if history is empty or contains only a single entry.
        """
        # Return False if history is empty or has only one entry
        if len(self._temp_history) <= 1:
            return False

        # Get oldest and current temperatures
        oldest_temp = self._temp_history[0][1]
        current_temp = self._temp_history[-1][1]

        # Calculate drop (oldest - current)
        temp_drop = oldest_temp - current_temp

        # Return True if drop meets or exceeds threshold
        return temp_drop >= self._temp_drop
