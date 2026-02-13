import subprocess
import socket
import os
import time
import venv
import sys

# ---------------------------
# Get Wi-Fi IP
# ---------------------------
def get_wifi_ip():
    s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    try:
        s.connect(("8.8.8.8", 80))
        ip = s.getsockname()[0]
    except Exception:
        ip = "127.0.0.1"
    finally:
        s.close()
    return ip

# ---------------------------
# Ensure virtual environment exists
# ---------------------------
def ensure_venv(root_dir):
    venv_dir = os.path.join(root_dir, "venv")
    python_exec = os.path.join(venv_dir, "Scripts", "python.exe") if os.name == "nt" else os.path.join(venv_dir, "bin", "python")

    # Create venv if it does not exist
    if not os.path.exists(venv_dir):
        print("Creating virtual environment...")
        venv.create(venv_dir, with_pip=True)
        print("Virtual environment created.")

    # Always install/update dependencies
    req_file = os.path.join(root_dir, "requirements.txt")
    if os.path.exists(req_file):
        print("Installing/updating dependencies from requirements.txt...")
        subprocess.check_call([python_exec, "-m", "pip", "install", "--upgrade", "-r", req_file])
        print("Dependencies installed/updated.")
    else:
        print("No requirements.txt found, skipping dependencies installation.")

    return venv_dir, python_exec

# ---------------------------
# Build environment for subprocess
# ---------------------------
def build_venv_env(venv_dir):
    env = os.environ.copy()
    if os.name == "nt":
        # Windows
        env["VIRTUAL_ENV"] = venv_dir
        env["PATH"] = os.path.join(venv_dir, "Scripts") + os.pathsep + env["PATH"]
    else:
        # Linux/Mac
        env["VIRTUAL_ENV"] = venv_dir
        env["PATH"] = os.path.join(venv_dir, "bin") + os.pathsep + env["PATH"]
    return env

def main():
    wifi_ip = get_wifi_ip()
    print(f"Detected IP: {wifi_ip}")

    # ---------------------------
    # Define project directories
    # ---------------------------
    ROOT_DIR = os.path.dirname(os.path.abspath(__file__))
    FRONT_DIR = os.path.join(ROOT_DIR, "front")
    FASTAPI_DIR = os.path.join(ROOT_DIR, "must-inverter-monitor")

    # ---------------------------
    # Setup virtual environment
    # ---------------------------
    venv_dir, python_exec = ensure_venv(ROOT_DIR)
    env = build_venv_env(venv_dir)

    # ---------------------------
    # FastAPI command
    # ---------------------------
    uvicorn_cmd = [
        python_exec, "-m", "uvicorn",
        "app:app",
        "--reload",
        "--host", wifi_ip,
        "--port", "8001"
    ]
    uvicorn_process = subprocess.Popen(uvicorn_cmd, cwd=FASTAPI_DIR, env=env)

    # ---------------------------
    # HTTP server command
    # ---------------------------
    http_cmd = [python_exec, "-m", "http.server", "8080", "--bind", wifi_ip]
    http_process = subprocess.Popen(http_cmd, cwd=FRONT_DIR, env=env)

    print(f"FastAPI running at http://{wifi_ip}:8001")
    print(f"HTML server running at http://{wifi_ip}:8080")

    # ---------------------------
    # Keep script alive until Ctrl+C
    # ---------------------------
    try:
        while True:
            time.sleep(1)
    except KeyboardInterrupt:
        print("\nStopping servers...")
        uvicorn_process.terminate()
        http_process.terminate()
        uvicorn_process.wait()
        http_process.wait()
        print("Servers stopped")


if __name__ == "__main__":
    main()
