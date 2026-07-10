import json
import os

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
    {
        "type": "function",
        "function": {
            "name": "screw_operation",
            "description": (
                "Fasten or unfasten screws on the workpiece. "
                "Use when the user says fasten, tighten, screw in, unfasten, loosen, remove, or unscrew. "
                "screw_number is 1-5 for a specific screw, or 0 for all screws."
            ),
            "parameters": {
                "type": "object",
                "properties": {
                    "action":       {"type": "string", "enum": ["fasten", "unfasten"], "description": "fasten or unfasten"},
                    "screw_number": {"type": "integer", "description": "Screw number 1-5, or 0 for all screws"},
                },
                "required": ["action", "screw_number"],
            },
        },
    },
]

# TCP connection to full_robot_client.py (replaces the old command.json file IPC)
HOST = "127.0.0.1"
PORT = 9100

_sock = None


def _send_msg(sock, msg):
    import struct
    data = json.dumps(msg).encode("utf-8")
    sock.sendall(struct.pack("!I", len(data)) + data)


def _recv_msg(sock):
    import struct
    raw = _recv_exact(sock, 4)
    if raw is None:
        return None
    length = struct.unpack("!I", raw)[0]
    data = _recv_exact(sock, length)
    if data is None:
        return None
    return json.loads(data.decode("utf-8"))


def _recv_exact(sock, n):
    buf = b""
    while len(buf) < n:
        chunk = sock.recv(n - len(buf))
        if not chunk:
            return None
        buf += chunk
    return buf


def connect_robot():
    """Connect to full_robot_client.py and trigger robot setup. Call once at startup."""
    global _sock
    import socket
    print(f"Connecting to robot client at {HOST}:{PORT}...")
    _sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    _sock.connect((HOST, PORT))
    _send_msg(_sock, {"command": "setup"})
    reply = _recv_msg(_sock)
    print(f"Robot client connected: {reply}")


def _send_payload(payload):
    """Send a command payload to the robot client and wait for the reply."""
    _send_msg(_sock, {"command": "execute", "payload": payload})
    return _recv_msg(_sock)


def execute_screw_command(action, screw_number):
    """Fasten/unfasten a screw (1-5) or all screws (0) via full_screw_control.py."""
    cmd = {"function": "screw_operation", "action": action, "screw_number": screw_number}
    print(f"Screw operation: {cmd}")
    _send_payload(cmd)
    print("Command sent!")


def execute_llm_command(tool_result):
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
            _send_payload(move)
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
            _send_payload(cmd)
            print("Command sent!")

        elif func == "motion_abort":
            _send_payload({"function": "motion_abort"})
            print("Abort sent!")

        elif func == "screw_operation":
            cmd = {
                "function":     "screw_operation",
                "action":       args.get("action", "fasten"),
                "screw_number": int(float(args.get("screw_number", 0))),
            }
            print(f"Screw operation: {cmd}")
            _send_payload(cmd)
            print("Command sent!")

        else:
            print(f"Unknown function: {func}")

    except Exception as e:
        print(f"Error in execute_llm_command: {e}")

def execute_finetuned_command(cmd):
    """Send a positional-args command from llm_finetuned to the robot client."""
    try:
        func = cmd["function"]
        args = cmd.get("args", [])

        if func == "circular_move" and "args" not in cmd:
            # radius-based command for the proven circular_move handler
            print(f"Sending: {cmd}")
            _send_payload(cmd)
            print("Command sent!")
            return

        PASS_THROUGH = {"linear_move", "joint_move", "set_digital_output",
                        "motion_abort", "execute_script"}
        if func in PASS_THROUGH:
            payload = cmd if func == "execute_script" else {"function": func, "args": args}
            print(f"Sending: {payload}")
            _send_payload(payload)
            print("Command sent!")
        else:
            print(f"Unknown function: {func}")
    except Exception as e:
        print(f"Error in execute_finetuned_command: {e}")

def execute_command(parsed):
    try:
        axis_map = {"x": 0, "y": 1, "z": 2}
        move = [0, 0, 0, 0, 0, 0]
        value = parsed["distance"] * parsed["direction"]
        if parsed["axis"] == "x":
            value = -value  # robot's physical X axis is opposite to named direction
        move[axis_map[parsed["axis"]]] = value
        print(f"Moving: {move}")
        _send_payload(move)
        print("Command sent!")
    except Exception as e:
        print(f"Error in execute_command: {e}")
