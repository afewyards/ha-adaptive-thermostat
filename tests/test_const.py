"""Tests for constants in const.py."""

from custom_components.adaptive_thermostat.const import (
    HEATING_TYPE_CHARACTERISTICS,
    HEATING_TYPE_FLOOR_HYDRONIC,
    HEATING_TYPE_RADIATOR,
    HEATING_TYPE_CONVECTOR,
    HEATING_TYPE_FORCED_AIR,
    VALID_HEATING_TYPES,
    INTEGRAL_DECAY_THRESHOLDS,
    CONF_OPEN_WINDOW_DETECTION,
    CONF_OWD_TEMP_DROP,
    CONF_OWD_DETECTION_WINDOW,
    CONF_OWD_PAUSE_DURATION,
    CONF_OWD_COOLDOWN,
    CONF_OWD_ACTION,
    DEFAULT_OWD_TEMP_DROP,
    DEFAULT_OWD_DETECTION_WINDOW,
    DEFAULT_OWD_PAUSE_DURATION,
    DEFAULT_OWD_COOLDOWN,
    DEFAULT_OWD_ACTION,
    OWD_ACTION_PAUSE,
    OWD_ACTION_FROST,
    VALID_OWD_ACTIONS,
)


class TestHeatingTypeCharacteristics:
    """Test HEATING_TYPE_CHARACTERISTICS structure and values."""

    def test_heating_type_characteristics_has_decay_params(self):
        """Verify cold_tolerance, hot_tolerance, decay_exponent, max_settling_time exist for all heating types."""
        required_keys = [
            "cold_tolerance",
            "hot_tolerance",
            "decay_exponent",
            "max_settling_time",
        ]

        for heating_type in VALID_HEATING_TYPES:
            assert heating_type in HEATING_TYPE_CHARACTERISTICS, (
                f"Heating type {heating_type} missing from HEATING_TYPE_CHARACTERISTICS"
            )

            characteristics = HEATING_TYPE_CHARACTERISTICS[heating_type]

            for key in required_keys:
                assert key in characteristics, (
                    f"Heating type {heating_type} missing required key: {key}"
                )
                assert isinstance(characteristics[key], (int, float)), (
                    f"Heating type {heating_type} key {key} must be numeric, got {type(characteristics[key])}"
                )
                assert characteristics[key] > 0, (
                    f"Heating type {heating_type} key {key} must be positive, got {characteristics[key]}"
                )

    def test_floor_hydronic_decay_values(self):
        """Test floor_hydronic has correct tolerance and decay values."""
        chars = HEATING_TYPE_CHARACTERISTICS[HEATING_TYPE_FLOOR_HYDRONIC]

        assert chars["cold_tolerance"] == 0.5
        assert chars["hot_tolerance"] == 0.5
        assert chars["decay_exponent"] == 2.0
        assert chars["max_settling_time"] == 90

    def test_radiator_decay_values(self):
        """Test radiator has correct tolerance and decay values."""
        chars = HEATING_TYPE_CHARACTERISTICS[HEATING_TYPE_RADIATOR]

        assert chars["cold_tolerance"] == 0.3
        assert chars["hot_tolerance"] == 0.3
        assert chars["decay_exponent"] == 1.0
        assert chars["max_settling_time"] == 45

    def test_convector_decay_values(self):
        """Test convector has correct tolerance and decay values."""
        chars = HEATING_TYPE_CHARACTERISTICS[HEATING_TYPE_CONVECTOR]

        assert chars["cold_tolerance"] == 0.2
        assert chars["hot_tolerance"] == 0.2
        assert chars["decay_exponent"] == 1.0
        assert chars["max_settling_time"] == 30

    def test_forced_air_decay_values(self):
        """Test forced_air has correct tolerance and decay values."""
        chars = HEATING_TYPE_CHARACTERISTICS[HEATING_TYPE_FORCED_AIR]

        assert chars["cold_tolerance"] == 0.15
        assert chars["hot_tolerance"] == 0.15
        assert chars["decay_exponent"] == 0.5
        assert chars["max_settling_time"] == 15

    def test_decay_exponent_ordering(self):
        """Test that decay_exponent decreases with faster heating systems."""
        floor = HEATING_TYPE_CHARACTERISTICS[HEATING_TYPE_FLOOR_HYDRONIC]["decay_exponent"]
        radiator = HEATING_TYPE_CHARACTERISTICS[HEATING_TYPE_RADIATOR]["decay_exponent"]
        convector = HEATING_TYPE_CHARACTERISTICS[HEATING_TYPE_CONVECTOR]["decay_exponent"]
        forced_air = HEATING_TYPE_CHARACTERISTICS[HEATING_TYPE_FORCED_AIR]["decay_exponent"]

        # Slower systems (higher thermal mass) need higher decay exponents
        assert floor > radiator
        assert radiator >= convector
        assert convector > forced_air

    def test_tolerance_ordering(self):
        """Test that tolerance decreases with faster heating systems."""
        floor = HEATING_TYPE_CHARACTERISTICS[HEATING_TYPE_FLOOR_HYDRONIC]["cold_tolerance"]
        radiator = HEATING_TYPE_CHARACTERISTICS[HEATING_TYPE_RADIATOR]["cold_tolerance"]
        convector = HEATING_TYPE_CHARACTERISTICS[HEATING_TYPE_CONVECTOR]["cold_tolerance"]
        forced_air = HEATING_TYPE_CHARACTERISTICS[HEATING_TYPE_FORCED_AIR]["cold_tolerance"]

        # Slower systems get wider tolerance bands
        assert floor > radiator
        assert radiator > convector
        assert convector > forced_air

    def test_max_settling_time_ordering(self):
        """Test that max_settling_time decreases with faster heating systems."""
        floor = HEATING_TYPE_CHARACTERISTICS[HEATING_TYPE_FLOOR_HYDRONIC]["max_settling_time"]
        radiator = HEATING_TYPE_CHARACTERISTICS[HEATING_TYPE_RADIATOR]["max_settling_time"]
        convector = HEATING_TYPE_CHARACTERISTICS[HEATING_TYPE_CONVECTOR]["max_settling_time"]
        forced_air = HEATING_TYPE_CHARACTERISTICS[HEATING_TYPE_FORCED_AIR]["max_settling_time"]

        # Slower systems take longer to settle
        assert floor > radiator
        assert radiator > convector
        assert convector > forced_air


