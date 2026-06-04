import __common
__common.init_env()
import jkrc
import time

cobot = jkrc.RC("192.168.10.200")
cobot.login()
cobot.power_on()
cobot.enable_robot()
time.sleep(1)

result = cobot.linear_move([50, 0, 0, 0, 0, 0], 1, False, 50)
print(f"Return code: {result}")
