"""
Vision server — runs camera, YOLO detection, and OpenCV UI.
Sends robot commands over a TCP socket to robot_client.py.
Requires Python 3.12+ (ultralytics).

Usage:  py -3.12 vision_server.py
"""

import pyrealsense2 as rs
import numpy as np
import cv2
import os
import sys
import time
import json
import socket
import struct
from ultralytics import YOLO

HOST = "127.0.0.1"
PORT = 9100

SPEED = 250
STEP = 1

ALIGN_SPEED = 100
ALIGN_TOLERANCE = 1

ALIGN_STEP_BANDS = [
    (100, 5.0),
    (50, 2.0),
    (20, 1.0),
    (10, 0.5),
    (0, 0.1),
]

PIXEL_X_TO_ROBOT_DIR = 1
PIXEL_Y_TO_ROBOT_DIR = 1

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
SAVE_DIR = os.path.join(BASE_DIR, "mounted_screw")
CALIBRATION_FILE = os.path.join(SAVE_DIR, "calibration.json")
MODEL_PATH = os.path.join(BASE_DIR, "runs", "detect", "head_detect", "weights", "best.pt")

model = YOLO(MODEL_PATH)

CONTROLS = {
    ord('w'): [0, -STEP, 0, 0, 0, 0],
    ord('s'): [0, STEP, 0, 0, 0, 0],
    ord('d'): [-STEP, 0, 0, 0, 0, 0],
    ord('a'): [STEP, 0, 0, 0, 0, 0],
    ord('e'): [0, 0, STEP, 0, 0, 0],
    ord('q'): [0, 0, -STEP, 0, 0, 0],
}


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


def detect_screw(image):
    results = model(image, verbose=False, conf=0.3)
    boxes = results[0].boxes
    if len(boxes) == 0:
        return None
    cx, cy = image.shape[1] // 2, image.shape[0] // 2
    best = None
    best_dist = float("inf")
    for box in boxes:
        x1, y1, x2, y2 = box.xyxy[0].tolist()
        bx, by = int((x1 + x2) / 2), int((y1 + y2) / 2)
        dist = (bx - cx) ** 2 + (by - cy) ** 2
        if dist < best_dist:
            best_dist = dist
            best = (bx, by, int(x2 - x1), int(y2 - y1))
    return best


def load_calibration():
    if os.path.exists(CALIBRATION_FILE):
        with open(CALIBRATION_FILE, "r") as f:
            data = json.load(f)
            return data["target_x"], data["target_y"]
    return None


def save_calibration(x, y):
    os.makedirs(SAVE_DIR, exist_ok=True)
    with open(CALIBRATION_FILE, "w") as f:
        json.dump({"target_x": x, "target_y": y}, f)
    print(f"Calibration saved: target pixel = ({x}, {y})")


def setup_camera():
    pipeline = rs.pipeline()
    config = rs.config()
    config.enable_stream(rs.stream.color, 640, 480, rs.format.bgr8, 30)
    pipeline.start(config)
    return pipeline


def get_step_size(err_px):
    err_px = abs(err_px)
    for threshold, step_mm in ALIGN_STEP_BANDS:
        if err_px > threshold:
            return step_mm
    return ALIGN_STEP_BANDS[-1][1]


def send_robot_command(sock, command):
    send_msg(sock, command)
    reply = recv_msg(sock)
    return reply