class TestIntegralDecayThresholds:
    """Test INTEGRAL_DECAY_THRESHOLDS structure and values."""

    def test_integral_decay_thresholds_exists(self):
        """Verify INTEGRAL_DECAY_THRESHOLDS dict exists."""
        assert INTEGRAL_DECAY_THRESHOLDS is not None
        assert isinstance(INTEGRAL_DECAY_THRESHOLDS, dict)

    def test_integral_decay_thresholds_has_all_heating_types(self):
        """Verify all heating types have integral decay threshold entries."""
        for heating_type in VALID_HEATING_TYPES:
            assert heating_type in INTEGRAL_DECAY_THRESHOLDS, (
                f"Heating type {heating_type} missing from INTEGRAL_DECAY_THRESHOLDS"
            )

    def test_integral_decay_thresholds_values_are_numeric(self):
        """Verify all threshold values are numeric and positive."""
        for heating_type, threshold in INTEGRAL_DECAY_THRESHOLDS.items():
            assert isinstance(threshold, (int, float)), (
                f"Threshold for {heating_type} must be numeric, got {type(threshold)}"
            )
            assert threshold > 0, (
                f"Threshold for {heating_type} must be positive, got {threshold}"
            )

    def test_integral_decay_threshold_values(self):
        """Verify specific threshold values match the specification."""
        assert INTEGRAL_DECAY_THRESHOLDS[HEATING_TYPE_FLOOR_HYDRONIC] == 30.0
        assert INTEGRAL_DECAY_THRESHOLDS[HEATING_TYPE_RADIATOR] == 40.0
        assert INTEGRAL_DECAY_THRESHOLDS[HEATING_TYPE_CONVECTOR] == 50.0
        assert INTEGRAL_DECAY_THRESHOLDS[HEATING_TYPE_FORCED_AIR] == 60.0

    def test_integral_decay_threshold_ordering(self):
        """Test that thresholds increase with faster heating systems.

        Slower systems (high thermal mass) need lower thresholds to activate
        safety net earlier, preventing prolonged overshoot.
        """
        floor = INTEGRAL_DECAY_THRESHOLDS[HEATING_TYPE_FLOOR_HYDRONIC]
        radiator = INTEGRAL_DECAY_THRESHOLDS[HEATING_TYPE_RADIATOR]
        convector = INTEGRAL_DECAY_THRESHOLDS[HEATING_TYPE_CONVECTOR]
        forced_air = INTEGRAL_DECAY_THRESHOLDS[HEATING_TYPE_FORCED_AIR]

        # Faster systems can tolerate higher thresholds before needing safety net
        assert floor < radiator
        assert radiator < convector
        assert convector < forced_air


