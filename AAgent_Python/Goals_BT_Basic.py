import math
import random
import asyncio
import Sensors
from collections import Counter

def calculate_distance(point_a, point_b):
    distance = math.sqrt((point_b['x'] - point_a['x']) ** 2 +
                         (point_b['y'] - point_a['y']) ** 2 +
                         (point_b['z'] - point_a['z']) ** 2)
    return distance 

class DoNothing:
    """
    Does nothing
    """
    def __init__(self, a_agent):
        self.a_agent = a_agent
        self.rc_sensor = a_agent.rc_sensor
        self.i_state = a_agent.i_state

    async def run(self):
        print("Doing nothing")
        await asyncio.sleep(1)
        return True

class ForwardStop:
    """
        Moves forward till it finds an obstacle. Then stops.
    """
    STOPPED = 0
    MOVING = 1
    END = 2

    def __init__(self, a_agent):
        self.a_agent = a_agent
        self.rc_sensor = a_agent.rc_sensor
        self.i_state = a_agent.i_state
        self.state = self.STOPPED

    async def run(self):
        try:
            while True:
                if self.state == self.STOPPED:
                    # Start moving
                    await self.a_agent.send_message("action", "mf")
                    self.state = self.MOVING
                elif self.state == self.MOVING:
                    sensor_hits = self.rc_sensor.sensor_rays[Sensors.RayCastSensor.HIT]
                    if any(ray_hit == 1 for ray_hit in sensor_hits):
                        self.state = self.END
                        await self.a_agent.send_message("action", "stop")
                    else:
                        await asyncio.sleep(0)
                elif self.state == self.END:
                    break
                else:
                    print("Unknown state: " + str(self.state))
                    return False
        except asyncio.CancelledError:
            print("***** TASK Forward CANCELLED")
            await self.a_agent.send_message("action", "stop")
            self.state = self.STOPPED

class ForwardDist:
    """
        Moves forward a certain distance specified in the parameter "dist".
        If "dist" is -1, selects a random distance between the initial
        parameters of the class "d_min" and "d_max"
    """
    STOPPED = 0
    MOVING = 1
    END = 2

    def __init__(self, a_agent, dist, d_min, d_max):
        self.a_agent = a_agent
        self.rc_sensor = a_agent.rc_sensor
        self.i_state = a_agent.i_state
        self.original_dist = dist
        self.target_dist = dist
        self.d_min = d_min
        self.d_max = d_max
        self.starting_pos = a_agent.i_state.position
        self.state = self.STOPPED

    async def run(self):
        try:
            previous_dist = 0.0  # Used to detect if we are stuck
            while True:
                if self.state == self.STOPPED:
                    # starting position before moving
                    self.starting_pos = self.a_agent.i_state.position
                    # Before start moving, calculate the distance we want to move
                    if self.original_dist < 0:
                        self.target_dist = random.randint(self.d_min, self.d_max)
                    else:
                        self.target_dist = self.original_dist
                    # Start moving
                    await self.a_agent.send_message("action", "mf")
                    self.state = self.MOVING
                    # print("TARGET DISTANCE: " + str(self.target_dist))
                elif self.state == self.MOVING:
                    # If we are moving
                    await asyncio.sleep(0.5)  # Wait for a little movement
                    current_dist = calculate_distance(self.starting_pos, self.i_state.position)
                    # print(f"Current distance: {current_dist}")
                    if current_dist >= self.target_dist:  # Check if we already have covered the required distance
                        await self.a_agent.send_message("action", "ntm")
                        self.state = self.STOPPED
                        return True
                    elif previous_dist == current_dist:  # We are not moving
                        # print(f"previous dist: {previous_dist}, current dist: {current_dist}")
                        # print("NOT MOVING")
                        await self.a_agent.send_message("action", "ntm")
                        self.state = self.STOPPED
                        return False
                    previous_dist = current_dist
                else:
                    print("Unknown state: " + str(self.state))
                    return False
        except asyncio.CancelledError:
            print("***** TASK Forward CANCELLED")
            await self.a_agent.send_message("action", "ntm")
            self.state = self.STOPPED

class Turn:
    """
    Repeats the action of turning a random number of degrees in a random
    direction (right or left)
    """
    LEFT = -1
    RIGHT = 1

    SELECTING = 0
    TURNING = 1

    def __init__(self, a_agent):
        self.a_agent = a_agent
        self.rc_sensor = a_agent.rc_sensor
        self.i_state = a_agent.i_state

        self.current_heading = 0
        self.new_heading = 0

        self.state = self.SELECTING

    async def run(self):
        try:
            while True:
                if self.state == self.SELECTING:
                    # print("SELECTING NEW TURN")
                    rotation_direction = random.choice([-1, 1])
                    # print(f"Rotation direction: {rotation_direction}")
                    rotation_degrees = random.uniform(1, 180) * rotation_direction
                    # print("Degrees: " + str(rotation_degrees))
                    current_heading = self.i_state.rotation["y"]
                    # print(f"Current heading: {current_heading}")
                    self.new_heading = (current_heading + rotation_degrees) % 360
                    if self.new_heading == 360:
                        self.new_heading = 0.0
                    # print(f"New heading: {self.new_heading}")
                    if rotation_direction == self.RIGHT:
                        await self.a_agent.send_message("action", "tr")
                    else:
                        await self.a_agent.send_message("action", "tl")
                    self.state = self.TURNING
                elif self.state == self.TURNING:
                    # check if we have finished the rotation
                    current_heading = self.i_state.rotation["y"]
                    final_condition = abs(current_heading - self.new_heading)
                    if final_condition < 5:
                        await self.a_agent.send_message("action", "nt")
                        current_heading = self.i_state.rotation["y"]
                        # print(f"Current heading: {current_heading}")
                        # print("TURNING DONE.")
                        self.state = self.SELECTING
                        return True
                await asyncio.sleep(0)
        except asyncio.CancelledError:
            print("***** TASK Turn CANCELLED")
            await self.a_agent.send_message("action", "nt")

