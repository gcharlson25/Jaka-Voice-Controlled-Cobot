import __common
__common.init_env()
import jkrc

import time
import math
import json
import os
import sys
import ctypes

ABS_MOVEMENT = 0
INCREMENT_MOVEMENT = 1
COMMAND_FILE = "command.json"
QUIT_FILE = "quit.signal"
LOCK_FILE = "robot_control.lock"

def cobotSetup():
    print("\n\n\n")
    cobot = jkrc.RC("192.168.10.200")
    print("logging in")
    cobot.login()
    print("powering on")
    cobot.power_on()
    print("enabling")
    cobot.enable_robot()
    print("setting payload and centroid")
    cobot.set_payload(mass = 0.5, centroid = [0, 0, 20])
    return cobot

def execute_move(cobot, move):
    print(f"Executing move: {move}")
    cobot.linear_move(move, INCREMENT_MOVEMENT, False, 100)
    print("Move complete")

def main():
    if os.path.exists(LOCK_FILE):
        try:
            with open(LOCK_FILE, "r") as f:
                pid = int(f.read().strip())
            handle = ctypes.windll.kernel32.OpenProcess(0x1000, False, pid)
            if handle:
                ctypes.windll.kernel32.CloseHandle(handle)
                print("Another robot_control instance is already running. Exiting.")
                sys.exit(1)
            else:
                print("Stale lock file found, removing.")
        except Exception:
            pass
    with open(LOCK_FILE, "w") as f:
        f.write(str(os.getpid()))
    if os.path.exists(QUIT_FILE):
        os.remove(QUIT_FILE)
    try:
        cobot = cobotSetup()
        print("Robot ready, waiting for voice commands...")

        if os.path.exists(COMMAND_FILE):
            try:
                time.sleep(0.05)
                with open(COMMAND_FILE, "r") as f:
                    move = json.load(f)
                os.remove(COMMAND_FILE)
                execute_move(cobot, move)
            except Exception as e:
                print(f"Error: {e}")

        while True:
            if os.path.exists(QUIT_FILE):
                os.remove(QUIT_FILE)
                print("Quit signal received. Shutting down.")
                break
            if os.path.exists(COMMAND_FILE):
                try:
                    with open(COMMAND_FILE, "r") as f:
                        move = json.load(f)
                    os.remove(COMMAND_FILE)
                    execute_move(cobot, move)
                except Exception as e:
                    print(f"Error: {e}")
            time.sleep(0.05)
    finally:
        if os.path.exists(LOCK_FILE):
            os.remove(LOCK_FILE)

if __name__ == '__main__':
    main()
