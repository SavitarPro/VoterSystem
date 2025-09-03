import subprocess
import time
import sys
import os


def run_service(service_name, port):
    """Run a service in a separate process"""
    try:
        print(f"Starting {service_name} service on port {port}...")
        cmd = [sys.executable, f"{service_name}_service/app.py", str(port)]
        return subprocess.Popen(cmd)
    except Exception as e:
        print(f"Error starting {service_name} service: {e}")
        return None


def main():
    processes = []

    try:
        # Start all services
        processes.append(run_service("registration", 5001))
        processes.append(run_service("validity", 5002))
        processes.append(run_service("auth", 5003))
        processes.append(run_service("vote", 5004))
        processes.append(run_service("admin", 5005))
        processes.append(run_service("fraud", 5006))

        print("All services started. Press Ctrl+C to stop.")

        # Keep the script running
        while True:
            time.sleep(1)

    except KeyboardInterrupt:
        print("\nStopping all services...")
        for process in processes:
            if process:
                process.terminate()
        print("All services stopped.")


if __name__ == "__main__":
    main()