class GoToBase:
    def __init__(self, a_agent):
        self.a_agent = a_agent
        self.i_state = a_agent.i_state
    async def run(self):
        try: 
            #start walking to basealpha
            await self.a_agent.send_message("action", "stop")
            await asyncio.sleep(0.5)
            await self.a_agent.send_message("action", "walk_to,BaseAlpha")
            alpha_coords = {'x': 32.99653, 'y': 0.3717452, 'z': -32.9364967}
            #poll until the agent stops moving
            while calculate_distance(alpha_coords, self.i_state.position) > 1:
                    if self.a_agent.i_state.isFrozen:
                        print("frozen")

                    # await self.a_agent.send_message("action", "walk_to,BaseAlpha")
                    await asyncio.sleep(0.1) #it is still walking so we wait
            await self.a_agent.send_message("action", "tl")
            await asyncio.sleep(0.5)
            if self.i_state.currentNamedLoc == "BaseAlpha":
                    return True
            else:
                return False
        except asyncio.CancelledError:
            # await self.a_agent.send_message("action", "stop")
            return False

class Unload:
    def __init__(self, a_agent):
        self.a_agent = a_agent
        self.i_state = a_agent.i_state
    async def run(self):
        try:
            if any(item['name']=="AlienFlower" for item in self.i_state.myInventoryList):
                await self.a_agent.send_message("action", "leave,AlienFlower,2")
                await asyncio.sleep(0.5)
                return True
            return False
        except asyncio.CancelledError:
            return False

class MoveToFlower:
    def __init__(self, a_agent):
        self.a_agent = a_agent
        self.i_state = a_agent.i_state
        self.rc_sensor = a_agent.rc_sensor

    def get_smallest_angle(self):
        smallest_angle_index = None
        smallest_abs_angle = float("inf")

        angles = self.rc_sensor.sensor_rays[Sensors.RayCastSensor.ANGLE]
        objects = self.rc_sensor.sensor_rays[Sensors.RayCastSensor.OBJECT_INFO]

        for i, (angle, sensor_data) in enumerate(zip(angles, objects)):
            if not sensor_data:
                continue
            if sensor_data.get("tag") != "AlienFlower":
                continue

            abs_angle = abs(angle)
            if abs_angle < smallest_abs_angle:
                smallest_abs_angle = abs_angle
                smallest_angle_index = i

        return smallest_angle_index
    
    async def approach_flower(self, timeout=3.0):
        def get_flowers_count():
            inventory = self.a_agent.i_state.myInventoryList
            return inventory[0]["amount"] if inventory else 0

        original_num_flowers = get_flowers_count()
        await self.a_agent.send_message("action", "stop")
        await self.a_agent.send_message("action", "mf")

        poll_interval = 0.5

        while True:
            await self.a_agent.send_message("action", "mf")
            if get_flowers_count() > original_num_flowers:
                await self.a_agent.send_message("action", "stop")
                return True

            if self.get_smallest_angle() is None:
                await self.a_agent.send_message("action", "stop")
                return False

            await asyncio.sleep(poll_interval)

    async def run(self):
        try:
            smallest_angle_index = self.get_smallest_angle()
            if smallest_angle_index is None:
                await self.a_agent.send_message("action", "nt")
                return False
            angle = self.rc_sensor.sensor_rays[Sensors.RayCastSensor.ANGLE][smallest_angle_index]
            if abs(angle) <= 1e-6:
                res = await self.approach_flower()
            
                await asyncio.sleep(0.5)
                return res
            else:
                await self.a_agent.send_message("action", "tl" if angle < 0 else "tr")
                await asyncio.sleep(0.5)
                return False

        except asyncio.CancelledError:
            await self.a_agent.send_message("action", "nt")
            return False
