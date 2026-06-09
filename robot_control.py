import __common
__common.init_env()
import jkrc

import time
import math
import json
import os
import sys
import ctypes

from screws import (
    fastenScrew1, fastenScrew2, fastenScrew3, fastenScrew4, fastenScrew5,
    unfastenScrew1, unfastenScrew2, unfastenScrew3, unfastenScrew4, unfastenScrew5,
    fastenAll, unfastenAll,
)

ABS_MOVEMENT = 0
INCREMENT_MOVEMENT = 1
COMMAND_FILE = "command.json"
QUIT_FILE = "quit.signal"
LOCK_FILE = "robot_control.lock"

TCP = [0, 0, 0, 0, 0, 0]
USR = [0, 0, 0, 0, 0, 0]

def coordinateSetup(cobot):
    print("setting coordinates")
    cobot.set_tool_data(5, TCP, "tool_screw_test")
    cobot.set_tool_id(5)
    cobot.set_user_frame_data(6, USR, "user_screw_test")
    cobot.set_user_frame_id(6)

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
    coordinateSetup(cobot)
    return cobot

def execute_move(cobot, command):
    try:
        # plain list from keyword parser
        if isinstance(command, list):
            print(f"Executing move: {command}")
            cobot.linear_move(command, INCREMENT_MOVEMENT, False, 500)
            print("Move complete")
            return

        func = command.get("function", "linear_move")

        if func == "linear_move":
            end_pos = command["end_pos"]
            speed = command.get("speed", 500)
            print(f"Executing linear_move: {end_pos} at {speed}mm/s")
            cobot.linear_move(end_pos, INCREMENT_MOVEMENT, False, speed)
            print("Move complete")

        elif func == "circular_move":
            ret = cobot.get_tcp_position()
            if ret[0] != 0:
                print(f"Error getting TCP position: {ret[0]}")
                return
            pos = list(ret[1])
            R           = command["radius_mm"]
            if R < 20:
                print(f"Radius {R}mm too small, skipping.")
                return
            plane       = command.get("plane", "xy") or "xy"
            num_circles = int(command.get("circles", 1))
            speed       = command.get("speed", 50)

            mid_pos = pos[:]
            end_pos = pos[:]
            if plane == "xy":
                mid_pos[0] = pos[0]+R; mid_pos[1] = pos[1]+R
                end_pos[1] = pos[1]+2*R
            elif plane == "xz":
                mid_pos[0] = pos[0]+R; mid_pos[2] = pos[2]+R
                end_pos[2] = pos[2]+2*R
            elif plane == "yz":
                mid_pos[1] = pos[1]+R; mid_pos[2] = pos[2]+R
                end_pos[2] = pos[2]+2*R

            mid_rev = pos[:]
            end_rev = pos[:]
            if plane == "xy":
                mid_rev[0] = pos[0]-R; mid_rev[1] = pos[1]+R
            elif plane == "xz":
                mid_rev[0] = pos[0]-R; mid_rev[2] = pos[2]+R
            elif plane == "yz":
                mid_rev[1] = pos[1]-R; mid_rev[2] = pos[2]+R

            print(f"Executing circular_move: R={R}mm plane={plane} x{num_circles}")
            for _ in range(num_circles):
                for arc_end, arc_mid in [(end_pos, mid_pos), (end_rev, mid_rev)]:
                    cobot.circular_move(arc_end, arc_mid, ABS_MOVEMENT, True, speed, 200, 0.1)
            print("Move complete")

        elif func == "motion_abort":
            print("Aborting motion!")
            cobot.motion_abort()
            print("Motion aborted")

        elif func == "screw_operation":
            action = command.get("action", "fasten")
            screw_number = int(command.get("screw_number", 0))
            screw_funcs = {
                "fasten":   [fastenScrew1, fastenScrew2, fastenScrew3, fastenScrew4, fastenScrew5],
                "unfasten": [unfastenScrew1, unfastenScrew2, unfastenScrew3, unfastenScrew4, unfastenScrew5],
            }
            if screw_number == 0:
                fastenAll(cobot) if action == "fasten" else unfastenAll(cobot)
            elif 1 <= screw_number <= 5:
                screw_funcs[action][screw_number - 1](cobot)
            else:
                print(f"Invalid screw number: {screw_number}")

        else:
            print(f"Unknown function: {func}")

    except Exception as e:
        print(f"Error in execute_move: {e}")

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
