import minimalmodbus
import time
import os
import logging
import json
from datetime import datetime
from dotenv import load_dotenv
from logging.handlers import RotatingFileHandler

# ==============================
# LOAD ENVIRONMENT VARIABLES
# ==============================
load_dotenv()

SERPORT = os.getenv("SERPORT")
SERTIMEOUT = float(os.getenv("SERTIMEOUT", 1))
SERBAUD = int(os.getenv("SERBAUD", 9600))
INTERVAL = int(os.getenv("INTERVAL", 10))

OUTPUT_FILE = "inverter_data.json"

# ==============================
# LOGGING SETUP
# ==============================
os.makedirs("logs", exist_ok=True)

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s | %(levelname)s | %(message)s",
    handlers=[
        logging.StreamHandler(),
        RotatingFileHandler(
            filename="logs/must_inverter_monitor.log",
            maxBytes=1_000_000,
            backupCount=5,
        ),
    ],
)

# ==============================
# REGISTER MAP
# ==============================
register_map = {
    25201: ["workState", "Work state", 1, "map", {
        0: "PowerOn", 1: "SelfTest", 2: "OffGrid",
        3: "Grid-Tie", 4: "Bypass", 5: "Stop",
        6: "Grid Charging"
    }],
    25205: ["batteryVoltage", "Battery voltage", 0.1, "V"],
    25206: ["inverterVoltage", "Inverter voltage", 0.1, "V"],
    25207: ["gridVoltage", "Grid voltage", 0.1, "V"],
    25210: ["inverterCurrent", "Inverter current", 0.1, "A"],
    25211: ["gridCurrent", "Grid current", 0.1, "A"],
    25213: ["inverterPower", "Inverter power", 1, "W"],
    25214: ["gridPower", "Grid power", 1, "W"],
    25215: ["loadPower", "Load power", 1, "W"],
    25216: ["loadPercent", "Load percent", 1, "%"],
    25225: ["inverterFrequency", "Inverter frequency", 0.01, "Hz"],
    25226: ["gridFrequency", "Grid frequency", 0.01, "Hz"],
    25233: ["acRadiatorTemperature", "AC radiator temperature", 1, "C"],
    25247: ["inverterVoltageL1", "Inverter voltage L1", 0.1, "V"],
    25248: ["inverterVoltageL2", "Inverter voltage L2", 0.1, "V"],
    25250: ["inverterCurrentL1", "Inverter current L1", 0.1, "A"],
    25251: ["inverterCurrentL2", "Inverter current L2", 0.1, "A"],
    25257: ["loadVoltageL1", "Load voltage L1", 0.1, "V"],
    25258: ["loadVoltageL2", "Load voltage L2", 0.1, "V"],
    25260: ["loadCurrentL1", "Load current L1", 0.1, "A"],
    25261: ["loadCurrentL2", "Load current L2", 0.1, "A"],
    25273: ["batteryPower", "Battery power", 1, "W"],
    25274: ["batteryCurrent", "Battery current", 1, "A"],

    20109: ["EnergyUseMode", "Energy use mode", 1, "map", {
        0: "-", 1: "SBU", 2: "SUB", 3: "UTI", 4: "SOL"
    }],

    15201: ["ChargerWorkstate", "Charger Workstate", 1, "map", {
        0: "Initialization", 1: "Selftest",
        2: "Work", 3: "Stop"
    }],
    15202: ["MpptState", "Mppt State", 1, "map", {
        0: "Stop", 1: "MPPT", 2: "Current limiting"
    }],
    15205: ["PvVoltage", "Pv Voltage", 0.1, "V"],
    15206: ["chBatteryVoltage", "Ch Battery Voltage", 0.1, "V"],
    15207: ["chChargerCurrent", "Ch Charger Current", 0.1, "A"],
    15208: ["ChargerPower", "Charger Power", 1, "W"],
}


# ==============================
# READ STANDARD REGISTERS
# ==============================
def read_register_values(instrument, startreg, count):
    data = {}
    register_id = startreg

    try:
        results = instrument.read_registers(startreg, count)
    except Exception as e:
        logging.error(f"Error reading registers {startreg}: {e}")
        return data

    for r in results:
        if register_id in register_map:
            r_key = register_map[register_id][0]
            r_unit = register_map[register_id][2]

            if register_map[register_id][3] == "map":
                r_value = register_map[register_id][4].get(r, r)
            else:
                r_value = round(r * r_unit, 2)

            if register_id in [25213, 25273, 25274, 25214, 110]:
                if isinstance(r_value, (int, float)) and r_value > 32000:
                    r_value = -abs(r_value - 65536)

            data[r_key] = r_value

        register_id += 1

    return data


