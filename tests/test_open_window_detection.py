"""Tests for open window detection module."""
import pytest
from datetime import datetime, timedelta
from collections import deque
from custom_components.adaptive_thermostat.adaptive.open_window_detection import (
    OpenWindowDetector
)
from custom_components.adaptive_thermostat.const import DEFAULT_OWD_TEMP_DROP


class TestOpenWindowDetectorRingBuffer:
    """Test OpenWindowDetector ring buffer and temperature recording."""

    def test_empty_history_on_init(self):
        """Test that detector starts with empty history."""
        detector = OpenWindowDetector(detection_window=180)

        # History should be empty on initialization
        assert len(detector._temp_history) == 0
        assert isinstance(detector._temp_history, deque)

    def test_record_temperature_adds_to_history(self):
        """Test that recording temperature adds (timestamp, temp) tuple to history."""
        detector = OpenWindowDetector(detection_window=180)

        timestamp = datetime(2024, 1, 15, 10, 0, 0)
        temperature = 20.5

        detector.record_temperature(timestamp, temperature)

        # Should have one entry
        assert len(detector._temp_history) == 1

        # Entry should be (timestamp, temp) tuple
        entry = detector._temp_history[0]
        assert entry[0] == timestamp
        assert entry[1] == temperature

        # Add another entry
        timestamp2 = datetime(2024, 1, 15, 10, 0, 30)
        temperature2 = 20.3

        detector.record_temperature(timestamp2, temperature2)

        # Should have two entries
        assert len(detector._temp_history) == 2
        assert detector._temp_history[1][0] == timestamp2
        assert detector._temp_history[1][1] == temperature2

    def test_ring_buffer_maintains_order(self):
        """Test that ring buffer maintains chronological order (oldest first)."""
        detector = OpenWindowDetector(detection_window=180)

        # Add several temperature readings
        base_time = datetime(2024, 1, 15, 10, 0, 0)
        temperatures = [20.5, 20.4, 20.3, 20.2, 20.1]

        for i, temp in enumerate(temperatures):
            timestamp = base_time + timedelta(seconds=i * 30)
            detector.record_temperature(timestamp, temp)

        # Verify order - oldest (first) to newest (last)
        assert len(detector._temp_history) == 5

        for i in range(len(detector._temp_history)):
            expected_time = base_time + timedelta(seconds=i * 30)
            expected_temp = temperatures[i]

            assert detector._temp_history[i][0] == expected_time
            assert detector._temp_history[i][1] == expected_temp

    def test_ring_buffer_prunes_old_entries(self):
        """Test that entries older than detection_window are removed."""
        detection_window = 180  # 3 minutes
        detector = OpenWindowDetector(detection_window=detection_window)

        base_time = datetime(2024, 1, 15, 10, 0, 0)

        # Add entries spanning 4.5 minutes (10 entries, 30 seconds apart)
        # With detection_window=180s, entries are pruned continuously.
        # After adding entry at 270s, cutoff = 270-180 = 90s
        # Entries at 0, 30, 60s are pruned, leaving entries at 90-270s (7 entries)
        for i in range(10):
            timestamp = base_time + timedelta(seconds=i * 30)
            temperature = 20.5 - (i * 0.1)
            detector.record_temperature(timestamp, temperature)

        # After loop: entries within detection_window of last entry (270s)
        # are kept: 90, 120, 150, 180, 210, 240, 270 = 7 entries
        assert len(detector._temp_history) == 7

        # Now record a new temperature 5 minutes after start
        current_time = base_time + timedelta(minutes=5)
        detector.record_temperature(current_time, 20.0)

        # Should prune entries older than (current_time - detection_window)
        # detection_window = 180 sec = 3 min
        # cutoff = 5 min - 3 min = 2 min from base_time
        # Entries at 0, 0.5, 1, 1.5 min should be pruned (< 2 min)
        # Entries at 2, 2.5, 3, 3.5, 4, 4.5 min should remain
        # Plus the new entry at 5 min

        cutoff_time = current_time - timedelta(seconds=detection_window)

        # Verify no entries older than cutoff
        for timestamp, _ in detector._temp_history:
            assert timestamp >= cutoff_time

        # Verify oldest entry is approximately at cutoff
        oldest_entry_time = detector._temp_history[0][0]
        assert oldest_entry_time >= cutoff_time

    def test_detection_window_configurable(self):
        """Test that custom detection_window works correctly."""
        # Test with 60 second window
        detector_60 = OpenWindowDetector(detection_window=60)

        base_time = datetime(2024, 1, 15, 10, 0, 0)

        # Add entries spanning 90 seconds
        for i in range(6):  # 6 entries, 15 seconds apart = 75 seconds span
            timestamp = base_time + timedelta(seconds=i * 15)
            detector_60.record_temperature(timestamp, 20.0)

        # Add entry at 90 seconds
        current_time = base_time + timedelta(seconds=90)
        detector_60.record_temperature(current_time, 19.5)

        # Should prune entries older than 30 seconds from base_time
        # (90 - 60 = 30 seconds)
        cutoff_time = current_time - timedelta(seconds=60)

        for timestamp, _ in detector_60._temp_history:
            assert timestamp >= cutoff_time

        # Test with 300 second window (5 minutes)
        detector_300 = OpenWindowDetector(detection_window=300)

        # Add entries spanning 6 minutes
        for i in range(12):  # 12 entries, 30 seconds apart = 5.5 minutes
            timestamp = base_time + timedelta(seconds=i * 30)
            detector_300.record_temperature(timestamp, 20.0)

        # Add entry at 6 minutes
        current_time = base_time + timedelta(minutes=6)
        detector_300.record_temperature(current_time, 19.5)

        # Should prune entries older than 1 minute from base_time
        # (6 min - 5 min = 1 min)
        cutoff_time = current_time - timedelta(seconds=300)

        for timestamp, _ in detector_300._temp_history:
            assert timestamp >= cutoff_time

    def test_ring_buffer_handles_single_entry(self):
        """Test ring buffer with single entry."""
        detector = OpenWindowDetector(detection_window=180)

        timestamp = datetime(2024, 1, 15, 10, 0, 0)
        temperature = 20.5

        detector.record_temperature(timestamp, temperature)

        # Single entry should remain even after time passes
        # (until a new entry triggers pruning)
        assert len(detector._temp_history) == 1
        assert detector._temp_history[0] == (timestamp, temperature)

    def test_ring_buffer_all_entries_pruned(self):
        """Test scenario where all old entries are pruned."""
        detector = OpenWindowDetector(detection_window=60)

        base_time = datetime(2024, 1, 15, 10, 0, 0)

        # Add several old entries
        for i in range(5):
            timestamp = base_time + timedelta(seconds=i * 10)
            detector.record_temperature(timestamp, 20.0)

        assert len(detector._temp_history) == 5

        # Add new entry much later (5 minutes later)
        # This should prune all previous entries
        future_time = base_time + timedelta(minutes=5)
        detector.record_temperature(future_time, 19.0)

        # Only the new entry should remain
        assert len(detector._temp_history) == 1
        assert detector._temp_history[0][0] == future_time
        assert detector._temp_history[0][1] == 19.0


