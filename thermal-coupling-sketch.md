# Thermal Coupling Learning - Rough Sketch

## Core Idea

Learn heat transfer coefficients between zones by observing temperature changes when only one zone heats.

```
Zone A heats: ΔT_A = +2.0°C over 30 min
Zone B idle:  ΔT_B = +0.6°C over same period
Coupling A→B: 0.6 / 2.0 = 0.30 (30% heat transfer)
```

## Data Already Available

Per zone via Coordinator.get_all_zones():
- `cycle_tracker.temperature_history` → list[(timestamp, temp)]
- `cycle_tracker.state` → IDLE | HEATING | SETTLING
- `cycle_tracker.cycle_start_time` → when heating began
- `adaptive_learner.cycle_history` → last 50 CycleMetrics

## Learning Algorithm

```python
# When zone A completes a heating cycle:
def analyze_coupling(zone_a_id: str, cycle: CycleMetrics) -> dict[str, float]:
    couplings = {}

    for zone_b_id, zone_b_data in coordinator.get_all_zones().items():
        if zone_b_id == zone_a_id:
            continue

        # Only analyze if B was idle during A's heating
        if zone_b_was_heating_during(zone_a_cycle_window):
            continue

        # Get B's temperature change during A's heating window
        delta_t_b = get_temp_change(zone_b, zone_a_cycle_window)
        delta_t_a = zone_a_rise  # from CycleMetrics

        # Filter out noise
        if abs(delta_t_b) < 0.1:  # below sensor precision
            continue

        # Compute coupling coefficient
        coupling = delta_t_b / delta_t_a
        couplings[zone_b_id] = coupling

    return couplings
```

## Storage Structure

```python
# New: ThermalCouplingManager
class ThermalCouplingManager:
    # Learned coupling coefficients (directional)
    _couplings: dict[tuple[str, str], list[float]]
    # e.g., ("living_room", "bedroom_upstairs"): [0.28, 0.32, 0.30, ...]

    def get_coupling(self, from_zone: str, to_zone: str) -> float:
        """Returns averaged coupling coefficient."""
        samples = self._couplings.get((from_zone, to_zone), [])
        if len(samples) < MIN_SAMPLES:
            return 0.0  # Not enough data
        return robust_average(samples)  # Reject outliers

    def add_observation(self, from_zone: str, to_zone: str, coupling: float):
        """Add new coupling observation."""
        key = (from_zone, to_zone)
        self._couplings.setdefault(key, []).append(coupling)
        # Keep last N observations (e.g., 20)
```

## What Coupling Data Enables

### 1. Smarter Zone Linking (immediate value)
```python
# Current: fixed delay when linked zone heats
# New: delay proportional to coupling strength

if coupling > 0.3:  # Strong coupling
    delay_heating(zone_b, until=zone_a_settles)
elif coupling > 0.15:  # Moderate coupling
    reduce_setpoint_temporarily(zone_b, by=coupling * expected_rise)
```

### 2. Learning Correction (filter spillover noise)
```python
# When analyzing zone B's cycle:
spillover = sum(
    coupling(a, b) * zone_a_output
    for a in heating_neighbors
)
adjusted_rise = observed_rise - spillover
# Use adjusted_rise for PID tuning decisions
```

### 3. Predictive Pre-heating
```python
# If living room will heat soon, upstairs can delay
# because it'll get ~30% of that heat for free
expected_spillover = coupling * predicted_rise_in_source
if expected_spillover > (setpoint - current_temp):
    skip_heating_cycle()
```

### 4. Asymmetric Coupling Detection (stairwell)
```python
coupling_up = get_coupling("living_room", "bedroom_upstairs")   # 0.35
coupling_down = get_coupling("bedroom_upstairs", "living_room") # 0.10
# Asymmetry indicates stack effect - heat rises more than falls
```

## Integration Points

```
┌─────────────────┐     cycle completes     ┌──────────────────────┐
│ CycleTracker    │ ───────────────────────▶│ ThermalCouplingMgr   │
│ (per zone)      │                         │ (in Coordinator)     │
└─────────────────┘                         └──────────┬───────────┘
                                                       │
        ┌──────────────────────────────────────────────┼───────────┐
        │                                              │           │
        ▼                                              ▼           ▼
┌───────────────┐                           ┌──────────────┐ ┌───────────┐
│ ZoneLinker    │                           │ Adaptive     │ │ Demand    │
│ (smart delay) │                           │ Learner      │ │ Aggregator│
└───────────────┘                           │ (filter      │ └───────────┘
                                            │  spillover)  │
                                            └──────────────┘
```

## Design Decisions

- **No persistence**: Rebuild coupling coefficients from cycle history on restart
- **Pure learning**: No manual configuration, system discovers all couplings automatically
- **Stairwell detection**: Inferred from asymmetric coupling (up >> down)

## Filtering Requirements

Only use coupling observations when:
- Source zone completed a clean cycle (not interrupted)
- Target zone was idle throughout (no own heating)
- No major disturbances (solar gain, contact sensors)
- Outdoor temp stable (|ΔT_outdoor| < 2°C during window)
- Similar setpoints (within 1°C) - controls for intentional differences

## Minimum Viable Version

1. Add `ThermalCouplingManager` to Coordinator
2. Hook into cycle completion callback
3. Compute and store coupling observations
4. Expose via sensor entities for visibility
5. Use in ZoneLinker for smarter delays

Later iterations:
- Learning correction in AdaptiveLearner
- Predictive pre-heating logic
- Stairwell detection and special handling

---

## Open Questions

1. **Observation window**: Use full heating phase, or just the rise portion before settling?
2. **Outdoor compensation**: Subtract Ke-predicted change from observed change before computing coupling?
3. **Minimum samples**: How many observations before trusting the coupling value? (suggest: 5)
4. **Decay**: Should old observations be weighted less, or just use rolling window?
