# Line Power Details

Independent line measurements (L1/L2) were unreliable or unavailable on the target
Must inverter hardware. After extensive testing it was determined that the device
does not expose separate phase data consistently, so all code and documentation
has been simplified to work with aggregate values only.

The monitor now reports only the following core metrics:

* `inverterVoltage` – overall inverter output voltage
* `inverterCurrent` – total current supplied by the inverter
* `inverterPower` – total inverter power (Watts)
* `gridVoltage`, `gridCurrent`, `gridPower` – grid interface values
* `batteryVoltage`, `batteryCurrent`, `batteryPower` – battery stats
* other normal registers (frequency, temperatures, charger states, etc.)

### Why the change?
The earlier code attempted to read L1/L2 registers and calculate phase-specific
power. The registers either returned 0, mirrored each other, or were simply
absent depending on firmware version. Maintaining that logic added complexity
without providing accurate information, so it has been removed entirely.

### Impact on existing setups
No action is required. Your existing data files and dashboard will continue to
default to total values. Any previously stored L1/L2 fields in historic logs can
be ignored or deleted; they are no longer generated.

For reference, old register numbers that were once monitored (now ignored) were:
`25247`, `25248`, `25250`, `25251`, `25258`, `25260`, `25261`, and the INT32
registers `10120/10122`.

Feel free to delete this document once you no longer need the historical context.
