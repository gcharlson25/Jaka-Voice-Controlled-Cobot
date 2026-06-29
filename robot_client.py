"""
Robot client -- listens for commands from vision_server.py and drives the JAKA robot.
Requires Python 3.7 (jkrc SDK).

Usage:  python robot_client.py
"""

import __common
__common.init_env()
import jkrc

import json
import socket
import struct

HOST = "127.0.0.1"
PORT = 9100

ABS = 0
INCR = 1

TCP = [0, 0, 0, 0, 0, 0]
USR = [0, 0, 0, 0, 0, 0]

cobot = None


def send_msg(sock, msg):
    data = json.dumps(msg).encode("utf-8")
    sock.sendall(struct.pack("!I", len(data)) + data)


def recv_msg(sock):
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


def setup_robot():
    global cobot
    cobot = jkrc.RC("192.168.10.200")
    cobot.login()
    cobot.power_on()
    cobot.enable_robot()
    cobot.set_payload(mass=0.5, centroid=[0, 0, 20])
    cobot.set_tool_data(5, TCP, "tool_teleop")
    cobot.set_tool_id(5)
    cobot.set_user_frame_data(6, USR, "user_teleop")
    cobot.set_user_frame_id(6)
    print("Robot ready.")
    return cobot


def handle_command(msg):
    cmd = msg.get("command")

    if cmd == "setup":
        setup_robot()
        return {"status": "ok"}

    elif cmd == "move":
        move = msg["move"]
        speed = msg.get("speed", 250)
        blocking = msg.get("blocking", False)
        cobot.linear_move(move, INCR, blocking, speed)
        return {"status": "ok"}

    elif cmd == "shutdown":
        print("Shutdown requested.")
        return {"status": "ok"}

    else:
        print("Unknown command: {}".format(cmd))
        return {"status": "error", "message": "unknown command"}


def main():
    server = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    server.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
    server.bind((HOST, PORT))
    server.listen(1)
    print("Robot client listening on {}:{}...".format(HOST, PORT))
    print("Start vision_server.py to connect.")

    conn, addr = server.accept()
    print("Vision server connected from {}".format(addr))

    try:
        while True:
            msg = recv_msg(conn)
            if msg is None:
                print("Connection closed.")
                break

            reply = handle_command(msg)
            send_msg(conn, reply)

            if msg.get("command") == "shutdown":
                break
    finally:
        conn.close()
        server.close()
        print("Robot client stopped.")


if __name__ == "__main__":
    main()
