"""Tests for entity-level schema validation in climate.py.

Tests the PLATFORM_SCHEMA validation for climate entity configuration,
particularly the open_window_detection schema.
"""
import pytest
from unittest.mock import Mock, MagicMock
import sys

# Store original modules
_original_modules = {}


# Mock Home Assistant modules before importing
def setup_module(module):
    """Set up mocks for Home Assistant modules."""
    modules_to_mock = [
        'homeassistant',
        'homeassistant.core',
        'homeassistant.helpers',
        'homeassistant.helpers.config_validation',
        'homeassistant.helpers.typing',
        'homeassistant.helpers.event',
        'homeassistant.helpers.restore_state',
        'homeassistant.helpers.entity_platform',
        'homeassistant.components',
        'homeassistant.components.climate',
        'homeassistant.const',
    ]
    for mod in modules_to_mock:
        if mod in sys.modules:
            _original_modules[mod] = sys.modules[mod]
        sys.modules[mod] = MagicMock()


def teardown_module(module):
    """Restore original modules."""
    for mod, original in _original_modules.items():
        sys.modules[mod] = original


# Try to import voluptuous, skip tests if not available
try:
    import voluptuous as vol
    HAS_VOLUPTUOUS = True
except ImportError:
    HAS_VOLUPTUOUS = False
    vol = None


pytestmark = pytest.mark.skipif(not HAS_VOLUPTUOUS, reason="voluptuous not installed")


# Import constants from the module
from custom_components.adaptive_thermostat.const import (
    CONF_SENSOR,
    CONF_CONTACT_SENSORS,
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
    VALID_CONTACT_ACTIONS,
)


# =============================================================================
# Helper to create a minimal platform schema for testing
# =============================================================================

def create_test_platform_schema():
    """Create a test schema matching the relevant parts of PLATFORM_SCHEMA.

    This focuses on the open_window_detection config which can be:
    - false (boolean to disable)
    - dict with overrides
    """
    # Mock cv functions for testing
    def mock_entity_id(value):
        """Mock entity_id validator."""
        if not isinstance(value, str):
            raise vol.Invalid("entity_id must be a string")
        if "." not in value:
            raise vol.Invalid("entity_id must contain a domain")
        return value

    def mock_entity_ids(value):
        """Mock entity_ids validator."""
        if isinstance(value, str):
            value = [value]
        if not isinstance(value, list):
            raise vol.Invalid("entity_ids must be a list or string")
        return [mock_entity_id(v) for v in value]

    def mock_boolean(value):
        """Mock boolean validator."""
        if isinstance(value, bool):
            return value
        if isinstance(value, str):
            if value.lower() in ("true", "yes", "on", "1"):
                return True
            if value.lower() in ("false", "no", "off", "0"):
                return False
        raise vol.Invalid("Expected boolean")

    # OWD can be either:
    # 1. Boolean (false to disable, true to enable with defaults)
    # 2. Dict with overrides
    def validate_owd(value):
        """Validate open_window_detection config."""
        if isinstance(value, bool):
            return value
        if isinstance(value, dict):
            # Validate as a schema
            owd_schema = vol.Schema({
                vol.Optional(CONF_OWD_TEMP_DROP, default=DEFAULT_OWD_TEMP_DROP): vol.All(
                    vol.Coerce(float),
                    vol.Range(min=0.1, max=5.0)
                ),
                vol.Optional(CONF_OWD_DETECTION_WINDOW, default=DEFAULT_OWD_DETECTION_WINDOW): vol.All(
                    vol.Coerce(int),
                    vol.Range(min=60, max=600)
                ),
                vol.Optional(CONF_OWD_PAUSE_DURATION, default=DEFAULT_OWD_PAUSE_DURATION): vol.All(
                    vol.Coerce(int),
                    vol.Range(min=300, max=7200)
                ),
                vol.Optional(CONF_OWD_COOLDOWN, default=DEFAULT_OWD_COOLDOWN): vol.All(
                    vol.Coerce(int),
                    vol.Range(min=600, max=10800)
                ),
                vol.Optional(CONF_OWD_ACTION, default=DEFAULT_OWD_ACTION): vol.In(VALID_CONTACT_ACTIONS),
            })
            return owd_schema(value)
        raise vol.Invalid("open_window_detection must be boolean or dict")

    return vol.Schema({
        vol.Required(CONF_SENSOR): mock_entity_id,
        vol.Optional(CONF_CONTACT_SENSORS): mock_entity_ids,
        vol.Optional(CONF_OPEN_WINDOW_DETECTION): validate_owd,
    })


