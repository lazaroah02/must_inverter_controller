import minimalmodbus
import os
import json
from dotenv import load_dotenv
from inverter_monitor import register_map

# load env for serial
load_dotenv()
SERPORT = os.getenv("SERPORT")
SERTIMEOUT = float(os.getenv("SERTIMEOUT", 1))
SERBAUD = int(os.getenv("SERBAUD", 9600))


def create_instrument():
    instr = minimalmodbus.Instrument(SERPORT, 4)
    instr.serial.timeout = SERTIMEOUT
    instr.serial.baudrate = SERBAUD
    return instr


def read_register(instr, reg):
    """Read a single 16-bit register and return raw value."""
    try:
        val = instr.read_register(reg, 0)
        return val
    except Exception as e:
        print(f"error reading {reg}: {e}")
        return None


def scaled_value(reg, raw):
    if reg in register_map:
        key, _, unit, _, *rest = register_map[reg]
        scale = unit
        if isinstance(scale, (int, float)):
            return round(raw * scale, 2)
        else:
            return raw
    return raw


def lookup(reg):
    """Return descriptive info for a register."""
    if reg in register_map:
        info = register_map[reg]
        return {"name": info[0], "description": info[1], "scale": info[2], "type": info[3]}
    else:
        return None


def read_and_print(reg):
    instr = create_instrument()
    raw = read_register(instr, reg)
    info = lookup(reg) or {}
    scaled = scaled_value(reg, raw) if raw is not None else None
    print(f"Reg {reg}: raw={raw} scaled={scaled} info={info}")
    return raw, scaled


def read_int32(instr, reg, scale=1):
    """Read a signed 32‑bit value (two registers) and return scaled result."""
    try:
        val = instr.read_long(reg, functioncode=3, signed=True)
        return round(val / scale, 2)
    except Exception as e:
        print(f"error reading INT32 {reg}: {e}")
        return None


def get_value(reg):
    """Helper to get interpreted value (like PVVoltage)."""
    instr = create_instrument()
    raw = read_register(instr, reg)
    if raw is None:
        return None
    return scaled_value(reg, raw)


def dump_range(start, count):
    instr = create_instrument()
    try:
        results = instr.read_registers(start, count)
    except Exception as e:
        print(f"error reading block: {e}")
        return {}
    output = {}
    for i, raw in enumerate(results):
        r = start + i
        scaled = scaled_value(r, raw)
        output[r] = {"raw": raw, "scaled": scaled, "info": lookup(r)}
    print(json.dumps(output, indent=2))
    return output


def dump_all(block_size=100):
    """Scan the full 0‑65535 address space in chunks and print any non‑zero result.
    May take a while over RTU but lets you see every register the inverter responds to.
    """
    instr = create_instrument()
    result = {}
    for base in range(0, 0x10000, block_size):
        try:
            regs = instr.read_registers(base, block_size)
        except Exception:
            continue
        for i, raw in enumerate(regs):
            if raw is None:
                continue
            r = base + i
            if raw == 0:
                continue
            scaled = scaled_value(r, raw)
            result[r] = {"raw": raw, "scaled": scaled, "info": lookup(r)}
    print(json.dumps(result, indent=2))
    return result


if __name__ == "__main__":
    import argparse
    parser = argparse.ArgumentParser(description="Manual inverter register tester")
    parser.add_argument("--read", type=int, help="read single register")
    parser.add_argument("--read32", type=int, help="read signed 32-bit register")
    parser.add_argument("--get", type=int, help="get scaled value for register")
    parser.add_argument("--range", nargs=2, type=int, metavar=("START","COUNT"), help="dump block of registers")
    parser.add_argument("--range32", nargs=2, type=int, metavar=("START","COUNT"), help="dump blocks of signed 32-bit registers")
    parser.add_argument("--dump-all", action="store_true", help="scan the whole register space and show non-zero replies")
    args = parser.parse_args()
    if args.read is not None:
        read_and_print(args.read)
    elif args.read32 is not None:
        instr = create_instrument()
        val = read_int32(instr, args.read32)
        print(f"INT32 {args.read32} => {val}")
    elif args.get is not None:
        val = get_value(args.get)
        print(val)
    elif args.range:
        start, count = args.range
        dump_range(start, count)
    elif args.range32:
        instr = create_instrument()
        start, count = args.range32
        for i in range(start, start + count*2, 2):
            val = read_int32(instr, i)
            print(f"{i}: {val}")
    elif args.dump_all:
        dump_all()
    else:
        parser.print_help()
