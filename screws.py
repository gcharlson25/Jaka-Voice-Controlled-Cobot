import time
import math

import __common
__common.init_env()
import jkrc

ABS_MOVEMENT = 0
INCREMENT_MOVEMENT = 1

TCP = [0, 0, 0, 0, 0, 0]
USR = [0, 0, 0, 0, 0, 0]

IO_CABINET = 0
ON = 1
OFF = 0
FASTENING = 9
UNFASTENING = 10

HOME_JOINT = [math.radians(x) for x in [-273.900, 135.500, -115.723, 53.620, -91.834, -269.114]]
SCREW1_UNFASTEN_START_JOINT = [math.radians(x) for x in [-270.604, 88.638, -113.402, 22.755, -85.769, -270.021]]
SCREW1_FASTEN_START_JOINT = [math.radians(x) for x in [-270.604, 89.872, -110.948, 19.068, -85.769, -270.021]]
SCREW2_UNFASTEN_START_JOINT = [math.radians(x) for x in [-284.456, 90.744, -115.951, 23.175, -99.613, -270.509]]
SCREW2_FASTEN_START_JOINT = [math.radians(x) for x in [-284.258, 91.696, -114.118, 20.392, -99.415, -270.502]]
SCREW3_UNFASTEN_START_JOINT = [math.radians(x) for x in [-290.949, 91.169, -115.612, 22.357, -106.102, -270.748]]
SCREW3_FASTEN_START_JOINT = [math.radians(x) for x in [-291.198, 91.983, -114.005, 19.935, -106.350, -270.757]]
SCREW4_UNFASTEN_START_JOINT = [math.radians(x) for x in [-297.310, 90.678, -115.132, 22.285, -112.458, -270.998]]
SCREW4_FASTEN_START_JOINT = [math.radians(x) for x in [-297.542, 91.465, -113.507, 19.872, -112.690, -271.007]]
SCREW5_UNFASTEN_START_JOINT = [math.radians(x) for x in [-303.322, 89.537, -113.995, 22.178, -118.466, -271.256]]
SCREW5_FASTEN_START_JOINT = [math.radians(x) for x in [-303.521, 90.297, -112.363, 19.783, -118.664, -271.265]]

ENGAGE = [0, 0, -7.5, 0, 0, 0]
DISENGAGE = [0, 0, 75, 0, 0, 0]
UNFASTEN = [0, 0, 40, 0, 0, 0]
FASTEN = [0, 0, -24, 0, 0, 0]

def coordinateSetup(cobot):
    print("setting TCP")
    cobot.set_tool_data(5, TCP, "tool_screw_test")
    cobot.set_tool_id(5)

    print("setting USR") 
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
    print("setting outputs")
    cobot.set_digital_output(IO_CABINET, FASTENING,  OFF)
    cobot.set_digital_output(IO_CABINET, UNFASTENING, OFF)
    coordinateSetup(cobot)
    return cobot

def fastenScrewOperation(cobot):
    cobot.set_digital_output(IO_CABINET, FASTENING, ON)
    time.sleep(2)
    cobot.linear_move(ENGAGE, INCREMENT_MOVEMENT, True, 25)
    cobot.linear_move(FASTEN, INCREMENT_MOVEMENT, True, 25)
    cobot.set_digital_output(IO_CABINET, FASTENING, OFF)
    cobot.linear_move(DISENGAGE, INCREMENT_MOVEMENT, True, 500)

def unfastenScrewOperation(cobot):
    time.sleep(2)
    cobot.linear_move(ENGAGE, INCREMENT_MOVEMENT, True, 2000)
    cobot.set_digital_output(IO_CABINET, UNFASTENING, ON)
    cobot.linear_move(UNFASTEN, INCREMENT_MOVEMENT, True, 15)
    cobot.set_digital_output(IO_CABINET, UNFASTENING, OFF)
    cobot.linear_move(DISENGAGE, INCREMENT_MOVEMENT, True, 500)

def unfastenScrew1(cobot):
    print("unfastening screw one")
    cobot.joint_move(SCREW1_UNFASTEN_START_JOINT, ABS_MOVEMENT, True, 2)
    unfastenScrewOperation(cobot)