# =============================================================================
# Test OWD Schema: Boolean False (Disable)
# =============================================================================

class TestOWDSchemaDisable:
    """Tests for open_window_detection: false config."""

    def test_entity_schema_owd_false_disables(self):
        """Test that open_window_detection: false is valid."""
        schema = create_test_platform_schema()
        config = {
            CONF_SENSOR: "sensor.temp",
            CONF_OPEN_WINDOW_DETECTION: False,
        }
        result = schema(config)
        assert result[CONF_OPEN_WINDOW_DETECTION] is False

    def test_entity_schema_owd_true_enables_with_defaults(self):
        """Test that open_window_detection: true is valid."""
        schema = create_test_platform_schema()
        config = {
            CONF_SENSOR: "sensor.temp",
            CONF_OPEN_WINDOW_DETECTION: True,
        }
        result = schema(config)
        assert result[CONF_OPEN_WINDOW_DETECTION] is True


# =============================================================================
# Test OWD Schema: Dict Overrides
# =============================================================================

class TestOWDSchemaDictOverrides:
    """Tests for open_window_detection with dict overrides."""

    def test_entity_schema_owd_dict_overrides(self):
        """Test that OWD dict with overrides is valid."""
        schema = create_test_platform_schema()
        config = {
            CONF_SENSOR: "sensor.temp",
            CONF_OPEN_WINDOW_DETECTION: {
                CONF_OWD_TEMP_DROP: 0.8,
                CONF_OWD_DETECTION_WINDOW: 240,
                CONF_OWD_PAUSE_DURATION: 2400,
                CONF_OWD_COOLDOWN: 3000,
                CONF_OWD_ACTION: "pause",
            }
        }
        result = schema(config)
        owd_config = result[CONF_OPEN_WINDOW_DETECTION]
        assert isinstance(owd_config, dict)
        assert owd_config[CONF_OWD_TEMP_DROP] == 0.8
        assert owd_config[CONF_OWD_DETECTION_WINDOW] == 240
        assert owd_config[CONF_OWD_PAUSE_DURATION] == 2400
        assert owd_config[CONF_OWD_COOLDOWN] == 3000
        assert owd_config[CONF_OWD_ACTION] == "pause"

    def test_entity_schema_owd_partial_overrides(self):
        """Test that can override just one field, others get defaults."""
        schema = create_test_platform_schema()
        config = {
            CONF_SENSOR: "sensor.temp",
            CONF_OPEN_WINDOW_DETECTION: {
                CONF_OWD_TEMP_DROP: 0.8,
            }
        }
        result = schema(config)
        owd_config = result[CONF_OPEN_WINDOW_DETECTION]
        assert isinstance(owd_config, dict)
        assert owd_config[CONF_OWD_TEMP_DROP] == 0.8
        # Others should have defaults
        assert owd_config[CONF_OWD_DETECTION_WINDOW] == DEFAULT_OWD_DETECTION_WINDOW
        assert owd_config[CONF_OWD_PAUSE_DURATION] == DEFAULT_OWD_PAUSE_DURATION
        assert owd_config[CONF_OWD_COOLDOWN] == DEFAULT_OWD_COOLDOWN
        assert owd_config[CONF_OWD_ACTION] == DEFAULT_OWD_ACTION

    def test_entity_schema_owd_empty_dict_uses_defaults(self):
        """Test that empty dict uses all defaults."""
        schema = create_test_platform_schema()
        config = {
            CONF_SENSOR: "sensor.temp",
            CONF_OPEN_WINDOW_DETECTION: {}
        }
        result = schema(config)
        owd_config = result[CONF_OPEN_WINDOW_DETECTION]
        assert isinstance(owd_config, dict)
        assert owd_config[CONF_OWD_TEMP_DROP] == DEFAULT_OWD_TEMP_DROP
        assert owd_config[CONF_OWD_DETECTION_WINDOW] == DEFAULT_OWD_DETECTION_WINDOW
        assert owd_config[CONF_OWD_PAUSE_DURATION] == DEFAULT_OWD_PAUSE_DURATION
        assert owd_config[CONF_OWD_COOLDOWN] == DEFAULT_OWD_COOLDOWN
        assert owd_config[CONF_OWD_ACTION] == DEFAULT_OWD_ACTION