class TestOpenWindowDetectorDropDetection:
    """Test OpenWindowDetector drop detection logic."""

    def test_check_for_drop_detects_rapid_drop(self):
        """Test that drop >= threshold returns True."""
        detector = OpenWindowDetector(detection_window=180)

        base_time = datetime(2024, 1, 15, 10, 0, 0)

        # Record decreasing temperatures: 21.0 -> 20.4 (0.6°C drop, exceeds 0.5°C threshold)
        detector.record_temperature(base_time, 21.0)
        detector.record_temperature(base_time + timedelta(seconds=30), 20.8)
        detector.record_temperature(base_time + timedelta(seconds=60), 20.6)
        detector.record_temperature(base_time + timedelta(seconds=90), 20.4)

        # Should detect drop: oldest (21.0) - current (20.4) = 0.6°C >= 0.5°C threshold
        assert detector.check_for_drop() is True

    def test_check_for_drop_ignores_small_drop(self):
        """Test that drop < threshold returns False."""
        detector = OpenWindowDetector(detection_window=180)

        base_time = datetime(2024, 1, 15, 10, 0, 0)

        # Record temperatures with small drop: 21.0 -> 20.6 (0.4°C drop, below 0.5°C threshold)
        detector.record_temperature(base_time, 21.0)
        detector.record_temperature(base_time + timedelta(seconds=30), 20.9)
        detector.record_temperature(base_time + timedelta(seconds=60), 20.8)
        detector.record_temperature(base_time + timedelta(seconds=90), 20.6)

        # Should NOT detect drop: oldest (21.0) - current (20.6) = 0.4°C < 0.5°C threshold
        assert detector.check_for_drop() is False

    def test_check_for_drop_empty_history(self):
        """Test that empty buffer returns False."""
        detector = OpenWindowDetector(detection_window=180)

        # No temperature readings recorded
        assert len(detector._temp_history) == 0

        # Should return False with empty history
        assert detector.check_for_drop() is False

    def test_check_for_drop_single_entry(self):
        """Test that single entry returns False."""
        detector = OpenWindowDetector(detection_window=180)

        base_time = datetime(2024, 1, 15, 10, 0, 0)

        # Record only one temperature
        detector.record_temperature(base_time, 21.0)

        # Should return False with only one entry
        # (oldest == current, so drop = 0)
        assert detector.check_for_drop() is False

    def test_check_for_drop_configurable_threshold(self):
        """Test that custom temp_drop threshold works."""
        # Use custom threshold of 1.0°C (twice the default)
        custom_threshold = 1.0
        detector = OpenWindowDetector(detection_window=180, temp_drop=custom_threshold)

        base_time = datetime(2024, 1, 15, 10, 0, 0)

        # Record drop of 0.8°C (exceeds default 0.5°C but below custom 1.0°C)
        detector.record_temperature(base_time, 21.0)
        detector.record_temperature(base_time + timedelta(seconds=60), 20.2)

        # Should NOT detect drop with custom threshold: 0.8°C < 1.0°C
        assert detector.check_for_drop() is False

        # Now add a bigger drop: 1.2°C total
        detector.record_temperature(base_time + timedelta(seconds=120), 19.8)

        # Should detect drop with custom threshold: 1.2°C >= 1.0°C
        assert detector.check_for_drop() is True

    def test_check_for_drop_temperature_rise(self):
        """Test that temperature rise returns False."""
        detector = OpenWindowDetector(detection_window=180)

        base_time = datetime(2024, 1, 15, 10, 0, 0)

        # Record rising temperatures: 20.0 -> 21.0
        detector.record_temperature(base_time, 20.0)
        detector.record_temperature(base_time + timedelta(seconds=30), 20.3)
        detector.record_temperature(base_time + timedelta(seconds=60), 20.6)
        detector.record_temperature(base_time + timedelta(seconds=90), 21.0)

        # Should NOT detect drop: oldest (20.0) - current (21.0) = -1.0°C (negative)
        assert detector.check_for_drop() is False


