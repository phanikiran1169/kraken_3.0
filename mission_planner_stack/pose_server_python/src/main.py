import roslib;roslib.load_manifest('mission_planner')
import rospy
import rospy
import time
from resources import topicHeader

import kraken_msgs
import kraken_msgs
from kraken_msgs.msg._imuData import imuData
from kraken_msgs.msg._dvlData import dvlData

from kalman_estimator import *

dt = 0.1
NUM_VARIABLE_IN_STATE = 4
INDEX_VEL_X = 3
INDEX_VEL_Y = 4
CONVERTED_TO_WORLD = False
FIRST_ITERATION = True
base_roll = 0
base_pitch = 0
base_yaw = 0

# state = [position-x, position-y, velocity-x, velocity-y]
state = matrix([[0.0], [0.0], [0.], [0.]]) # initial state (location and velocity)
statefilled = 2
measurements = [[0.0, 0.0]]
P = matrix([[1000., 0., 0., 0.], [0., 1000., 0., 0.], [0., 0., 0, 0.], [0., 0., 0., 0]])# initial uncertainty

oldtime = 0
def dvlCallback2(dvl):
	global oldtime
	t = dvl.data

	if oldtime == 0:

		oldtime = time.time()
		# print t[3], t[4]
		return

	if time.time() - oldtime >= 1:

		oldtime = time.time()
		# print t[3], t[4]

def imuCallback(imu):
	global statefilled
	global state
	global CONVERTED_TO_WORLD
	global base_roll
	global base_pitch
	global base_yaw

	vx = state.getvalue(INDEX_VEL_X, 1)
	vy = state.getvalue(INDEX_VEL_Y, 1)

	# yaw, pitch, roll

	roll = imu.data[0]
	pitch = imu.data[1]
	yaw = imu.data[2]

	if FIRST_ITERATION:

		base_roll = roll
		base_pitch = pitch
		base_yaw = yaw
		FIRST_ITERATION = False

	roll = roll - base_roll
	pitch = pitch - base_pitch
	yaw = yaw - base_yaw

	print "IMU (Corrected): ", roll, pitch, yaw

	## Convert the roll, pitch and yaw to radians.

	yaw = yaw * 3.14 / 180
	roll = roll * 3.14 / 180
	pitch = pitch * 3.14 / 180

	bodytoworld = matrix(
		[[cos(yaw) * cos(pitch), 
		 sin(yaw) * cos(pitch), 
		 -1 * sin(pitch)
		],

		[cos(yaw) * sin(pitch) * sin(roll) - sin(yaw) * cos(roll), 
		 sin(yaw) * sin(pitch) * sin(roll) + cos(yaw) * cos(roll),
		 cos(pitch) * sin(roll)
		],
		[cos(yaw) * sin(pitch) * cos(roll) + sin(yaw) * sin(roll),
		 sin(yaw) * sin(pitch) * cos(roll) - cos(yaw) * sin(roll),
		 cos(pitch) * cos(roll)
		]])

	# print bodytoworld

	# import numpy
	# print numpy.linalg.det(bodytoworld.value)

	# bodytoworld.show()

	vel_wrt_body = matrix([[vx],[vy],[0.]])

	vel_wrt_world = bodytoworld * vel_wrt_body

	# vel_wrt_world.show()

	CONVERTED_TO_WORLD = True

	# print "Entered IMU callback!"

def dvlCallback(dvl):
	global state
	global measurements
	global statefilled

	# print dvl.data

	# print "Entered DVL callback!"

	## Extract from the variable dvl

	# vx = int(raw_input("Enter vx: "))
	# vy = int(raw_input("Enter vy: "))

	vx = dvl.data[3]
	vy = -1 * dvl.data[4]

	# print vx, vy

	roll = dvl.data[0]
	pitch = dvl.data[1]
	yaw = dvl.data[2]

	# print "DVL: ", roll, pitch, yaw
	## End extract step

	this_iteration_measurement = [vx, vy]

	state.setvalue(INDEX_VEL_X, 1, vx)
	state.setvalue(INDEX_VEL_Y, 1, vy)

	statefilled += 2	
	measurements.append(this_iteration_measurement)

# subscribe to IMU and DVL

# extract pitch and yaw from IMU
# extract vx and vy from DVL
# take positions state and y from previous state. (Take (state, y) = (0, 0) initially.)

imu_topic_name = topicHeader.SENSOR_IMU
dvl_topic_name = topicHeader.SENSOR_DVL

# print imu_topic_name
# print dvl_topic_name

rospy.init_node('pose_server_python_node', anonymous=True)

rospy.Subscriber(name=imu_topic_name, data_class=imuData, callback=imuCallback)
rospy.Subscriber(name=dvl_topic_name, data_class=dvlData, callback=dvlCallback)

while(1):

	# if all the data has been accumulated in the state variable

	if(statefilled >= NUM_VARIABLE_IN_STATE and CONVERTED_TO_WORLD):

		(new_state, new_P) = kalman_estimate(state, P, measurements[-1])

		state.setvalue(1, 1, new_state.getvalue(1, 1))
		state.setvalue(2, 1, new_state.getvalue(2, 1))

		statefilled = 2
		CONVERTED_TO_WORLD = False

		# print "new state: "
		# new_state.show()
		# print "new P matrix: "
		# new_P.show()
		
		P = matrix(new_P.value)

rospy.spin()