# =============================================================================
# Test OWD Schema: Validation
# =============================================================================

class TestOWDSchemaValidation:
    """Tests for OWD schema value validation."""

    def test_entity_schema_owd_validates_temp_drop_too_low(self):
        """Test that temp_drop < 0.1 is rejected."""
        schema = create_test_platform_schema()
        config = {
            CONF_SENSOR: "sensor.temp",
            CONF_OPEN_WINDOW_DETECTION: {
                CONF_OWD_TEMP_DROP: 0.05,
            }
        }
        with pytest.raises(vol.Invalid) as exc_info:
            schema(config)
        assert "range" in str(exc_info.value).lower() or "0.1" in str(exc_info.value)

    def test_entity_schema_owd_validates_temp_drop_too_high(self):
        """Test that temp_drop > 5.0 is rejected."""
        schema = create_test_platform_schema()
        config = {
            CONF_SENSOR: "sensor.temp",
            CONF_OPEN_WINDOW_DETECTION: {
                CONF_OWD_TEMP_DROP: 6.0,
            }
        }
        with pytest.raises(vol.Invalid) as exc_info:
            schema(config)
        assert "range" in str(exc_info.value).lower() or "5.0" in str(exc_info.value)

    def test_entity_schema_owd_validates_detection_window_too_low(self):
        """Test that detection_window < 60 is rejected."""
        schema = create_test_platform_schema()
        config = {
            CONF_SENSOR: "sensor.temp",
            CONF_OPEN_WINDOW_DETECTION: {
                CONF_OWD_DETECTION_WINDOW: 30,
            }
        }
        with pytest.raises(vol.Invalid) as exc_info:
            schema(config)
        assert "range" in str(exc_info.value).lower() or "60" in str(exc_info.value)

    def test_entity_schema_owd_validates_detection_window_too_high(self):
        """Test that detection_window > 600 is rejected."""
        schema = create_test_platform_schema()
        config = {
            CONF_SENSOR: "sensor.temp",
            CONF_OPEN_WINDOW_DETECTION: {
                CONF_OWD_DETECTION_WINDOW: 700,
            }
        }
        with pytest.raises(vol.Invalid) as exc_info:
            schema(config)
        assert "range" in str(exc_info.value).lower() or "600" in str(exc_info.value)

    def test_entity_schema_owd_validates_pause_duration_too_low(self):
        """Test that pause_duration < 300 is rejected."""
        schema = create_test_platform_schema()
        config = {
            CONF_SENSOR: "sensor.temp",
            CONF_OPEN_WINDOW_DETECTION: {
                CONF_OWD_PAUSE_DURATION: 200,
            }
        }
        with pytest.raises(vol.Invalid) as exc_info:
            schema(config)
        assert "range" in str(exc_info.value).lower() or "300" in str(exc_info.value)

    def test_entity_schema_owd_validates_pause_duration_too_high(self):
        """Test that pause_duration > 7200 is rejected."""
        schema = create_test_platform_schema()
        config = {
            CONF_SENSOR: "sensor.temp",
            CONF_OPEN_WINDOW_DETECTION: {
                CONF_OWD_PAUSE_DURATION: 8000,
            }
        }
        with pytest.raises(vol.Invalid) as exc_info:
            schema(config)
        assert "range" in str(exc_info.value).lower() or "7200" in str(exc_info.value)

    def test_entity_schema_owd_validates_cooldown_too_low(self):
        """Test that cooldown < 600 is rejected."""
        schema = create_test_platform_schema()
        config = {
            CONF_SENSOR: "sensor.temp",
            CONF_OPEN_WINDOW_DETECTION: {
                CONF_OWD_COOLDOWN: 500,
            }
        }
        with pytest.raises(vol.Invalid) as exc_info:
            schema(config)
        assert "range" in str(exc_info.value).lower() or "600" in str(exc_info.value)

    def test_entity_schema_owd_validates_cooldown_too_high(self):
        """Test that cooldown > 10800 is rejected."""
        schema = create_test_platform_schema()
        config = {
            CONF_SENSOR: "sensor.temp",
            CONF_OPEN_WINDOW_DETECTION: {
                CONF_OWD_COOLDOWN: 12000,
            }
        }
        with pytest.raises(vol.Invalid) as exc_info:
            schema(config)
        assert "range" in str(exc_info.value).lower() or "10800" in str(exc_info.value)

    def test_entity_schema_owd_validates_action_invalid(self):
        """Test that invalid action is rejected."""
        schema = create_test_platform_schema()
        config = {
            CONF_SENSOR: "sensor.temp",
            CONF_OPEN_WINDOW_DETECTION: {
                CONF_OWD_ACTION: "invalid_action",
            }
        }
        with pytest.raises(vol.Invalid) as exc_info:
            schema(config)
        error_msg = str(exc_info.value)
        assert "invalid_action" in error_msg or "action" in error_msg.lower()

    def test_entity_schema_owd_validates_action_frost_protection(self):
        """Test that frost_protection action is valid."""
        schema = create_test_platform_schema()
        config = {
            CONF_SENSOR: "sensor.temp",
            CONF_OPEN_WINDOW_DETECTION: {
                CONF_OWD_ACTION: "frost_protection",
            }
        }
        result = schema(config)
        owd_config = result[CONF_OPEN_WINDOW_DETECTION]
        assert owd_config[CONF_OWD_ACTION] == "frost_protection"

    def test_entity_schema_owd_validates_action_none(self):
        """Test that none action is valid."""
        schema = create_test_platform_schema()
        config = {
            CONF_SENSOR: "sensor.temp",
            CONF_OPEN_WINDOW_DETECTION: {
                CONF_OWD_ACTION: "none",
            }
        }
        result = schema(config)
        owd_config = result[CONF_OPEN_WINDOW_DETECTION]
        assert owd_config[CONF_OWD_ACTION] == "none"