class TestOpenWindowDetectorPauseLifecycle:
    """Test OpenWindowDetector pause lifecycle."""

    def test_initial_state_no_pause_active(self):
        """Test that detector starts with no pause active."""
        detector = OpenWindowDetector(pause_duration=1800)
        now = datetime(2024, 1, 15, 10, 0, 0)

        # Initial state should have no pause active
        assert detector.should_pause(now) is False
        assert detector.pause_just_expired() is False

    def test_trigger_detection_starts_pause(self):
        """Test that trigger_detection() starts pause period and sets internal state."""
        detector = OpenWindowDetector(pause_duration=1800)
        now = datetime(2024, 1, 15, 10, 0, 0)

        # Trigger detection
        detector.trigger_detection(now)

        # Should now be in pause state
        assert detector.should_pause(now) is True

    def test_should_pause_during_pause_period(self):
        """Test that should_pause() returns True during pause period."""
        detector = OpenWindowDetector(pause_duration=60)  # 1 minute pause
        now = datetime(2024, 1, 15, 10, 0, 0)

        detector.trigger_detection(now)

        # 30 seconds later - still paused
        assert detector.should_pause(now + timedelta(seconds=30)) is True

        # 59 seconds later - still paused
        assert detector.should_pause(now + timedelta(seconds=59)) is True

    def test_should_pause_after_pause_expires(self):
        """Test that should_pause() returns False after pause_duration expires."""
        detector = OpenWindowDetector(pause_duration=60)  # 1 minute pause
        now = datetime(2024, 1, 15, 10, 0, 0)

        detector.trigger_detection(now)

        # 61 seconds later - pause expired
        assert detector.should_pause(now + timedelta(seconds=61)) is False

        # 120 seconds later - pause still expired
        assert detector.should_pause(now + timedelta(seconds=120)) is False

    def test_pause_just_expired_returns_true_once(self):
        """Test that pause_just_expired() returns True once when pause expires, then False."""
        detector = OpenWindowDetector(pause_duration=60)  # 1 minute pause
        now = datetime(2024, 1, 15, 10, 0, 0)

        detector.trigger_detection(now)

        # During pause - should return False
        assert detector.pause_just_expired() is False

        # Check if pause has expired (this triggers the transition)
        pause_expired_time = now + timedelta(seconds=61)
        detector.should_pause(pause_expired_time)

        # First call after expiration - should return True
        assert detector.pause_just_expired() is True

        # Subsequent calls - should return False (already consumed)
        assert detector.pause_just_expired() is False
        assert detector.pause_just_expired() is False

    def test_multiple_trigger_detection_calls_reset_timer(self):
        """Test that multiple trigger_detection() calls reset the pause timer."""
        detector = OpenWindowDetector(pause_duration=60)  # 1 minute pause
        now = datetime(2024, 1, 15, 10, 0, 0)

        # First trigger
        detector.trigger_detection(now)

        # 30 seconds later - still paused
        time_30s = now + timedelta(seconds=30)
        assert detector.should_pause(time_30s) is True

        # Trigger again at 30 seconds - resets the timer
        detector.trigger_detection(time_30s)

        # 50 seconds from original start (20s from second trigger) - should still be paused
        time_50s = now + timedelta(seconds=50)
        assert detector.should_pause(time_50s) is True

        # 70 seconds from original start (40s from second trigger) - should still be paused
        time_70s = now + timedelta(seconds=70)
        assert detector.should_pause(time_70s) is True

        # 91 seconds from original start (61s from second trigger) - pause should expire
        time_91s = now + timedelta(seconds=91)
        assert detector.should_pause(time_91s) is False

    def test_pause_duration_configurable_via_constructor(self):
        """Test that pause_duration is configurable via constructor."""
        # Test with 120 second pause
        detector_120 = OpenWindowDetector(pause_duration=120)
        now = datetime(2024, 1, 15, 10, 0, 0)

        detector_120.trigger_detection(now)

        # 60 seconds later - still paused (half of 120s duration)
        assert detector_120.should_pause(now + timedelta(seconds=60)) is True

        # 119 seconds later - still paused
        assert detector_120.should_pause(now + timedelta(seconds=119)) is True

        # 121 seconds later - pause expired
        assert detector_120.should_pause(now + timedelta(seconds=121)) is False

        # Test with 1800 second pause (default from DEFAULT_OWD_PAUSE_DURATION)
        detector_1800 = OpenWindowDetector(pause_duration=1800)
        detector_1800.trigger_detection(now)

        # 15 minutes later (900s) - still paused (half of 30 minutes)
        assert detector_1800.should_pause(now + timedelta(seconds=900)) is True

        # 29 minutes later (1740s) - still paused
        assert detector_1800.should_pause(now + timedelta(seconds=1740)) is True

        # 31 minutes later (1860s) - pause expired
        assert detector_1800.should_pause(now + timedelta(seconds=1860)) is False

    def test_pause_just_expired_without_prior_should_pause_check(self):
        """Test pause_just_expired() behavior when called without prior should_pause() check."""
        detector = OpenWindowDetector(pause_duration=60)
        now = datetime(2024, 1, 15, 10, 0, 0)

        detector.trigger_detection(now)

        # Call pause_just_expired() directly after pause has expired (no should_pause check)
        # This tests edge case where user calls pause_just_expired() directly
        # Expected behavior: should return False (requires should_pause to detect transition)
        time_after_expire = now + timedelta(seconds=61)

        # Without calling should_pause first, pause_just_expired should return False
        assert detector.pause_just_expired() is False

        # Now call should_pause to trigger the transition
        detector.should_pause(time_after_expire)

        # Now pause_just_expired should return True
        assert detector.pause_just_expired() is True

    def test_pause_lifecycle_full_flow(self):
        """Test complete pause lifecycle: trigger → pause → expire → resume."""
        detector = OpenWindowDetector(pause_duration=60)
        now = datetime(2024, 1, 15, 10, 0, 0)

        # 1. Initial state - no pause
        assert detector.should_pause(now) is False
        assert detector.pause_just_expired() is False

        # 2. Trigger detection - starts pause
        detector.trigger_detection(now)
        assert detector.should_pause(now) is True
        assert detector.pause_just_expired() is False

        # 3. During pause period
        time_30s = now + timedelta(seconds=30)
        assert detector.should_pause(time_30s) is True
        assert detector.pause_just_expired() is False

        # 4. Pause expires
        time_61s = now + timedelta(seconds=61)
        assert detector.should_pause(time_61s) is False

        # 5. pause_just_expired returns True once
        assert detector.pause_just_expired() is True

        # 6. pause_just_expired returns False on subsequent calls
        assert detector.pause_just_expired() is False

        # 7. No pause active anymore
        time_120s = now + timedelta(seconds=120)
        assert detector.should_pause(time_120s) is False
        assert detector.pause_just_expired() is False

    def test_trigger_detection_during_active_pause_extends_pause(self):
        """Test that triggering detection during active pause extends the pause duration."""
        detector = OpenWindowDetector(pause_duration=60)
        now = datetime(2024, 1, 15, 10, 0, 0)

        # First trigger
        detector.trigger_detection(now)

        # 45 seconds later - trigger again (extends pause)
        time_45s = now + timedelta(seconds=45)
        detector.trigger_detection(time_45s)

        # 70 seconds from original start (25s from second trigger) - should still be paused
        time_70s = now + timedelta(seconds=70)
        assert detector.should_pause(time_70s) is True

        # 105 seconds from original start (60s from second trigger) - should still be paused
        time_105s = now + timedelta(seconds=105)
        assert detector.should_pause(time_105s) is True

        # 106 seconds from original start (61s from second trigger) - pause expires
        time_106s = now + timedelta(seconds=106)
        assert detector.should_pause(time_106s) is False


