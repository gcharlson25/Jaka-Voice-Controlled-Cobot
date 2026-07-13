import json

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


def execute_finetuned_command(cmd):
    """Send a positional-args command from llm_finetuned to the robot client."""
    try:
        func = cmd["function"]
        args = cmd.get("args", [])

        if func == "circular_move" and "args" not in cmd:
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
            value = -value  
        move[axis_map[parsed["axis"]]] = value
        print(f"Moving: {move}")
        _send_payload(move)
        print("Command sent!")
    except Exception as e:
        print(f"Error in execute_command: {e}")
