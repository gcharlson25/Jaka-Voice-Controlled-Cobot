import json
import os
import re
import time

TOOLS = [
    {
        "type": "function",
        "function": {
            "name": "linear_move",
            "description": (
                "Move the robot arm in a straight line. "
                "Positive x_mm = right, negative = left. "
                "Positive y_mm = forward, negative = backward. "
                "Positive z_mm = up, negative = down. "
                "Set unused axes to 0. Default 10mm if no distance given. Default 100 mm/s."
            ),
            "parameters": {
                "type": "object",
                "properties": {
                    "x_mm":      {"type": "number", "description": "X offset in mm"},
                    "y_mm":      {"type": "number", "description": "Y offset in mm"},
                    "z_mm":      {"type": "number", "description": "Z offset in mm"},
                    "speed_mms": {"type": "number", "description": "Speed in mm/s, default 100"},
                },
                "required": ["x_mm", "y_mm", "z_mm"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "circular_move",
            "description": (
                "Move the robot end effector in a circle. "
                "'xy' = horizontal circle. 'xz' = vertical circle in X-Z plane. 'yz' = vertical circle in Y-Z plane. "
                "circles = number of full loops, default 1."
            ),
            "parameters": {
                "type": "object",
                "properties": {
                    "radius_mm": {"type": "number",  "description": "Radius in mm"},
                    "plane":     {"type": "string",  "enum": ["xy", "xz", "yz"]},
                    "circles":   {"type": "integer", "description": "Number of full circles, default 1"},
                    "speed_mms": {"type": "number",  "description": "Speed in mm/s, default 50"},
                },
                "required": ["radius_mm", "plane"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "motion_abort",
            "description": "Immediately stop all robot motion. Use for stop, halt, abort, emergency stop.",
            "parameters": {"type": "object", "properties": {}, "required": []},
        },
    },
]

COMMAND_FILE = "C:/Projects/jaka_voice/command.json"

def execute_ollama_command(tool_result):
    try:
        func = tool_result["function"]
        args = tool_result.get("args", {})

        if func == "linear_move":
            x = -(float(args.get("x_mm", 0)))  # robot's physical X axis is inverted
            y = float(args.get("y_mm", 0))
            z = float(args.get("z_mm", 0))
            speed = float(args.get("speed_mms", 100))
            if x == 0.0 and y == 0.0 and z == 0.0:
                return
            move = [x, y, z, 0, 0, 0]
            print(f"Moving: {move}")
            with open(COMMAND_FILE, "w") as f:
                json.dump(move, f)
            print("Command sent!")

        elif func == "circular_move":
            cmd = {
                "function": "circular_move",
                "radius_mm": float(args.get("radius_mm", 50)),
                "plane":     args.get("plane", "xy"),
                "circles":   int(float(args.get("circles", 1))),
                "speed":     float(args.get("speed_mms", 50)),
            }
            print(f"Moving: {cmd}")
            with open(COMMAND_FILE, "w") as f:
                json.dump(cmd, f)
            print("Command sent!")

        elif func == "motion_abort":
            cmd = {"function": "motion_abort"}
            with open(COMMAND_FILE, "w") as f:
                json.dump(cmd, f)
            print("Abort sent!")

        else:
            print(f"Unknown function: {func}")

    except Exception as e:
        print(f"Error in execute_ollama_command: {e}")

def execute_command(parsed):
    try:
        axis_map = {"x": 0, "y": 1, "z": 2}
        move = [0, 0, 0, 0, 0, 0]
        value = parsed["distance"] * parsed["direction"]
        if parsed["axis"] == "x":
            value = -value  # robot's physical X axis is opposite to named direction
        move[axis_map[parsed["axis"]]] = value
        print(f"Moving: {move}")
        with open(COMMAND_FILE, "w") as f:
            json.dump(move, f)
        print("Command sent!")
    except Exception as e:
        print(f"Error in execute_command: {e}")