class TestOpenWindowDetectorCooldownSuppression:
    """Test OpenWindowDetector cooldown and suppression features."""

    # Cooldown tests
    def test_cooldown_prevents_retriggering(self):
        """Test that cooldown prevents rapid re-triggering of detection."""
        detector = OpenWindowDetector(cooldown=60)  # 1 minute cooldown
        now = datetime(2024, 1, 15, 10, 0, 0)

        # Set up and trigger first detection
        detector.record_temperature(now, 21.0)
        detector.record_temperature(now + timedelta(seconds=30), 20.0)
        detector.trigger_detection(now + timedelta(seconds=30))

        # 30 seconds later - in cooldown
        assert detector.in_cooldown(now + timedelta(seconds=60)) is True

        # 90 seconds later - cooldown expired
        assert detector.in_cooldown(now + timedelta(seconds=120)) is False

    def test_cooldown_blocks_check_for_drop(self):
        """Test that check_for_drop() returns False during cooldown period."""
        detector = OpenWindowDetector(cooldown=60)  # 1 minute cooldown
        now = datetime(2024, 1, 15, 10, 0, 0)

        # First detection
        detector.record_temperature(now, 21.0)
        detector.record_temperature(now + timedelta(seconds=30), 20.0)
        assert detector.check_for_drop(now + timedelta(seconds=30)) is True
        detector.trigger_detection(now + timedelta(seconds=30))

        # Add another big drop during cooldown
        detector.record_temperature(now + timedelta(seconds=45), 19.5)

        # check_for_drop should return False even though drop exists (in cooldown)
        assert detector.check_for_drop(now + timedelta(seconds=45)) is False

        # After cooldown expires, should detect drop again
        detector.record_temperature(now + timedelta(seconds=120), 19.0)
        assert detector.check_for_drop(now + timedelta(seconds=120)) is True

    def test_cooldown_default_value(self):
        """Test that cooldown defaults to DEFAULT_OWD_COOLDOWN (2700 seconds = 45 min)."""
        detector = OpenWindowDetector()  # No cooldown specified
        now = datetime(2024, 1, 15, 10, 0, 0)

        detector.trigger_detection(now)

        # Should be in cooldown after 30 minutes (1800s)
        assert detector.in_cooldown(now + timedelta(seconds=1800)) is True

        # Should be in cooldown after 44 minutes (2640s)
        assert detector.in_cooldown(now + timedelta(seconds=2640)) is True

        # Should NOT be in cooldown after 46 minutes (2760s > 2700s)
        assert detector.in_cooldown(now + timedelta(seconds=2760)) is False

    def test_cooldown_configurable(self):
        """Test that cooldown duration is configurable via constructor."""
        # Test with 120 second cooldown
        detector_120 = OpenWindowDetector(cooldown=120)
        now = datetime(2024, 1, 15, 10, 0, 0)

        detector_120.trigger_detection(now)

        # 60 seconds - in cooldown
        assert detector_120.in_cooldown(now + timedelta(seconds=60)) is True

        # 119 seconds - in cooldown
        assert detector_120.in_cooldown(now + timedelta(seconds=119)) is True

        # 121 seconds - cooldown expired
        assert detector_120.in_cooldown(now + timedelta(seconds=121)) is False

    def test_cooldown_tracks_last_detection_time(self):
        """Test that _last_detection_time tracks when last detection occurred."""
        detector = OpenWindowDetector(cooldown=60)
        now = datetime(2024, 1, 15, 10, 0, 0)

        # Initially no detection
        assert detector._last_detection_time is None

        # First trigger
        detector.trigger_detection(now)
        assert detector._last_detection_time == now

        # Second trigger updates time
        later = now + timedelta(seconds=120)
        detector.trigger_detection(later)
        assert detector._last_detection_time == later

    def test_cooldown_resets_on_new_detection(self):
        """Test that triggering new detection resets cooldown timer."""
        detector = OpenWindowDetector(cooldown=60)
        now = datetime(2024, 1, 15, 10, 0, 0)

        # First detection
        detector.trigger_detection(now)

        # 70 seconds later - cooldown expired
        time_70s = now + timedelta(seconds=70)
        assert detector.in_cooldown(time_70s) is False

        # Trigger again - resets cooldown
        detector.trigger_detection(time_70s)

        # 100 seconds from original (30s from second trigger) - in cooldown
        time_100s = now + timedelta(seconds=100)
        assert detector.in_cooldown(time_100s) is True

        # 131 seconds from original (61s from second trigger) - cooldown expired
        time_131s = now + timedelta(seconds=131)
        assert detector.in_cooldown(time_131s) is False

    def test_in_cooldown_without_prior_detection(self):
        """Test that in_cooldown() returns False when no detection has occurred."""
        detector = OpenWindowDetector(cooldown=60)
        now = datetime(2024, 1, 15, 10, 0, 0)

        # No detection triggered yet
        assert detector.in_cooldown(now) is False

    # Suppression tests
    def test_suppression_blocks_detection(self):
        """Test that suppression prevents check_for_drop() from triggering."""
        detector = OpenWindowDetector()
        now = datetime(2024, 1, 15, 10, 0, 0)

        # Suppress for 5 minutes
        detector.suppress_detection(now, duration=300)

        # Set up temp drop during suppression
        detector.record_temperature(now, 21.0)
        detector.record_temperature(now + timedelta(seconds=30), 19.5)

        # check_for_drop should return False even though drop exceeds threshold
        assert detector.check_for_drop(now + timedelta(seconds=30)) is False

    def test_suppression_duration(self):
        """Test that suppression lasts for specified duration."""
        detector = OpenWindowDetector()
        now = datetime(2024, 1, 15, 10, 0, 0)

        # Suppress for 300 seconds (5 minutes)
        detector.suppress_detection(now, duration=300)

        # 2 minutes later - still suppressed
        assert detector.is_suppressed(now + timedelta(seconds=120)) is True

        # 4.5 minutes later - still suppressed
        assert detector.is_suppressed(now + timedelta(seconds=270)) is True

        # 5.5 minutes later - suppression expired
        assert detector.is_suppressed(now + timedelta(seconds=330)) is False

    def test_suppression_tracks_suppressed_until(self):
        """Test that _suppressed_until tracks when suppression expires."""
        detector = OpenWindowDetector()
        now = datetime(2024, 1, 15, 10, 0, 0)

        # Initially not suppressed
        assert detector._suppressed_until is None

        # Suppress for 300 seconds
        detector.suppress_detection(now, duration=300)

        # Should set _suppressed_until to now + 300s
        expected_until = now + timedelta(seconds=300)
        assert detector._suppressed_until == expected_until

    def test_suppression_prevents_false_positives_after_setpoint_change(self):
        """Test suppression use case: prevent false positives during setpoint changes."""
        detector = OpenWindowDetector()
        now = datetime(2024, 1, 15, 10, 0, 0)

        # User changes setpoint from 22°C to 20°C
        # Suppress detection for 10 minutes to avoid false positive
        detector.suppress_detection(now, duration=600)

        # Temperature drops naturally from 22°C to 20.5°C
        detector.record_temperature(now, 22.0)
        detector.record_temperature(now + timedelta(seconds=60), 21.5)
        detector.record_temperature(now + timedelta(seconds=120), 21.0)
        detector.record_temperature(now + timedelta(seconds=180), 20.5)

        # Should not detect drop during suppression (even though drop = 1.5°C > threshold)
        assert detector.check_for_drop(now + timedelta(seconds=180)) is False

        # After suppression expires, detection works normally
        detector.record_temperature(now + timedelta(seconds=660), 20.0)
        # Add a new rapid drop after suppression
        detector.record_temperature(now + timedelta(seconds=690), 19.0)
        assert detector.check_for_drop(now + timedelta(seconds=690)) is True

    def test_is_suppressed_without_prior_suppression(self):
        """Test that is_suppressed() returns False when no suppression is active."""
        detector = OpenWindowDetector()
        now = datetime(2024, 1, 15, 10, 0, 0)

        # No suppression set
        assert detector.is_suppressed(now) is False

    def test_suppression_can_be_renewed(self):
        """Test that calling suppress_detection() again extends suppression."""
        detector = OpenWindowDetector()
        now = datetime(2024, 1, 15, 10, 0, 0)

        # Initial suppression for 60 seconds
        detector.suppress_detection(now, duration=60)

        # 45 seconds later - still suppressed
        time_45s = now + timedelta(seconds=45)
        assert detector.is_suppressed(time_45s) is True

        # Extend suppression for another 60 seconds from time_45s
        detector.suppress_detection(time_45s, duration=60)

        # 70 seconds from original start (25s from renewal) - still suppressed
        time_70s = now + timedelta(seconds=70)
        assert detector.is_suppressed(time_70s) is True

        # 106 seconds from original start (61s from renewal) - suppression expired
        time_106s = now + timedelta(seconds=106)
        assert detector.is_suppressed(time_106s) is False

    def test_suppression_works_independently_of_cooldown(self):
        """Test that suppression and cooldown are independent mechanisms."""
        detector = OpenWindowDetector(cooldown=60)
        now = datetime(2024, 1, 15, 10, 0, 0)

        # Suppress for 30 seconds
        detector.suppress_detection(now, duration=30)

        # Trigger detection (starts cooldown but doesn't affect suppression)
        detector.trigger_detection(now)

        # 15 seconds later - both suppressed and in cooldown
        time_15s = now + timedelta(seconds=15)
        assert detector.is_suppressed(time_15s) is True
        assert detector.in_cooldown(time_15s) is True

        # 35 seconds later - suppression expired, still in cooldown
        time_35s = now + timedelta(seconds=35)
        assert detector.is_suppressed(time_35s) is False
        assert detector.in_cooldown(time_35s) is True

        # 65 seconds later - both expired
        time_65s = now + timedelta(seconds=65)
        assert detector.is_suppressed(time_65s) is False
        assert detector.in_cooldown(time_65s) is False

    # Combined cooldown + suppression tests
    def test_check_for_drop_respects_both_cooldown_and_suppression(self):
        """Test that check_for_drop() returns False if either cooldown or suppression is active."""
        detector = OpenWindowDetector(cooldown=60)
        now = datetime(2024, 1, 15, 10, 0, 0)

        # Set up a detectable drop
        detector.record_temperature(now, 21.0)
        detector.record_temperature(now + timedelta(seconds=30), 20.0)

        # Test 1: Cooldown active
        detector.trigger_detection(now)
        assert detector.check_for_drop(now + timedelta(seconds=30)) is False

        # Test 2: Wait for cooldown to expire, then test suppression
        time_after_cooldown = now + timedelta(seconds=120)

        # Add new drop
        detector.record_temperature(time_after_cooldown, 21.0)
        detector.record_temperature(time_after_cooldown + timedelta(seconds=30), 20.0)

        # Suppress
        detector.suppress_detection(time_after_cooldown, duration=60)

        # Should not detect drop (suppressed)
        assert detector.check_for_drop(time_after_cooldown + timedelta(seconds=30)) is False

    def test_cooldown_and_suppression_lifecycle(self):
        """Test complete lifecycle of cooldown and suppression together."""
        detector = OpenWindowDetector(cooldown=120)
        now = datetime(2024, 1, 15, 10, 0, 0)

        # 1. Initial state - no cooldown, no suppression
        assert detector.in_cooldown(now) is False
        assert detector.is_suppressed(now) is False

        # 2. Trigger detection - starts cooldown
        detector.trigger_detection(now)
        assert detector.in_cooldown(now) is True
        assert detector.is_suppressed(now) is False

        # 3. Add suppression while in cooldown
        time_30s = now + timedelta(seconds=30)
        detector.suppress_detection(time_30s, duration=60)
        assert detector.in_cooldown(time_30s) is True
        assert detector.is_suppressed(time_30s) is True

        # 4. Suppression expires, cooldown still active
        time_100s = now + timedelta(seconds=100)
        assert detector.in_cooldown(time_100s) is True
        assert detector.is_suppressed(time_100s) is False

        # 5. Both expired
        time_150s = now + timedelta(seconds=150)
        assert detector.in_cooldown(time_150s) is False
        assert detector.is_suppressed(time_150s) is False