# ==============================
# READ INT32 REGISTERS
# ==============================
def read_int32(instrument, register, scale=1):
    try:
        value = instrument.read_long(register, functioncode=3, signed=True)
        return round(value / scale, 2)
    except Exception as e:
        logging.error(f"Error reading INT32 register {register}: {e}")
        return None


# ==============================
# SAVE JSON
# ==============================
def save_data(data):
    data["timestamp"] = datetime.utcnow().isoformat()

    if not os.path.exists(OUTPUT_FILE):
        with open(OUTPUT_FILE, "w") as f:
            json.dump([data], f, indent=4)
    else:
        try:
            with open(OUTPUT_FILE, "r") as f:
                existing_data = json.load(f)
        except json.JSONDecodeError:
            existing_data = []

        existing_data.append(data)

        with open(OUTPUT_FILE, "w") as f:
            json.dump(existing_data, f, indent=4)

    logging.info("Data saved successfully.")


# ==============================
# DERIVED METRICS
# ==============================
def calculate_derived_metrics(data):
    derived = {}

    battery_voltage = data.get("batteryVoltage")
    battery_current = data.get("batteryCurrent")
    load_power = data.get("loadPower", 0)
    grid_power = data.get("gridPower", 0)
    battery_power = data.get("batteryPower")
    charger_power = data.get("ChargerPower", 0)
    soc = data.get("BMS_Battery_SOC")

    # Old method for line currents (INT32)
    l1_current = data.get("currentL1")
    l2_current = data.get("currentL2")
    inverter_voltage = data.get("inverterVoltage")

    # NEW: Get individual line data from registers
    inverter_voltage_l1 = data.get("inverterVoltageL1")
    inverter_voltage_l2 = data.get("inverterVoltageL2")
    inverter_current_l1 = data.get("inverterCurrentL1")
    inverter_current_l2 = data.get("inverterCurrentL2")
    
    load_voltage_l1 = data.get("loadVoltageL1")
    load_voltage_l2 = data.get("loadVoltageL2")
    load_current_l1 = data.get("loadCurrentL1")
    load_current_l2 = data.get("loadCurrentL2")

    # Battery calculated power
    if battery_voltage is not None and battery_current is not None:
        calc_power = round(battery_voltage * battery_current, 2)
        derived["batteryCalculatedPower"] = calc_power

        if calc_power > 100:
            derived["batteryDirection"] = "discharging"
        elif calc_power < -100:
            derived["batteryDirection"] = "charging"
        else:
            derived["batteryDirection"] = "idle"

    # Estimated runtime
    if soc is not None and load_power > 0 and battery_voltage:
        battery_capacity_wh = battery_voltage * 100
        remaining_wh = battery_capacity_wh * (soc / 100)
        runtime_hours = round(remaining_wh / load_power, 2)
        derived["batteryEstimatedRuntimeHours"] = runtime_hours

    # Grid dependency
    if load_power > 0:
        derived["gridDependencyPercent"] = round((grid_power / load_power) * 100, 2)

    # Consumption source - gridPower is negative when grid is feeding the system
    if data.get("gridVoltage") > 0:
        # grid is supplying energy into inverter/battery/load
        derived["houseConsumptionSource"] = "grid"
    elif battery_power is not None and battery_power > 0:
        # battery is discharging (power leaving battery to house)
        derived["houseConsumptionSource"] = "battery"
    elif charger_power > 50:
        # solar charger producing significant power
        derived["houseConsumptionSource"] = "solar"
    else:
        derived["houseConsumptionSource"] = "mixed/low"

    # Inverter efficiency
    input_power = 0
    if grid_power:
        input_power += abs(grid_power)
    if charger_power:
        input_power += abs(charger_power)
    if battery_power:
        input_power += abs(battery_power)

    if input_power > 0:
        derived["estimatedInverterEfficiency"] = round(
            (load_power / input_power) * 100, 2
        )

    # ==========================================
    # NEW: Individual Line Power Calculations
    # ==========================================
    
    # Line 1 Inverter Power (Register-based)
    if inverter_voltage_l1 is not None and inverter_current_l1 is not None:
        derived["inverterPowerL1"] = round(inverter_voltage_l1 * inverter_current_l1, 2)

    # Line 2 Inverter Power (Register-based)
    if inverter_voltage_l2 is not None and inverter_current_l2 is not None:
        derived["inverterPowerL2"] = round(inverter_voltage_l2 * inverter_current_l2, 2)

    # Load Line 1 Power (Register-based)
    if load_voltage_l1 is not None and load_current_l1 is not None:
        derived["loadPowerL1"] = round(load_voltage_l1 * load_current_l1, 2)

    # Load Line 2 Power (Register-based)
    if load_voltage_l2 is not None and load_current_l2 is not None:
        derived["loadPowerL2"] = round(load_voltage_l2 * load_current_l2, 2)

    # Total Line Power (sum of both lines)
    if "inverterPowerL1" in derived and "inverterPowerL2" in derived:
        derived["inverterPowerTotal"] = round(
            derived["inverterPowerL1"] + derived["inverterPowerL2"], 2
        )

    if "loadPowerL1" in derived and "loadPowerL2" in derived:
        derived["loadPowerTotal"] = round(
            derived["loadPowerL1"] + derived["loadPowerL2"], 2
        )

    # Phase Imbalance (Inverter)
    if "inverterPowerL1" in derived and "inverterPowerL2" in derived:
        max_inv_power = max(
            abs(derived["inverterPowerL1"]), abs(derived["inverterPowerL2"])
        )
        if max_inv_power > 0:
            derived["inverterPhaseImbalancePercent"] = round(
                abs(
                    derived["inverterPowerL1"] - derived["inverterPowerL2"]
                ) / max_inv_power * 100,
                2,
            )

    # Phase Imbalance (Load)
    if "loadPowerL1" in derived and "loadPowerL2" in derived:
        max_load_power = max(abs(derived["loadPowerL1"]), abs(derived["loadPowerL2"]))
        if max_load_power > 0:
            derived["loadPhaseImbalancePercent"] = round(
                abs(derived["loadPowerL1"] - derived["loadPowerL2"])
                / max_load_power * 100,
                2,
            )

    # Legacy phase power calculations (from INT32 registers if available)
    if inverter_voltage and l1_current is not None:
        derived["powerL1"] = round(inverter_voltage * l1_current, 2)

    if inverter_voltage and l2_current is not None:
        derived["powerL2"] = round(inverter_voltage * l2_current, 2)

    if "powerL1" in derived and "powerL2" in derived:
        max_power = max(abs(derived["powerL1"]), abs(derived["powerL2"]))
        if max_power > 0:
            derived["phaseImbalancePercent"] = round(
                abs(derived["powerL1"] - derived["powerL2"]) / max_power * 100,
                2
            )

    return derived


