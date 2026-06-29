import __common
__common.init_env()
import jkrc

import pyrealsense2 as rs
import numpy as np
import cv2
import os
import time

ABS = 0
INCR = 1
SPEED = 250
STEP = 1

TCP = [0, 0, 0, 0, 0, 0]
USR = [0, 0, 0, 0, 0, 0]

SAVE_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "screw_adjustment")

CONTROLS = {
    ord('w'): [0, -STEP, 0, 0, 0, 0],   # backward (-Y)
    ord('s'): [0, STEP, 0, 0, 0, 0],     # forward (+Y)
    ord('d'): [-STEP, 0, 0, 0, 0, 0],    # right (-X)
    ord('a'): [STEP, 0, 0, 0, 0, 0],     # left (+X)
    ord('e'): [0, 0, STEP, 0, 0, 0],     # up (+Z)
    ord('q'): [0, 0, -STEP, 0, 0, 0],    # down (-Z)
}


def setup_robot():
    cobot = jkrc.RC("192.168.10.200")
    cobot.login()
    cobot.power_on()
    cobot.enable_robot()
    cobot.set_payload(mass=0.5, centroid=[0, 0, 20])
    cobot.set_tool_data(5, TCP, "tool_teleop")
    cobot.set_tool_id(5)
    cobot.set_user_frame_data(6, USR, "user_teleop")
    cobot.set_user_frame_id(6)
    return cobot


def setup_camera():
    pipeline = rs.pipeline()
    config = rs.config()
    config.enable_stream(rs.stream.color, 640, 480, rs.format.bgr8, 30)
    pipeline.start(config)
    return pipeline


def main():
    cobot = setup_robot()
    pipeline = setup_camera()

    cv2.namedWindow("Teleop", cv2.WINDOW_NORMAL)
    cv2.resizeWindow("Teleop", 1280, 960)

    print("Teleop ready!")
    print("  W = backward, S = forward")
    print("  A = left,     D = right")
    print("  Q = down,     E = up")
    print("  ESC = quit")

    try:
        while True:
            frames = pipeline.wait_for_frames()
            color_frame = frames.get_color_frame()
            if not color_frame:
                continue

            image = np.asanyarray(color_frame.get_data())

            cv2.putText(image, "W/S: back/fwd  A/D: left/right  Q/E: down/up  P: photo  ESC: quit",
                        (10, 30), cv2.FONT_HERSHEY_SIMPLEX, 0.55, (0, 255, 0), 2)

            cv2.imshow("Teleop", image)

            key = cv2.waitKey(1) & 0xFF
            if key == 27:
                break

            if key == ord('p'):
                os.makedirs(SAVE_DIR, exist_ok=True)
                filename = f"screw_{int(time.time())}.png"
                filepath = os.path.join(SAVE_DIR, filename)
                cv2.imwrite(filepath, image)
                print(f"Saved: {filepath}")

            if key in CONTROLS:
                move = CONTROLS[key]
                print(f"Moving: {move}")
                cobot.linear_move(move, INCR, False, SPEED)
    finally:
        pipeline.stop()
        cv2.destroyAllWindows()
        cobot.disable_robot()
        cobot.logout()


if __name__ == "__main__":
    main()
