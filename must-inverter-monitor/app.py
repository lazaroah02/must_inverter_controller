import asyncio
import minimalmodbus
import logging
from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import HTMLResponse
from fastapi.templating import Jinja2Templates
import os
from inverter_monitor import (
    read_register_values,
    SERTIMEOUT,
    SERBAUD,
    SERPORT,
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

templates = Jinja2Templates(directory="front")


async def modbus_loop():
    global latest_data

    instrument = None
    was_connected = False

    while True:

        # =========================
        # CONNECT IF NEEDED
        # =========================
        if instrument is None:
            try:
                if not was_connected:
                    logging.info("Trying to connect to inverter...")

                instrument = minimalmodbus.Instrument(SERPORT, 4)
                instrument.serial.timeout = SERTIMEOUT
                instrument.serial.baudrate = SERBAUD

                # 🔥 IMPORTANT FOR WINDOWS
                instrument.close_port_after_each_call = True

                logging.info("Connected to inverter.")
                was_connected = True

            except Exception as e:
                if was_connected:
                    logging.warning("Connection lost. Retrying...")
                else:
                    logging.warning(f"Connection failed: {e}")

                instrument = None
                was_connected = False
                await asyncio.sleep(5)
                continue

        # =========================
        # READ DATA
        # =========================
        try:
            all_data = {}

            all_data.update(read_register_values(instrument, 15201, 10))
            all_data.update(read_register_values(instrument, 25201, 20))
            all_data.update(read_register_values(instrument, 25221, 20))
            all_data.update(read_register_values(instrument, 25241, 20))
            all_data.update(read_register_values(instrument, 25261, 20))
            all_data.update(read_register_values(instrument, 25281, 20))
            all_data.update(read_register_values(instrument, 20109, 5))
            all_data.update(read_register_values(instrument, 109, 5))

            # individual phase currents are not monitored any more

            derived_data = calculate_derived_metrics(all_data)
            all_data.update(derived_data)

            latest_data = all_data

        except Exception as e:
            logging.error(f"Read error: {e}")
            logging.warning("Device disconnected. Releasing COM port...")

            try:
                if instrument and instrument.serial:
                    instrument.serial.close()
            except Exception as close_error:
                logging.warning(f"Error closing port: {close_error}")

            instrument = None
            was_connected = False

            # ⏳ Give Windows time to fully release COM
            await asyncio.sleep(3)
            continue

        await asyncio.sleep(INTERVAL)


@app.on_event("startup")
async def startup_event():
    asyncio.create_task(modbus_loop())


@app.get("/data")
def get_data():
    return latest_data


@app.get("/", response_class=HTMLResponse)
async def read_dashboard(request: Request):
    return templates.TemplateResponse("index.html", {"request": request})