def auto_align(sock, pipeline, target):
    target_x, target_y = target
    print(f"Auto-aligning to target pixel ({target_x}, {target_y})...")
    print("Press ESC to cancel")

    while True:
        frames = pipeline.wait_for_frames()
        color_frame = frames.get_color_frame()
        if not color_frame:
            continue

        image = np.asanyarray(color_frame.get_data())
        screw = detect_screw(image)

        display = image.copy()
        cv2.drawMarker(display, (target_x, target_y), (0, 0, 255), cv2.MARKER_CROSS, 30, 2)

        if screw is None:
            cv2.putText(display, "NO SCREW DETECTED",
                        (10, 30), cv2.FONT_HERSHEY_SIMPLEX, 0.6, (0, 0, 255), 2)
            cv2.imshow("Teleop", display)
            if cv2.waitKey(100) & 0xFF == 27:
                print("Auto-align cancelled")
                return False
            continue

        sx, sy, sw, sh = screw
        cv2.rectangle(display, (sx - sw // 2, sy - sh // 2), (sx + sw // 2, sy + sh // 2), (0, 255, 0), 2)
        cv2.circle(display, (sx, sy), 3, (0, 255, 0), -1)
        cv2.line(display, (sx, sy), (target_x, target_y), (255, 0, 0), 2)

        err_x = sx - target_x
        err_y = sy - target_y

        cv2.putText(display, f"Error: ({err_x}, {err_y}) px",
                    (10, 30), cv2.FONT_HERSHEY_SIMPLEX, 0.6, (0, 255, 255), 2)
        cv2.imshow("Teleop", display)

        if abs(err_x) <= ALIGN_TOLERANCE and abs(err_y) <= ALIGN_TOLERANCE:
            print(f"Aligned! Final error: ({err_x}, {err_y}) px")
            cv2.waitKey(500)
            return True

        move = [0, 0, 0, 0, 0, 0]
        if abs(err_x) > ALIGN_TOLERANCE:
            move[1] = get_step_size(err_x) * PIXEL_X_TO_ROBOT_DIR * (1 if err_x > 0 else -1)
        if abs(err_y) > ALIGN_TOLERANCE:
            move[0] = get_step_size(err_y) * PIXEL_Y_TO_ROBOT_DIR * (1 if err_y > 0 else -1)

        send_robot_command(sock, {"command": "move", "move": move, "speed": ALIGN_SPEED, "blocking": True})

        if cv2.waitKey(1) & 0xFF == 27:
            print("Auto-align cancelled")
            return False


def main():
    print(f"Connecting to robot client at {HOST}:{PORT}...")
    sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    try:
        sock.connect((HOST, PORT))
    except ConnectionRefusedError:
        print("ERROR: Could not connect. Start robot_client.py first.")
        sys.exit(1)
    print("Connected to robot client.")

    send_robot_command(sock, {"command": "setup"})

    pipeline = setup_camera()
    cv2.namedWindow("Teleop", cv2.WINDOW_NORMAL)
    cv2.resizeWindow("Teleop", 1280, 960)

    rapid_capture = False
    last_capture_time = 0
    capture_count = 0
    target = load_calibration()

    print("Teleop ready!")
    print("  W = backward, S = forward")
    print("  A = left,     D = right")
    print("  Q = down,     E = up")
    print("  P = take photo")
    print("  R = toggle rapid capture (every 0.5s)")
    print("  C = calibrate (align tool over screw, then press C)")
    print("  T = auto-align to calibrated target")
    print("  ESC = quit")
    if target:
        print(f"  Loaded calibration: target pixel = ({target[0]}, {target[1]})")
    else:
        print("  No calibration found. Align over a screw and press C first.")

    try:
        while True:
            frames = pipeline.wait_for_frames()
            color_frame = frames.get_color_frame()
            if not color_frame:
                continue

            image = np.asanyarray(color_frame.get_data())
            display = image.copy()

            screw = detect_screw(image)
            if screw:
                sx, sy, sw, sh = screw
                cv2.rectangle(display, (sx - sw // 2, sy - sh // 2), (sx + sw // 2, sy + sh // 2), (0, 255, 0), 2)
                cv2.circle(display, (sx, sy), 3, (0, 255, 0), -1)

            if target:
                cv2.drawMarker(display, (target[0], target[1]), (0, 0, 255), cv2.MARKER_CROSS, 30, 2)

            status = "RAPID CAPTURE ON" if rapid_capture else "R: rapid  C: calib  T: align"
            cv2.putText(display, f"WASD/QE: move  P: photo  {status}  ESC: quit",
                        (10, 30), cv2.FONT_HERSHEY_SIMPLEX, 0.45, (0, 255, 0), 2)

            if rapid_capture and time.time() - last_capture_time >= 0.5:
                os.makedirs(SAVE_DIR, exist_ok=True)
                filename = f"screw_{int(time.time() * 1000)}.png"
                filepath = os.path.join(SAVE_DIR, filename)
                cv2.imwrite(filepath, image)
                capture_count += 1
                last_capture_time = time.time()
                print(f"Rapid capture [{capture_count}]: {filepath}")

            cv2.imshow("Teleop", display)

            key = cv2.waitKey(1) & 0xFF
            if key == 27:
                break

            if key == ord('p'):
                os.makedirs(SAVE_DIR, exist_ok=True)
                filename = f"screw_{int(time.time())}.png"
                filepath = os.path.join(SAVE_DIR, filename)
                cv2.imwrite(filepath, image)
                print(f"Saved: {filepath}")

            if key == ord('r'):
                rapid_capture = not rapid_capture
                if rapid_capture:
                    last_capture_time = 0
                    print("Rapid capture ON - saving every 0.5s")
                else:
                    print(f"Rapid capture OFF - saved {capture_count} images")

            if key == ord('c'):
                if screw:
                    sx, sy, sw, sh = screw
                    target = (sx, sy)
                    save_calibration(sx, sy)
                else:
                    print("No screw detected! Move closer and try again.")

            if key == ord('t'):
                if target:
                    auto_align(sock, pipeline, target)
                else:
                    print("No calibration! Align over a screw and press C first.")

            if key in CONTROLS:
                move = CONTROLS[key]
                print(f"Moving: {move}")
                send_robot_command(sock, {"command": "move", "move": move, "speed": SPEED, "blocking": False})
    finally:
        send_robot_command(sock, {"command": "shutdown"})
        sock.close()
        pipeline.stop()
        cv2.destroyAllWindows()


if __name__ == "__main__":
    main()
