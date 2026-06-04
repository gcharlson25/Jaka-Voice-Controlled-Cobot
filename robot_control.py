import __common
__common.init_env()
import jkrc

import time
import math
import json
import os

ABS_MOVEMENT = 0
INCREMENT_MOVEMENT = 1
COMMAND_FILE = "command.json"

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
    cobot = cobotSetup()
    print("Robot ready, waiting for voice commands...")
    
    # clear any old commands on startup
    if os.path.exists(COMMAND_FILE):
        try:
            time.sleep(0.05)  # small delay to let voice script finish writing
            with open(COMMAND_FILE, "r") as f:
                move = json.load(f)
            os.remove(COMMAND_FILE)
            execute_move(cobot, move)
        except Exception as e:
            print(f"Error: {e}")

    while True:
        if os.path.exists(COMMAND_FILE):
            try:
                with open(COMMAND_FILE, "r") as f:
                    move = json.load(f)
                os.remove(COMMAND_FILE)  # delete after reading
                execute_move(cobot, move)
            except Exception as e:
                print(f"Error: {e}")
        time.sleep(0.05)  # check every 50ms

if __name__ == '__main__':
    main()