class TestOpenWindowDetectorResetClear:
    """Test OpenWindowDetector reset and clear methods."""

    def test_clear_history_empties_ring_buffer(self):
        """Test that clear_history() empties the temperature history ring buffer."""
        detector = OpenWindowDetector()
        now = datetime(2024, 1, 15, 10, 0, 0)

        # Add some temperature readings
        detector.record_temperature(now, 21.0)
        detector.record_temperature(now + timedelta(seconds=30), 20.5)
        detector.record_temperature(now + timedelta(seconds=60), 20.0)

        # Verify history has entries
        assert len(detector._temp_history) == 3

        # Clear history
        detector.clear_history()

        # Verify history is empty
        assert len(detector._temp_history) == 0

    def test_clear_history_can_be_called_on_empty_buffer(self):
        """Test that clear_history() works on empty buffer without error."""
        detector = OpenWindowDetector()

        # Clear empty buffer - should not raise
        detector.clear_history()

        # Verify still empty
        assert len(detector._temp_history) == 0

    def test_clear_history_does_not_affect_pause_state(self):
        """Test that clear_history() only clears temp history, not pause state."""
        detector = OpenWindowDetector()
        now = datetime(2024, 1, 15, 10, 0, 0)

        # Add history and trigger detection
        detector.record_temperature(now, 21.0)
        detector.trigger_detection(now)

        # Verify pause is active
        assert detector.should_pause(now) is True

        # Clear history
        detector.clear_history()

        # Verify pause state unchanged, only history cleared
        assert len(detector._temp_history) == 0
        assert detector.should_pause(now) is True

    def test_reset_clears_all_state_except_cooldown(self):
        """Test that reset() clears all state except cooldown (last_detection_time)."""
        detector = OpenWindowDetector()
        now = datetime(2024, 1, 15, 10, 0, 0)

        # Set up full state
        detector.record_temperature(now, 21.0)
        detector.record_temperature(now + timedelta(seconds=30), 20.5)
        detector.trigger_detection(now + timedelta(seconds=30))
        detector.suppress_detection(now + timedelta(seconds=30), 300)

        # Verify state is set
        assert len(detector._temp_history) == 2
        assert detector._detection_triggered is True
        assert detector._pause_start_time is not None
        assert detector._suppressed_until is not None
        assert detector._last_detection_time is not None

        # Reset
        detector.reset()

        # Verify history cleared
        assert len(detector._temp_history) == 0

        # Verify pause state cleared
        assert detector._detection_triggered is False
        assert detector._pause_start_time is None

        # Verify suppression cleared
        assert detector._suppressed_until is None

        # BUT cooldown (last_detection_time) should remain
        assert detector._last_detection_time is not None
        assert detector._last_detection_time == now + timedelta(seconds=30)

    def test_reset_on_fresh_detector(self):
        """Test that reset() works on freshly initialized detector."""
        detector = OpenWindowDetector()

        # Reset without any prior state
        detector.reset()

        # Verify all state is clean
        assert len(detector._temp_history) == 0
        assert detector._detection_triggered is False
        assert detector._pause_start_time is None
        assert detector._suppressed_until is None
        assert detector._last_detection_time is None

    def test_reset_clears_pause_expired_flags(self):
        """Test that reset() clears pause expiration flags."""
        detector = OpenWindowDetector(pause_duration=60)
        now = datetime(2024, 1, 15, 10, 0, 0)

        # Trigger and let pause expire
        detector.trigger_detection(now)
        detector.should_pause(now + timedelta(seconds=61))  # Triggers expiration

        # Verify pause expired flag is set
        assert detector.pause_just_expired() is True

        # Reset
        detector.reset()

        # Verify flags cleared
        assert detector._pause_expired_flag is False
        assert detector._expiration_detected is False

    def test_reset_preserves_cooldown_for_anti_flapping(self):
        """Test that reset() preserves cooldown to prevent rapid re-detection."""
        detector = OpenWindowDetector(cooldown=120)
        now = datetime(2024, 1, 15, 10, 0, 0)

        # Trigger detection
        detector.trigger_detection(now)

        # Verify cooldown is active
        assert detector.in_cooldown(now + timedelta(seconds=60)) is True

        # Reset
        detector.reset()

        # Cooldown should still be active (prevents rapid re-triggering)
        assert detector.in_cooldown(now + timedelta(seconds=60)) is True

        # But pause should be inactive
        assert detector.should_pause(now + timedelta(seconds=60)) is False

    def test_get_action_returns_configured_action(self):
        """Test that get_action() returns the configured action type."""
        # Test default action (pause)
        detector_default = OpenWindowDetector()
        assert detector_default.get_action() == "pause"

        # Test explicit pause action
        detector_pause = OpenWindowDetector(action="pause")
        assert detector_pause.get_action() == "pause"

        # Test frost protection action
        detector_frost = OpenWindowDetector(action="frost_protection")
        assert detector_frost.get_action() == "frost_protection"

    def test_get_action_immutable_after_init(self):
        """Test that get_action() always returns the same value after initialization."""
        detector = OpenWindowDetector(action="frost_protection")

        # Call multiple times - should return same value
        assert detector.get_action() == "frost_protection"
        assert detector.get_action() == "frost_protection"
        assert detector.get_action() == "frost_protection"

    def test_clear_history_after_setpoint_change_scenario(self):
        """Test clear_history() use case: preventing false positives during setpoint changes."""
        detector = OpenWindowDetector()
        now = datetime(2024, 1, 15, 10, 0, 0)

        # Build up history at 22°C
        for i in range(5):
            detector.record_temperature(now + timedelta(seconds=i * 30), 22.0)

        assert len(detector._temp_history) == 5

        # User changes setpoint from 22°C to 20°C
        # Clear history to avoid false detection during natural cooldown
        detector.clear_history()

        # Start fresh history at new setpoint
        detector.record_temperature(now + timedelta(seconds=180), 21.5)
        detector.record_temperature(now + timedelta(seconds=210), 21.0)

        # Only recent history should exist
        assert len(detector._temp_history) == 2
        assert detector._temp_history[0][1] == 21.5
        assert detector._temp_history[1][1] == 21.0

    def test_reset_on_hvac_off_scenario(self):
        """Test reset() use case: HVAC mode set to OFF."""
        detector = OpenWindowDetector()
        now = datetime(2024, 1, 15, 10, 0, 0)

        # Simulate active detection during heating
        detector.record_temperature(now, 21.0)
        detector.record_temperature(now + timedelta(seconds=30), 20.0)
        detector.trigger_detection(now + timedelta(seconds=30))
        detector.suppress_detection(now, 300)

        # User turns HVAC OFF
        # Reset clears all active state except cooldown
        detector.reset()

        # When HVAC turns back on, detection should start fresh
        assert len(detector._temp_history) == 0
        assert detector.should_pause(now + timedelta(seconds=60)) is False
        assert detector.is_suppressed(now + timedelta(seconds=60)) is False

        # But cooldown prevents immediate re-detection if turned back on quickly
        assert detector.in_cooldown(now + timedelta(seconds=60)) is True
