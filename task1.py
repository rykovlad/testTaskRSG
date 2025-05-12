#  --home=50.450739,30.461242,0,0

import time
from dronekit import connect, VehicleMode, LocationGlobalRelative
import math
import enum
from loguru import logger


def connect_uav():
    connection_string = "tcp:127.0.0.1:5762"
    logger.info(f'Connecting to vehicle on: {connection_string}')
    return connect(connection_string, wait_ready=True)

# Connecting to a vehicle
vehicle = connect_uav()


def channel_override(overrides):
    vehicle.channels.overrides = {**vehicle.channels.overrides, **overrides}
    logger.info(vehicle.channels.overrides)


def arm_and_takeoff(altitude):
    logger.info("Basic pre-arm checks")
    # Don't try to arm until autopilot is ready
    while not vehicle.is_armable:
        logger.info(" Waiting for vehicle to initialise...")
        time.sleep(1)

    logger.info("Arming motors")
    # Copter should arm in GUIDED mode
    vehicle.mode = VehicleMode("ALT_HOLD")
    vehicle.armed = True

    # Confirm vehicle armed before attempting to take off
    while not vehicle.armed:
        logger.info(" Waiting for arming...")
        time.sleep(1)

    logger.success("Taking off!")

    logger.info("Cleaning all channel overrides")
    channel_override({'1': 1500, '2': 1500, '3': 1500, '4': 1500})

    while True:
        channel_override({'3': 2000})
        logger.info(f" Altitude: {vehicle.location.global_relative_frame.alt}")
        if vehicle.location.global_relative_frame.alt >= altitude:
            logger.info("Reached target altitude")
            break
        time.sleep(1)
    channel_override({'3': 1500})
    logger.success("Target altitude has been reached")


class RangeCheck(enum.Enum):
    IN_RANGE = 1
    NEED_LESS = 2
    NEED_MORE = 3


def is_heading_in_range(from_degrees, to_degrees, current_degrees):
    if from_degrees > to_degrees:  # the case, when from is less than 0 degress (which becomes from + 360)
        if current_degrees > from_degrees or current_degrees < to_degrees:
            return RangeCheck.IN_RANGE
        else:
            delta_to_mediana = (from_degrees - to_degrees) / 2
            return RangeCheck.NEED_MORE if from_degrees - delta_to_mediana < current_degrees else RangeCheck.NEED_LESS
    else:
        if current_degrees < from_degrees:
            return RangeCheck.NEED_MORE
        elif current_degrees > to_degrees:
            return RangeCheck.NEED_LESS
        else:
            return RangeCheck.IN_RANGE


def do_yaw(heading, allowed_deviation_in_degrees=10, forse_clockwise=False):
    logger.info(f"Do yaw up to {heading} degrees...")
    # Wait until the vehicle reaches the target point
    if allowed_deviation_in_degrees >= 10:
        speed_delta = 50
    else:
        speed_delta = 40

    while True:
        logger.info(f"Curr heading in degrees: {vehicle.heading}")
        # Break and return from function just below target altitude.
        from_range = bearing_plus_delta_and_normalize(heading, -allowed_deviation_in_degrees)
        to_range = bearing_plus_delta_and_normalize(heading, allowed_deviation_in_degrees)
        range_check = is_heading_in_range(from_range, to_range, vehicle.heading)
        if range_check == RangeCheck.IN_RANGE:
            logger.success("Reached target heading")
            channel_override({'4': 1500})
            break
        elif range_check == RangeCheck.NEED_MORE or forse_clockwise:
            logger.info(f"Heading right")
            channel_override({'4': 1500 + speed_delta})
        elif range_check == RangeCheck.NEED_LESS:
            logger.info(f"Heading left")
            channel_override({'4': 1500 - speed_delta})

        time.sleep(0.2)


def get_distance_metres(loc1, loc2):
    dlat = loc2.lat - loc1.lat
    dlong = loc2.lon - loc1.lon
    return math.sqrt((dlat * dlat) + (dlong * dlong)) * 1.113195e5


def distance_bearing(home_latitude, home_longitude, destination_latitude, destination_longitude):

    rlat1 = home_latitude * (math.pi / 180)
    rlat2 = destination_latitude * (math.pi / 180)
    rlon1 = home_longitude * (math.pi / 180)
    rlon2 = destination_longitude * (math.pi / 180)

    # Formula for bearing
    y = math.sin(rlon2 - rlon1) * math.cos(rlat2)
    x = math.cos(rlat1) * math.sin(rlat2) - math.sin(rlat1) * math.cos(rlat2) * math.cos(rlon2 - rlon1)

    # Bearing in radians
    bearing = math.atan2(y, x)
    bearing_degrees = bearing * (180 / math.pi)
    bearing_degrees_normalised_to_positive = bearing_plus_delta_and_normalize(bearing_degrees)
    return bearing_degrees_normalised_to_positive


def bearing_plus_delta_and_normalize(bearing, delta=0):
    return (bearing + delta + 360) % 360


def move_to_point(point):

    logger.info("Moving to location...")

    # Wait until the vehicle reaches the target point
    while True:
        bearing_degrees = distance_bearing(
            vehicle.location.global_relative_frame.lat, vehicle.location.global_relative_frame.lon,
            point.lat, point.lon
        )
        remaining_distance = get_distance_metres(vehicle.location.global_relative_frame, point)

        logger.info(f"Distance to target: {remaining_distance} meters")
        logger.info(f"Bearing degress   : {bearing_degrees}")

        if remaining_distance < 1:
            logger.success("")
            logger.success("******** Reached target! *****\n")
            logger.success("")
            channel_override({'2': 1510})
            time.sleep(0.1)
            channel_override({'2': 1500})
            break

        # constantly track bearing. If it riches the allowed deviation, we should do way to required bearing delta
        allowed_yaw_deviation_in_degrees = 5
        yaw_deviation_corrective_treshold = allowed_yaw_deviation_in_degrees + 5  # adding 5 here just to have some space and not constantly fix bearing
        if abs(bearing_plus_delta_and_normalize(bearing_degrees, -vehicle.heading)) > yaw_deviation_corrective_treshold:
            do_yaw(bearing_degrees, allowed_yaw_deviation_in_degrees)

        if remaining_distance < 150:
            pitch = round(1400 + 77 - (
                        77 * remaining_distance / 100))  # The closer the target, the lower the UAV's speed should be
            channel_override({'2': pitch})
        else:
            channel_override({'2': 1000})

        time.sleep(1)


arm_and_takeoff(100)
move_to_point(LocationGlobalRelative(50.443326, 30.448078, 100))

# Yaw
logger.info("Yaw 350 digrees relative to the UAV")
logger.info(f"Current bearing: {vehicle.heading}")
target_bearing = bearing_plus_delta_and_normalize(vehicle.heading, 350)
logger.info(f"Target bearing: {target_bearing}")
do_yaw(target_bearing, 1, forse_clockwise=True)

# Close vehicle object before exiting script
logger.success("")
logger.success("All tasks were completed")
logger.success("")
logger.info("Closing vehicle object....")
vehicle.close()