# ==============================
# MAIN LOOP
# ==============================
def main():
    while True:
        try:
            instrument = minimalmodbus.Instrument(SERPORT, 4)
            instrument.serial.timeout = SERTIMEOUT
            instrument.serial.baudrate = SERBAUD

            all_data = {}

            all_data.update(read_register_values(instrument, 15201, 10))

            all_data.update(read_register_values(instrument, 25201, 20))
            all_data.update(read_register_values(instrument, 25221, 20))
            all_data.update(read_register_values(instrument, 25241, 20))
            all_data.update(read_register_values(instrument, 25261, 20))
            all_data.update(read_register_values(instrument, 25281, 20))

            all_data.update(read_register_values(instrument, 20109, 5))
            all_data.update(read_register_values(instrument, 109, 5))

            # Read phase currents (INT32)
            l1_current = read_int32(instrument, 10120, 10)
            l2_current = read_int32(instrument, 10122, 10)

            if l1_current is not None:
                all_data["currentL1"] = l1_current

            if l2_current is not None:
                all_data["currentL2"] = l2_current

            derived_data = calculate_derived_metrics(all_data)
            all_data.update(derived_data)

            save_data(all_data)

        except Exception as e:
            logging.error(f"General error: {e}")

        time.sleep(INTERVAL)


if __name__ == "__main__":
    main()