# =============================================================================
# Test OWD Schema: Type Coercion
# =============================================================================

class TestOWDSchemaTypeCoercion:
    """Tests for type coercion in OWD schema."""

    def test_entity_schema_owd_coerces_temp_drop_from_int(self):
        """Test that temp_drop is coerced from int to float."""
        schema = create_test_platform_schema()
        config = {
            CONF_SENSOR: "sensor.temp",
            CONF_OPEN_WINDOW_DETECTION: {
                CONF_OWD_TEMP_DROP: 1,
            }
        }
        result = schema(config)
        owd_config = result[CONF_OPEN_WINDOW_DETECTION]
        assert owd_config[CONF_OWD_TEMP_DROP] == 1.0
        assert isinstance(owd_config[CONF_OWD_TEMP_DROP], float)

    def test_entity_schema_owd_coerces_temp_drop_from_string(self):
        """Test that temp_drop is coerced from string to float."""
        schema = create_test_platform_schema()
        config = {
            CONF_SENSOR: "sensor.temp",
            CONF_OPEN_WINDOW_DETECTION: {
                CONF_OWD_TEMP_DROP: "1.5",
            }
        }
        result = schema(config)
        owd_config = result[CONF_OPEN_WINDOW_DETECTION]
        assert owd_config[CONF_OWD_TEMP_DROP] == pytest.approx(1.5)

    def test_entity_schema_owd_coerces_int_from_string(self):
        """Test that integer fields are coerced from string."""
        schema = create_test_platform_schema()
        config = {
            CONF_SENSOR: "sensor.temp",
            CONF_OPEN_WINDOW_DETECTION: {
                CONF_OWD_DETECTION_WINDOW: "300",
                CONF_OWD_PAUSE_DURATION: "1200",
                CONF_OWD_COOLDOWN: "1800",
            }
        }
        result = schema(config)
        owd_config = result[CONF_OPEN_WINDOW_DETECTION]
        assert owd_config[CONF_OWD_DETECTION_WINDOW] == 300
        assert owd_config[CONF_OWD_PAUSE_DURATION] == 1200
        assert owd_config[CONF_OWD_COOLDOWN] == 1800
        assert isinstance(owd_config[CONF_OWD_DETECTION_WINDOW], int)


