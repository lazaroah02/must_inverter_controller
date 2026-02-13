import minimalmodbus
import time
import logging
from threading import Thread
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from logging.handlers import RotatingFileHandler
import os
from inverter_monitor import (
    read_register_values,
    SERTIMEOUT,
    SERBAUD,
    SERPORT,
    read_int32,
    calculate_derived_metrics,
    INTERVAL
)

# ==============================
# FASTAPI INIT
# ==============================
app = FastAPI()

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

latest_data = {}

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
# MAIN LOOP FOR READING INVERTER DATA
# ==============================
def modbus_loop():
    global latest_data

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

            latest_data = all_data

        except Exception as e:
            logging.error(f"General error: {e}")

        time.sleep(INTERVAL)


# ==============================
# START THREAD
# ==============================
@app.on_event("startup")
def startup_event():
    thread = Thread(target=modbus_loop, daemon=True)
    thread.start()


# ==============================
# API ENDPOINT
# ==============================
@app.get("/data")
def get_data():
    return latest_data
