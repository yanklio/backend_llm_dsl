#!/usr/bin/env python3
"""Utility script to kill processes using port 3000."""

import subprocess
import sys


def kill_port_3000():
    """Kill any process using port 3000."""
    port = 3000

    try:
        # Try lsof first (works on Linux/Mac)
        result = subprocess.run(["lsof", "-ti", f":{port}"], capture_output=True, text=True)

        if result.returncode == 0 and result.stdout.strip():
            pids = result.stdout.strip().split("\n")
            for pid in pids:
                if pid:
                    print(f"Killing process {pid} on port {port}")
                    subprocess.run(["kill", "-9", pid])
            print(f"Successfully freed port {port}")
            return True
        else:
            print(f"No process found on port {port}")
            return True

    except FileNotFoundError:
        # lsof not available, try fuser (Linux)
        try:
            result = subprocess.run(["fuser", "-k", f"{port}/tcp"], capture_output=True, text=True)
            if result.returncode == 0:
                print(f"Successfully freed port {port}")
                return True
            else:
                print(f"No process found on port {port}")
                return True
        except FileNotFoundError:
            print("Error: Neither 'lsof' nor 'fuser' command available", file=sys.stderr)
            print("Please install lsof or fuser to use this utility", file=sys.stderr)
            return False

    except Exception as e:
        print(f"Error killing process on port {port}: {e}", file=sys.stderr)
        return False


if __name__ == "__main__":
    success = kill_port_3000()
    sys.exit(0 if success else 1)