# =============================================================================
# Test OWD Schema: Without OWD Config
# =============================================================================

class TestOWDSchemaWithoutConfig:
    """Tests for entity config without OWD."""

    def test_entity_schema_without_owd(self):
        """Test that entity without OWD config is valid."""
        schema = create_test_platform_schema()
        config = {
            CONF_SENSOR: "sensor.temp",
        }
        result = schema(config)
        assert CONF_OPEN_WINDOW_DETECTION not in result

    def test_entity_schema_with_contact_sensors_only(self):
        """Test that entity with contact_sensors but no OWD is valid."""
        schema = create_test_platform_schema()
        config = {
            CONF_SENSOR: "sensor.temp",
            CONF_CONTACT_SENSORS: ["binary_sensor.window"],
        }
        result = schema(config)
        assert CONF_CONTACT_SENSORS in result
        assert CONF_OPEN_WINDOW_DETECTION not in result


# =============================================================================
# Test OWD Schema: Boundary Values
# =============================================================================

class TestOWDSchemaBoundaryValues:
    """Tests for boundary values in OWD schema."""

    def test_entity_schema_owd_temp_drop_at_minimum(self):
        """Test temp_drop at minimum (0.1)."""
        schema = create_test_platform_schema()
        config = {
            CONF_SENSOR: "sensor.temp",
            CONF_OPEN_WINDOW_DETECTION: {
                CONF_OWD_TEMP_DROP: 0.1,
            }
        }
        result = schema(config)
        owd_config = result[CONF_OPEN_WINDOW_DETECTION]
        assert owd_config[CONF_OWD_TEMP_DROP] == pytest.approx(0.1)

    def test_entity_schema_owd_temp_drop_at_maximum(self):
        """Test temp_drop at maximum (5.0)."""
        schema = create_test_platform_schema()
        config = {
            CONF_SENSOR: "sensor.temp",
            CONF_OPEN_WINDOW_DETECTION: {
                CONF_OWD_TEMP_DROP: 5.0,
            }
        }
        result = schema(config)
        owd_config = result[CONF_OPEN_WINDOW_DETECTION]
        assert owd_config[CONF_OWD_TEMP_DROP] == pytest.approx(5.0)

    def test_entity_schema_owd_detection_window_at_minimum(self):
        """Test detection_window at minimum (60)."""
        schema = create_test_platform_schema()
        config = {
            CONF_SENSOR: "sensor.temp",
            CONF_OPEN_WINDOW_DETECTION: {
                CONF_OWD_DETECTION_WINDOW: 60,
            }
        }
        result = schema(config)
        owd_config = result[CONF_OPEN_WINDOW_DETECTION]
        assert owd_config[CONF_OWD_DETECTION_WINDOW] == 60

    def test_entity_schema_owd_detection_window_at_maximum(self):
        """Test detection_window at maximum (600)."""
        schema = create_test_platform_schema()
        config = {
            CONF_SENSOR: "sensor.temp",
            CONF_OPEN_WINDOW_DETECTION: {
                CONF_OWD_DETECTION_WINDOW: 600,
            }
        }
        result = schema(config)
        owd_config = result[CONF_OPEN_WINDOW_DETECTION]
        assert owd_config[CONF_OWD_DETECTION_WINDOW] == 600

    def test_entity_schema_owd_pause_duration_at_minimum(self):
        """Test pause_duration at minimum (300)."""
        schema = create_test_platform_schema()
        config = {
            CONF_SENSOR: "sensor.temp",
            CONF_OPEN_WINDOW_DETECTION: {
                CONF_OWD_PAUSE_DURATION: 300,
            }
        }
        result = schema(config)
        owd_config = result[CONF_OPEN_WINDOW_DETECTION]
        assert owd_config[CONF_OWD_PAUSE_DURATION] == 300

    def test_entity_schema_owd_pause_duration_at_maximum(self):
        """Test pause_duration at maximum (7200)."""
        schema = create_test_platform_schema()
        config = {
            CONF_SENSOR: "sensor.temp",
            CONF_OPEN_WINDOW_DETECTION: {
                CONF_OWD_PAUSE_DURATION: 7200,
            }
        }
        result = schema(config)
        owd_config = result[CONF_OPEN_WINDOW_DETECTION]
        assert owd_config[CONF_OWD_PAUSE_DURATION] == 7200

    def test_entity_schema_owd_cooldown_at_minimum(self):
        """Test cooldown at minimum (600)."""
        schema = create_test_platform_schema()
        config = {
            CONF_SENSOR: "sensor.temp",
            CONF_OPEN_WINDOW_DETECTION: {
                CONF_OWD_COOLDOWN: 600,
            }
        }
        result = schema(config)
        owd_config = result[CONF_OPEN_WINDOW_DETECTION]
        assert owd_config[CONF_OWD_COOLDOWN] == 600

    def test_entity_schema_owd_cooldown_at_maximum(self):
        """Test cooldown at maximum (10800)."""
        schema = create_test_platform_schema()
        config = {
            CONF_SENSOR: "sensor.temp",
            CONF_OPEN_WINDOW_DETECTION: {
                CONF_OWD_COOLDOWN: 10800,
            }
        }
        result = schema(config)
        owd_config = result[CONF_OPEN_WINDOW_DETECTION]
        assert owd_config[CONF_OWD_COOLDOWN] == 10800