def fastenScrew1(cobot):
    print("fastening screw one")
    cobot.joint_move(SCREW1_FASTEN_START_JOINT, ABS_MOVEMENT, True, 2)
    fastenScrewOperation(cobot)

def unfastenScrew2(cobot):
    print("unfastening screw two")
    cobot.joint_move(SCREW2_UNFASTEN_START_JOINT, ABS_MOVEMENT, True, 2)
    unfastenScrewOperation(cobot)

def fastenScrew2(cobot):
    print("fastening screw two")
    cobot.joint_move(SCREW2_FASTEN_START_JOINT, ABS_MOVEMENT, True, 2)
    fastenScrewOperation(cobot)

def unfastenScrew3(cobot):
    print("unfastening screw three")
    cobot.joint_move(SCREW3_UNFASTEN_START_JOINT, ABS_MOVEMENT, True, 2)
    unfastenScrewOperation(cobot)

def fastenScrew3(cobot):
    print("fastening screw three")
    cobot.joint_move(SCREW3_FASTEN_START_JOINT, ABS_MOVEMENT, True, 2)
    fastenScrewOperation(cobot)

def unfastenScrew4(cobot):
    print("unfastening screw four")
    cobot.joint_move(SCREW4_UNFASTEN_START_JOINT, ABS_MOVEMENT, True, 2)
    unfastenScrewOperation(cobot)

def fastenScrew4(cobot):
    print("fastening screw four")
    cobot.joint_move(SCREW4_FASTEN_START_JOINT, ABS_MOVEMENT, True, 2)
    fastenScrewOperation(cobot)

def unfastenScrew5(cobot):
    print("unfastening screw five")
    cobot.joint_move(SCREW5_UNFASTEN_START_JOINT, ABS_MOVEMENT, True, 2)
    unfastenScrewOperation(cobot)

def fastenScrew5(cobot):
    print("fastening screw five")
    cobot.joint_move(SCREW5_FASTEN_START_JOINT, ABS_MOVEMENT, True, 2)
    fastenScrewOperation(cobot)

def unfastenAll(cobot):
    unfastenScrew1(cobot)
    unfastenScrew2(cobot)
    unfastenScrew3(cobot)
    unfastenScrew4(cobot)
    unfastenScrew5(cobot)

def fastenAll(cobot):
    fastenScrew1(cobot)
    fastenScrew2(cobot)
    fastenScrew3(cobot)
    fastenScrew4(cobot)
    fastenScrew5(cobot)

def unfastenThenFasten(cobot):
    unfastenScrew1(cobot)
    unfastenScrew2(cobot)
    unfastenScrew3(cobot)
    unfastenScrew4(cobot)
    unfastenScrew5(cobot)    
    fastenScrew1(cobot)
    fastenScrew2(cobot)
    fastenScrew3(cobot)
    fastenScrew4(cobot)
    fastenScrew5(cobot)

def allOneAtATime(cobot):
    unfastenScrew1(cobot)
    fastenScrew1(cobot)
    unfastenScrew2(cobot)
    fastenScrew2(cobot)
    unfastenScrew3(cobot)
    fastenScrew3(cobot)
    unfastenScrew4(cobot)
    fastenScrew4(cobot)
    unfastenScrew5(cobot)
    fastenScrew5(cobot)

def main():
    cobot = cobotSetup()
    cobot.joint_move(HOME_JOINT, ABS_MOVEMENT, True, 2)
    cobot.set_digital_output(IO_CABINET, FASTENING,  OFF)
    cobot.set_digital_output(IO_CABINET, UNFASTENING, OFF)
    unfastenAll(cobot)
    fastenAll(cobot)
    cobot.set_digital_output(IO_CABINET, FASTENING,  OFF)
    cobot.set_digital_output(IO_CABINET, UNFASTENING, OFF)
    cobot.joint_move(HOME_JOINT, ABS_MOVEMENT, True, 2) 
        
if __name__ == '__main__':
    main()    

