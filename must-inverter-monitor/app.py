import asyncio
import minimalmodbus
import logging
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
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

app = FastAPI()
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

latest_data = {}

os.makedirs("logs", exist_ok=True)
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s | %(levelname)s | %(message)s",
    handlers=[logging.StreamHandler()],
)


async def modbus_loop():
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

            # Currents
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

        await asyncio.sleep(INTERVAL)


@app.on_event("startup")
async def startup_event():
    asyncio.create_task(modbus_loop())


@app.get("/data")
def get_data():
    return latest_data
