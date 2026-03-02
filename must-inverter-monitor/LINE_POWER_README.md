# Individual Line Power Reading - Must 3300 6kw

## Overview
Your inverter monitor has been updated to read and calculate **independent power values for each output line** (Line 1 and Line 2). This provides more accurate monitoring than relying on combined/total current readings.

## New Registers Added

### Inverter Output (What Your Battery/System Produces)
- **Register 25247**: `inverterVoltageL1` - Line 1 voltage (0.1V resolution)
- **Register 25248**: `inverterVoltageL2` - Line 2 voltage (0.1V resolution)
- **Register 25250**: `inverterCurrentL1` - Line 1 current (0.1A resolution)
- **Register 25251**: `inverterCurrentL2` - Line 2 current (0.1A resolution)

### Load Output (What Your House Consumes)
- **Register 25257**: `loadVoltageL1` - Line 1 voltage to load (0.1V resolution)
- **Register 25258**: `loadVoltageL2` - Line 2 voltage to load (0.1V resolution)
- **Register 25260**: `loadCurrentL1` - Line 1 current to load (0.1A resolution)
- **Register 25261**: `loadCurrentL2` - Line 2 current to load (0.1A resolution)

## New Calculated Metrics

### Individual Line Power (Inverter Output)
```json
"inverterPowerL1": 330.0,  // Line 1 power in Watts (V × I)
"inverterPowerL2": 285.5,  // Line 2 power in Watts
"inverterPowerTotal": 615.5 // Total from both lines
```

### Individual Line Power (Load Consumption)
```json
"loadPowerL1": 275.0,       // Line 1 load power in Watts
"loadPowerL2": 295.8,       // Line 2 load power in Watts
"loadPowerTotal": 570.8     // Total consumption from both lines
```

### Phase Imbalance Indicators
```json
"inverterPhaseImbalancePercent": 7.3,  // Imbalance between L1 and L2 output
"loadPhaseImbalancePercent": 3.6       // Imbalance between L1 and L2 load
```

## Example JSON Output

```json
{
  "timestamp": "2026-03-01T12:30:45.123456",
  
  // Individual line voltages
  "inverterVoltageL1": 110.5,
  "inverterVoltageL2": 109.8,
  "loadVoltageL1": 110.3,
  "loadVoltageL2": 109.9,
  
  // Individual line currents
  "inverterCurrentL1": 3.0,
  "inverterCurrentL2": 2.6,
  "loadCurrentL1": 2.5,
  "loadCurrentL2": 2.7,
  
  // Calculated individual line power
  "inverterPowerL1": 331.5,
  "inverterPowerL2": 285.5,
  "inverterPowerTotal": 617.0,
  
  "loadPowerL1": 275.75,
  "loadPowerL2": 296.73,
  "loadPowerTotal": 572.48,
  
  // Balance analysis
  "inverterPhaseImbalancePercent": 7.33,
  "loadPhaseImbalancePercent": 3.5,
  
  // Legacy total values (still available)
  "inverterPower": 617,
  "loadPower": 573,
  "inverterVoltage": 110.2,
  "inverterCurrent": 5.6
}
```

## Understanding The Data

### Ideal Scenario
- Both lines have balanced voltage (~110V each)
- Both lines share load equally (similar power values)
- Phase imbalance is < 10%

### Example Readings for Your 3kW per Line Setup
- **Line 1 at max capacity**: 110V × 27.3A ≈ 3000W
- **Line 2 at max capacity**: 110V × 27.3A ≈ 3000W
- **Total capacity**: ~6000W (matches your 6kw inverter spec)

## Use Cases

1. **Load Balancing**: Distribute appliances across both lines to minimize imbalance
2. **Line Monitoring**: Detect if one line is overloaded or experiencing issues
3. **Efficiency**: Identify which line is consuming more from solar/battery
4. **Diagnostics**: Track voltage stability per line for troubleshooting

## Legacy Data Still Available
Your existing metrics still work:
- `inverterVoltage` - Average voltage
- `inverterCurrent` - Combined current (sum of both lines)
- `inverterPower` - Total power
- `powerL1`, `powerL2` - Calculated from INT32 registers 10120/10122 (optional legacy method)

## Configuration Notes
- The inverter reads these registers every 10 seconds (configurable in `INTERVAL`)
- All power calculations use the formula: **Power (W) = Voltage (V) × Current (A)**
- Voltage and current values are scaled by the inverter (0.1 resolution)
- Negative power indicates reverse (battery charging, feeding to grid)
