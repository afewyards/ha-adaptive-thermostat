# Plan: Add `supply_type` Configuration

## HVAC Engineering Verdict

**The feature is valuable.** Heat generation source has fundamentally different operational characteristics than heat distribution (`heating_type`). Current system treats all sources identically with generic 30s delay - this is wrong for most supply types.

## Key Operational Differences by Supply Type

| Supply Type | Startup | Min ON | Min OFF | Cycling Tolerance |
|-------------|---------|--------|---------|-------------------|
| `heatpump` | 45s | 10 min | 5 min | Very poor (compressor wear) |
| `district` | 5s | 0 | 0 | Excellent |
| `gas_boiler` | 60s | 3 min | 2 min | Moderate |
| `oil_boiler` | 90s | 5 min | 3 min | Poor |
| `electric_boiler` | 5s | 0 | 0 | Excellent |
| `pellet_boiler` | 10 min | 30 min | 10 min | Very poor |

**Most impactful change:** Enforcing min on/off times at central controller level to protect equipment (especially heat pumps and pellet boilers).

## MVP Scope (80/20)

```yaml
adaptive_thermostat:
  supply_type: heatpump  # Derives all defaults from this
  main_heater_switch: switch.heat_pump
  # Optional overrides:
  # source_min_on_time: 900  # Override default
  # source_min_off_time: 300
```

**What MVP includes:**
1. `supply_type` enum in domain config
2. Auto-derived `source_startup_delay` from type
3. **New:** `source_min_on_time` enforcement at central controller
4. **New:** `source_min_off_time` enforcement at central controller
5. All params user-overridable

**What MVP defers:**
- Demand aggregation strategies (min zones before startup)
- COP optimization for heat pumps
- Buffer tank awareness
- Hybrid system support
- Defrost cycle detection

## Implementation

### Files to Modify

1. **`const.py`** - Add `SUPPLY_TYPE_CHARACTERISTICS` lookup:
   ```python
   SUPPLY_TYPE_CHARACTERISTICS = {
       "heatpump": {"startup_delay": 45, "min_on": 600, "min_off": 300},
       "district": {"startup_delay": 5, "min_on": 0, "min_off": 0},
       # ...
   }
   ```

2. **`__init__.py`** - Add `CONF_SUPPLY_TYPE` to domain schema, wire to CentralController, add validation warnings for unsafe overrides

3. **`central_controller.py`** - Add min on/off enforcement:
   - Track last state change timestamp
   - In `_update_heater()`: if ON and `now - last_on < min_on_time`, defer turn-off
   - In `_update_heater()`: if OFF and `now - last_off < min_off_time`, defer turn-on

4. **`tests/test_central_controller.py`** - Add tests for min cycle enforcement

## Design Decisions

1. **Hybrid systems** - Not in MVP. Single supply_type only.
2. **Override precedence** - Explicit overrides win, but log warning if override seems unsafe for supply type
3. **Zone PWM interaction** - No. Keep supply_type separate from zone-level control.

## Verification

1. Unit tests for min cycle enforcement in `test_central_controller.py`
2. Integration test: simulate rapid demand changes, verify source respects min times
3. Manual test: configure `supply_type: heatpump`, observe startup delay and min cycle behavior in HA logs