class TestOpenWindowDetectionConstants:
    """Test Open Window Detection (OWD) configuration constants."""

    def test_owd_config_constants_defined(self):
        """Verify all OWD configuration constants are defined."""
        # Configuration key constants
        assert CONF_OPEN_WINDOW_DETECTION is not None
        assert isinstance(CONF_OPEN_WINDOW_DETECTION, str)

        assert CONF_OWD_TEMP_DROP is not None
        assert isinstance(CONF_OWD_TEMP_DROP, str)

        assert CONF_OWD_DETECTION_WINDOW is not None
        assert isinstance(CONF_OWD_DETECTION_WINDOW, str)

        assert CONF_OWD_PAUSE_DURATION is not None
        assert isinstance(CONF_OWD_PAUSE_DURATION, str)

        assert CONF_OWD_COOLDOWN is not None
        assert isinstance(CONF_OWD_COOLDOWN, str)

        assert CONF_OWD_ACTION is not None
        assert isinstance(CONF_OWD_ACTION, str)

    def test_owd_default_temp_drop(self):
        """Test default temperature drop is 0.5°C."""
        assert DEFAULT_OWD_TEMP_DROP == 0.5
        assert isinstance(DEFAULT_OWD_TEMP_DROP, (int, float))
        assert DEFAULT_OWD_TEMP_DROP > 0

    def test_owd_default_detection_window(self):
        """Test default detection window is 180 seconds (3 minutes)."""
        assert DEFAULT_OWD_DETECTION_WINDOW == 180
        assert isinstance(DEFAULT_OWD_DETECTION_WINDOW, int)
        assert DEFAULT_OWD_DETECTION_WINDOW > 0

    def test_owd_default_pause_duration(self):
        """Test default pause duration is 1800 seconds (30 minutes)."""
        assert DEFAULT_OWD_PAUSE_DURATION == 1800
        assert isinstance(DEFAULT_OWD_PAUSE_DURATION, int)
        assert DEFAULT_OWD_PAUSE_DURATION > 0

    def test_owd_default_cooldown(self):
        """Test default cooldown is 2700 seconds (45 minutes)."""
        assert DEFAULT_OWD_COOLDOWN == 2700
        assert isinstance(DEFAULT_OWD_COOLDOWN, int)
        assert DEFAULT_OWD_COOLDOWN > 0

    def test_owd_default_action(self):
        """Test default action is 'pause'."""
        assert DEFAULT_OWD_ACTION == "pause"
        assert isinstance(DEFAULT_OWD_ACTION, str)

    def test_owd_action_constants_defined(self):
        """Verify OWD action type constants are defined."""
        assert OWD_ACTION_PAUSE is not None
        assert isinstance(OWD_ACTION_PAUSE, str)
        assert OWD_ACTION_PAUSE == "pause"

        assert OWD_ACTION_FROST is not None
        assert isinstance(OWD_ACTION_FROST, str)
        assert OWD_ACTION_FROST == "frost_protection"

    def test_valid_owd_actions(self):
        """Test VALID_OWD_ACTIONS list contains expected actions."""
        assert VALID_OWD_ACTIONS is not None
        assert isinstance(VALID_OWD_ACTIONS, list)
        assert len(VALID_OWD_ACTIONS) == 2
        assert "pause" in VALID_OWD_ACTIONS
        assert "frost_protection" in VALID_OWD_ACTIONS

    def test_default_action_is_valid(self):
        """Test that the default action is in the valid actions list."""
        assert DEFAULT_OWD_ACTION in VALID_OWD_ACTIONS

    def test_owd_timing_relationships(self):
        """Test logical relationships between timing constants.

        - Detection window should be shorter than pause duration
        - Cooldown should be longer than detection window
        """
        assert DEFAULT_OWD_DETECTION_WINDOW < DEFAULT_OWD_PAUSE_DURATION, (
            "Detection window should be shorter than pause duration"
        )
        assert DEFAULT_OWD_COOLDOWN > DEFAULT_OWD_DETECTION_WINDOW, (
            "Cooldown should be longer than detection window"
        )


# Marker test
def test_const_module_exists():
    """Marker test to ensure const module is importable."""
    from custom_components.adaptive_thermostat import const
    assert const is not None
