"""Open window detection module for adaptive thermostat."""
from collections import deque
from datetime import datetime, timedelta
from typing import Optional, Tuple

from ..const import (
    DEFAULT_OWD_COOLDOWN,
    DEFAULT_OWD_DETECTION_WINDOW,
    DEFAULT_OWD_PAUSE_DURATION,
    DEFAULT_OWD_TEMP_DROP,
)


class OpenWindowDetector:
    """Detects open windows based on rapid temperature drops.

    Uses a ring buffer to track recent temperature history and detect
    patterns consistent with an open window (rapid temperature drop).
    """

    def __init__(
        self,
        detection_window: int = DEFAULT_OWD_DETECTION_WINDOW,
        temp_drop: float = DEFAULT_OWD_TEMP_DROP,
        pause_duration: int = DEFAULT_OWD_PAUSE_DURATION,
        cooldown: int = DEFAULT_OWD_COOLDOWN,
    ):
        """Initialize the open window detector.

        Args:
            detection_window: Time window in seconds to maintain temperature history.
                            Defaults to DEFAULT_OWD_DETECTION_WINDOW (180 seconds).
            temp_drop: Temperature drop threshold in °C to trigger open window detection.
                      Defaults to DEFAULT_OWD_TEMP_DROP (0.5°C).
            pause_duration: Duration in seconds to pause heating after window detection.
                          Defaults to DEFAULT_OWD_PAUSE_DURATION (1800 seconds).
            cooldown: Cooldown duration in seconds to prevent rapid re-triggering.
                     Defaults to DEFAULT_OWD_COOLDOWN (2700 seconds).
        """
        self._detection_window = detection_window
        self._temp_drop = temp_drop
        self._pause_duration = pause_duration
        self._cooldown = cooldown
        self._temp_history: deque[Tuple[datetime, float]] = deque()
        self._detection_triggered = False
        self._pause_start_time: Optional[datetime] = None
        self._pause_expired_flag = False
        self._expiration_detected = False
        self._last_detection_time: Optional[datetime] = None
        self._suppressed_until: Optional[datetime] = None

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

    def check_for_drop(self, now: Optional[datetime] = None) -> bool:
        """Check if temperature has dropped significantly within detection window.

        Compares the oldest temperature reading in the buffer to the current (most recent)
        reading. If the drop exceeds the configured threshold, returns True.

        Args:
            now: Optional current timestamp for cooldown/suppression checks.

        Returns:
            True if (oldest_temp - current_temp) >= temp_drop threshold, False otherwise.
            Also returns False if history is empty or contains only a single entry.
            Returns False if in cooldown or suppressed.
        """
        # Check cooldown if now is provided
        if now is not None and self.in_cooldown(now):
            return False

        # Check suppression if now is provided
        if now is not None and self.is_suppressed(now):
            return False

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

    def trigger_detection(self, now: datetime) -> None:
        """Trigger open window detection and start pause period.

        Args:
            now: Current timestamp when detection was triggered.
        """
        self._detection_triggered = True
        self._pause_start_time = now
        self._pause_expired_flag = False
        self._expiration_detected = False
        self._last_detection_time = now

    def should_pause(self, now: datetime) -> bool:
        """Check if heating should be paused due to open window detection.

        Args:
            now: Current timestamp to check against pause period.

        Returns:
            True if currently within pause period, False otherwise.
        """
        if not self._detection_triggered:
            return False

        if self._pause_start_time is None:
            return False

        pause_end_time = self._pause_start_time + timedelta(seconds=self._pause_duration)

        if now <= pause_end_time:
            return True

        # Pause has expired - set flag on first detection of expiration
        if not self._expiration_detected:
            self._expiration_detected = True
            self._pause_expired_flag = True
        return False

    def pause_just_expired(self) -> bool:
        """Check if pause period just expired and reset the flag.

        This method returns True only once when the pause expires, then False
        on subsequent calls until the pause expires again.

        Returns:
            True if pause just expired (first call after expiration), False otherwise.
        """
        if self._pause_expired_flag:
            self._pause_expired_flag = False
            return True
        return False

    def in_cooldown(self, now: datetime) -> bool:
        """Check if detector is in cooldown period.

        Args:
            now: Current timestamp to check against cooldown period.

        Returns:
            True if currently within cooldown period, False otherwise.
        """
        if self._last_detection_time is None:
            return False

        cooldown_end_time = self._last_detection_time + timedelta(seconds=self._cooldown)
        return now < cooldown_end_time

    def suppress_detection(self, now: datetime, duration: int) -> None:
        """Suppress detection for a specified duration.

        Args:
            now: Current timestamp when suppression starts.
            duration: Duration in seconds to suppress detection.
        """
        self._suppressed_until = now + timedelta(seconds=duration)

    def is_suppressed(self, now: datetime) -> bool:
        """Check if detection is currently suppressed.

        Args:
            now: Current timestamp to check against suppression period.

        Returns:
            True if currently suppressed, False otherwise.
        """
        if self._suppressed_until is None:
            return False

        return now < self._suppressed_until