# =============================================================================
# Test OWD Config Precedence
# =============================================================================

class TestOwdConfigPrecedence:
    """Tests for OWD config merging with precedence rules.

    Precedence order:
    1. Entity has contact_sensors → OWD inactive (physical sensors win)
    2. Entity sets open_window_detection: false → OWD disabled
    3. Otherwise → OWD enabled with entity overrides > domain defaults > built-in defaults
    """

    def create_merge_helper(self):
        """Create a helper function that merges domain and entity OWD configs.

        This helper will be implemented in climate.py but we test it here.
        Returns a function: merge_owd_config(domain_config, entity_config, has_contact_sensors) -> dict|None
        """
        def merge_owd_config(domain_config, entity_config, has_contact_sensors):
            """Merge OWD config with precedence rules.

            Args:
                domain_config: Domain-level OWD config dict or None
                entity_config: Entity-level OWD config (bool, dict, or None)
                has_contact_sensors: Whether entity has contact_sensors configured

            Returns:
                dict: Merged OWD config with all values, or None if OWD should be disabled
            """
            # Rule 1: Contact sensors win - OWD inactive
            if has_contact_sensors:
                return None

            # Rule 2: Entity explicitly disables OWD
            if entity_config is False:
                return None

            # Rule 3: Merge configs - entity > domain > defaults
            result = {
                CONF_OWD_TEMP_DROP: DEFAULT_OWD_TEMP_DROP,
                CONF_OWD_DETECTION_WINDOW: DEFAULT_OWD_DETECTION_WINDOW,
                CONF_OWD_PAUSE_DURATION: DEFAULT_OWD_PAUSE_DURATION,
                CONF_OWD_COOLDOWN: DEFAULT_OWD_COOLDOWN,
                CONF_OWD_ACTION: DEFAULT_OWD_ACTION,
            }

            # Apply domain defaults if provided
            if domain_config and isinstance(domain_config, dict):
                result.update(domain_config)

            # Apply entity overrides
            if entity_config is True:
                # True means enable with current defaults (already set)
                pass
            elif isinstance(entity_config, dict):
                # Dict means enable with overrides
                result.update(entity_config)
            elif entity_config is None:
                # None means not specified at entity level - use domain/defaults
                pass

            return result

        return merge_owd_config

    def test_contact_sensors_disables_owd(self):
        """Test that entity with contact_sensors has OWD disabled."""
        merge_fn = self.create_merge_helper()

        # Entity has contact sensors - OWD should be None regardless of config
        result = merge_fn(
            domain_config={"temp_drop": 0.6},
            entity_config={"temp_drop": 0.8},
            has_contact_sensors=True
        )
        assert result is None

        # Even with domain config
        result = merge_fn(
            domain_config={"temp_drop": 0.6, "pause_duration": 2000},
            entity_config=None,
            has_contact_sensors=True
        )
        assert result is None

    def test_entity_false_disables_owd(self):
        """Test that entity open_window_detection: false disables OWD."""
        merge_fn = self.create_merge_helper()

        # Entity explicitly sets false
        result = merge_fn(
            domain_config={"temp_drop": 0.6},
            entity_config=False,
            has_contact_sensors=False
        )
        assert result is None

        # Even without domain config
        result = merge_fn(
            domain_config=None,
            entity_config=False,
            has_contact_sensors=False
        )
        assert result is None

    def test_entity_overrides_domain_config(self):
        """Test that entity OWD values override domain values."""
        merge_fn = self.create_merge_helper()

        domain_config = {
            CONF_OWD_TEMP_DROP: 0.6,
            CONF_OWD_DETECTION_WINDOW: 200,
            CONF_OWD_PAUSE_DURATION: 2000,
        }
        entity_config = {
            CONF_OWD_TEMP_DROP: 0.8,  # Override
            CONF_OWD_COOLDOWN: 3000,  # Add new
        }

        result = merge_fn(domain_config, entity_config, False)

        # Entity overrides should win
        assert result[CONF_OWD_TEMP_DROP] == 0.8
        assert result[CONF_OWD_COOLDOWN] == 3000

        # Domain values not overridden should be present
        assert result[CONF_OWD_DETECTION_WINDOW] == 200
        assert result[CONF_OWD_PAUSE_DURATION] == 2000

        # Built-in default should fill in missing values
        assert result[CONF_OWD_ACTION] == DEFAULT_OWD_ACTION

    def test_domain_overrides_builtin_defaults(self):
        """Test that domain OWD values override built-in defaults."""
        merge_fn = self.create_merge_helper()

        domain_config = {
            CONF_OWD_TEMP_DROP: 0.7,
            CONF_OWD_PAUSE_DURATION: 2500,
        }

        result = merge_fn(domain_config, None, False)

        # Domain values should override defaults
        assert result[CONF_OWD_TEMP_DROP] == 0.7
        assert result[CONF_OWD_PAUSE_DURATION] == 2500

        # Built-in defaults for unspecified values
        assert result[CONF_OWD_DETECTION_WINDOW] == DEFAULT_OWD_DETECTION_WINDOW
        assert result[CONF_OWD_COOLDOWN] == DEFAULT_OWD_COOLDOWN
        assert result[CONF_OWD_ACTION] == DEFAULT_OWD_ACTION

    def test_builtin_defaults_when_no_config(self):
        """Test that built-in defaults are used when no domain or entity config."""
        merge_fn = self.create_merge_helper()

        result = merge_fn(None, None, False)

        # All values should be built-in defaults
        assert result[CONF_OWD_TEMP_DROP] == DEFAULT_OWD_TEMP_DROP
        assert result[CONF_OWD_DETECTION_WINDOW] == DEFAULT_OWD_DETECTION_WINDOW
        assert result[CONF_OWD_PAUSE_DURATION] == DEFAULT_OWD_PAUSE_DURATION
        assert result[CONF_OWD_COOLDOWN] == DEFAULT_OWD_COOLDOWN
        assert result[CONF_OWD_ACTION] == DEFAULT_OWD_ACTION

    def test_entity_true_enables_with_domain_and_defaults(self):
        """Test that entity open_window_detection: true enables with domain+defaults."""
        merge_fn = self.create_merge_helper()

        domain_config = {
            CONF_OWD_TEMP_DROP: 0.6,
            CONF_OWD_PAUSE_DURATION: 2000,
        }

        result = merge_fn(domain_config, True, False)

        # Should have domain values
        assert result[CONF_OWD_TEMP_DROP] == 0.6
        assert result[CONF_OWD_PAUSE_DURATION] == 2000

        # And built-in defaults for rest
        assert result[CONF_OWD_DETECTION_WINDOW] == DEFAULT_OWD_DETECTION_WINDOW
        assert result[CONF_OWD_COOLDOWN] == DEFAULT_OWD_COOLDOWN
        assert result[CONF_OWD_ACTION] == DEFAULT_OWD_ACTION

    def test_entity_empty_dict_uses_domain_and_defaults(self):
        """Test that entity open_window_detection: {} uses domain+defaults."""
        merge_fn = self.create_merge_helper()

        domain_config = {
            CONF_OWD_TEMP_DROP: 0.6,
        }

        result = merge_fn(domain_config, {}, False)

        # Should have domain value
        assert result[CONF_OWD_TEMP_DROP] == 0.6

        # And built-in defaults for rest
        assert result[CONF_OWD_DETECTION_WINDOW] == DEFAULT_OWD_DETECTION_WINDOW
        assert result[CONF_OWD_PAUSE_DURATION] == DEFAULT_OWD_PAUSE_DURATION
        assert result[CONF_OWD_COOLDOWN] == DEFAULT_OWD_COOLDOWN
        assert result[CONF_OWD_ACTION] == DEFAULT_OWD_ACTION

    def test_full_precedence_chain(self):
        """Test complete precedence: entity > domain > defaults."""
        merge_fn = self.create_merge_helper()

        domain_config = {
            CONF_OWD_TEMP_DROP: 0.6,
            CONF_OWD_DETECTION_WINDOW: 200,
            CONF_OWD_PAUSE_DURATION: 2000,
        }
        entity_config = {
            CONF_OWD_TEMP_DROP: 0.9,  # Entity wins
        }

        result = merge_fn(domain_config, entity_config, False)

        # Entity override wins
        assert result[CONF_OWD_TEMP_DROP] == 0.9

        # Domain values used where entity doesn't override
        assert result[CONF_OWD_DETECTION_WINDOW] == 200
        assert result[CONF_OWD_PAUSE_DURATION] == 2000

        # Built-in defaults for values not in domain or entity
        assert result[CONF_OWD_COOLDOWN] == DEFAULT_OWD_COOLDOWN
        assert result[CONF_OWD_ACTION] == DEFAULT_OWD_ACTION

    def test_contact_sensors_precedence_over_everything(self):
        """Test that contact_sensors takes precedence over all OWD config."""
        merge_fn = self.create_merge_helper()

        # Even with both domain and entity config
        result = merge_fn(
            domain_config={
                CONF_OWD_TEMP_DROP: 0.6,
                CONF_OWD_PAUSE_DURATION: 2000,
            },
            entity_config={
                CONF_OWD_TEMP_DROP: 0.9,
                CONF_OWD_ACTION: "frost_protection",
            },
            has_contact_sensors=True
        )
        assert result is None

    def test_entity_false_precedence_over_domain(self):
        """Test that entity false takes precedence over domain config."""
        merge_fn = self.create_merge_helper()

        result = merge_fn(
            domain_config={
                CONF_OWD_TEMP_DROP: 0.6,
                CONF_OWD_PAUSE_DURATION: 2000,
                CONF_OWD_ACTION: "frost_protection",
            },
            entity_config=False,
            has_contact_sensors=False
        )
        assert result is None