class Wander:
    def __init__(self, a_agent):
        self.a_agent = a_agent
        self.rc_sensor = a_agent.rc_sensor
        self._last_turn = None

    async def _do_action_for(self, action, duration, stop_action="stop"):
        await self.a_agent.send_message("action", action)
        await asyncio.sleep(duration)
        await self.a_agent.send_message("action", stop_action)

    def _choose_turn_direction(self):
        if self._last_turn is not None and random.random() < 0.65:
            return self._last_turn
        self._last_turn = random.choice(["tl", "tr"])
        return self._last_turn

    def _is_blocking_object(self, sensor_data):
        if not sensor_data:
            return False
        tag = sensor_data.get("tag")
        return tag in {"Wall", "Rock"}

    def _get_blocked_rays(self):
        angles = self.rc_sensor.sensor_rays[Sensors.RayCastSensor.ANGLE]
        objects = self.rc_sensor.sensor_rays[Sensors.RayCastSensor.OBJECT_INFO]

        blocked = []
        for angle, sensor_data in zip(angles, objects):
            if self._is_blocking_object(sensor_data):
                blocked.append((angle, sensor_data))
        return blocked

    def _front_is_blocked(self, front_angle=25):
        blocked = self._get_blocked_rays()
        return any(abs(angle) <= front_angle for angle, _ in blocked)

    def _side_block_scores(self, side_angle_threshold=10):
        """
        Returns how blocked the left and right sides are.
        Lower abs(angle) means more dangerous because it is closer to straight ahead.
        """
        blocked = self._get_blocked_rays()

        left_score = 0.0
        right_score = 0.0

        for angle, _ in blocked:
            weight = max(0.0, 100.0 - abs(angle))  # more weight if closer to center
            if angle < -side_angle_threshold:
                left_score += weight
            elif angle > side_angle_threshold:
                right_score += weight
            else:
                # near the center, count toward both a bit
                left_score += weight * 0.5
                right_score += weight * 0.5

        return left_score, right_score

    def _escape_turn_direction(self):
        left_score, right_score = self._side_block_scores()

        # if left side is more blocked, turn right
        if left_score > right_score:
            self._last_turn = "tr"
            return "tr"

        # if right side is more blocked, turn left
        if right_score > left_score:
            self._last_turn = "tl"
            return "tl"

        # tie -> keep some persistence or choose randomly
        return self._choose_turn_direction()

    async def run(self):
        try:
            # 1) If something undesirable is in front, escape first
            if self._front_is_blocked(front_angle=25):
                direction = self._escape_turn_direction()

                # bigger turn when front is blocked
                await self._do_action_for(direction, random.uniform(0.45, 0.9), stop_action="nt")
                return True

            # 2) Otherwise do normal natural wandering
            r = random.random()

            if r < 0.65:
                # mostly forward
                await self._do_action_for("mf", random.uniform(0.8, 1.6))

            elif r < 0.88:
                # small turn
                direction = self._choose_turn_direction()
                await self._do_action_for(direction, random.uniform(0.12, 0.3), stop_action="nt")

            else:
                # bigger random turn
                direction = self._choose_turn_direction()
                await self._do_action_for(direction, random.uniform(0.35, 0.75), stop_action="nt")

            return True

        except asyncio.CancelledError:
            await self.a_agent.send_message("action", "stop")
            await self.a_agent.send_message("action", "nt")
            return False
        

class EvadeCritter:
    def __init__(self, a_agent):
        self.a_agent = a_agent
        self.rc_sensor = a_agent.rc_sensor
        self.i_state = a_agent.i_state

    def _get_critter_rays(self):
        angles = self.rc_sensor.sensor_rays[Sensors.RayCastSensor.ANGLE]
        objects = self.rc_sensor.sensor_rays[Sensors.RayCastSensor.OBJECT_INFO]

        critter_rays = []
        for angle, sensor_data in zip(angles, objects):
            if sensor_data and sensor_data.get("tag") == "CritterMantaRay":
                critter_rays.append((angle, sensor_data))
        return critter_rays

    def _choose_escape_direction(self):
        """
        If the critter is mostly on the left, turn right.
        If the critter is mostly on the right, turn left.
        More centered critters count more heavily.
        """
        critter_rays = self._get_critter_rays()

        left_score = 0.0
        right_score = 0.0

        for angle, _ in critter_rays:
            weight = max(0.0, 100.0 - abs(angle))
            if angle < 0:
                left_score += weight
            elif angle > 0:
                right_score += weight
            else:
                left_score += weight * 0.5
                right_score += weight * 0.5

        if left_score > right_score:
            return "tr"   # critter is more on left -> turn right away from it
        elif right_score > left_score:
            return "tl"   # critter is more on right -> turn left away from it
        else:
            return random.choice(["tl", "tr"])

    async def run(self):
        try:
            critter_rays = self._get_critter_rays()
            if not critter_rays:
                return False
            print("DETECTEDDDDDD")
            direction = self._choose_escape_direction()
            print(direction)
            # stop whatever we were doing first
            # await self.a_agent.send_message("action", "stop")


            # turn away from the critter
            await self.a_agent.send_message("action", direction)
            await self.a_agent.send_message("action", "mf")
            await asyncio.sleep(random.uniform(0.5, 1.0))
            await self.a_agent.send_message("action", "stop")


            return True

        except asyncio.CancelledError:
            await self.a_agent.send_message("action", "stop")
            await self.a_agent.send_message("action", "nt")
            return False