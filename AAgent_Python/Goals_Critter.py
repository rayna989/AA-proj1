import math
import random
import asyncio
import Sensors


def calculate_distance(point_a, point_b):
    distance = math.sqrt(
        (point_b['x'] - point_a['x']) ** 2 +
        (point_b['y'] - point_a['y']) ** 2 +
        (point_b['z'] - point_a['z']) ** 2
    )
    return distance


def astronaut_detected(rc_sensor):
    """
    Returns True if any ray sees an astronaut.
    """
    try:
        sensor_obj_info = rc_sensor.sensor_rays[Sensors.RayCastSensor.OBJECT_INFO]
        for obj in sensor_obj_info:
            if obj and "Astronaut" in obj.get("tag", ""):
                return True
    except Exception:
        pass
    return False


class DoNothing:
    def __init__(self, a_agent):
        self.a_agent = a_agent

    async def run(self):
        print("Doing nothing")
        await asyncio.sleep(1)
        return True


class ForwardStop:
    """
    Moves forward until obstacle is detected in the FRONT rays only.
    Used for actual physical chase / roam forward.
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
                    await self.a_agent.send_message("action", "mf")
                    self.state = self.MOVING

                elif self.state == self.MOVING:
                    sensor_hits = self.rc_sensor.sensor_rays[Sensors.RayCastSensor.HIT]
                    n = len(sensor_hits)

                    if n == 0:
                        await asyncio.sleep(0.05)
                        continue

                    mid = n // 2
                    front_indices = [mid]
                    if mid - 1 >= 0:
                        front_indices.append(mid - 1)
                    if mid + 1 < n:
                        front_indices.append(mid + 1)

                    obstacle_ahead = any(sensor_hits[i] == 1 for i in front_indices)

                    if obstacle_ahead:
                        await self.a_agent.send_message("action", "stop")
                        self.state = self.END
                    else:
                        await asyncio.sleep(0.05)

                elif self.state == self.END:
                    self.state = self.STOPPED
                    return True

                else:
                    print("Unknown state: " + str(self.state))
                    self.state = self.STOPPED
                    return False

        except asyncio.CancelledError:
            print("***** TASK ForwardStop CANCELLED")
            await self.a_agent.send_message("action", "stop")
            self.state = self.STOPPED
            return False


class ForwardDist:
    """
    Moves forward a target distance.
    If dist == -1, picks a random distance between d_min and d_max.
    Also exits early if astronaut is detected.
    """
    STOPPED = 0
    MOVING = 1

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
            if self.original_dist < 0:
                self.target_dist = random.uniform(self.d_min, self.d_max)
            else:
                self.target_dist = self.original_dist

            self.starting_pos = dict(self.i_state.position)
            await self.a_agent.send_message("action", "mf")

            stuck_counter = 0
            last_dist = 0.0

            while True:
                await asyncio.sleep(0.1)

                current_dist = calculate_distance(self.starting_pos, self.i_state.position)

                if current_dist >= self.target_dist:
                    await self.a_agent.send_message("action", "ntm")
                    return True

                if abs(current_dist - last_dist) < 0.01:
                    stuck_counter += 1
                else:
                    stuck_counter = 0

                if stuck_counter >= 5:
                    await self.a_agent.send_message("action", "ntm")
                    return False

                last_dist = current_dist

        except asyncio.CancelledError:
            print("***** TASK ForwardDist CANCELLED")
            await self.a_agent.send_message("action", "ntm")
            return False


class Turn:
    """
    Simple random turn for roaming.
    Turn left or right for a short random duration, then stop.
    Exits early if astronaut is detected.
    """
    def __init__(self, a_agent):
        self.a_agent = a_agent
        self.rc_sensor = a_agent.rc_sensor
        self.i_state = a_agent.i_state

    async def run(self):
        try:
            direction = random.choice(["tr", "tl"])
            turn_time = random.uniform(0.2, 0.6)

            print(f"[Goal] Sending {direction} for {turn_time:.2f}s")
            await self.a_agent.send_message("action", direction)

            elapsed = 0.0
            step = 0.05

            while elapsed < turn_time:
                # stop turn immediately if astronaut appears
                if astronaut_detected(self.rc_sensor):
                    await self.a_agent.send_message("action", "nt")
                    await asyncio.sleep(0.05)
                    return True

                await asyncio.sleep(step)
                elapsed += step

            print("[Goal] Sending nt")
            await self.a_agent.send_message("action", "nt")
            await asyncio.sleep(0.1)

            return True

        except asyncio.CancelledError:
            print("***** TASK Turn CANCELLED")
            await self.a_agent.send_message("action", "nt")
            return False


class EscapeSequence:
    """
    Physically separates from the astronaut after a bite/stun.
    Moves back 3 times, then turns left twice.
    """
    def __init__(self, a_agent):
        self.a_agent = a_agent

    async def run(self):
        try:
            print("[Goal:Escape] Executing Back-steps...")
            for _ in range(3):
                await self.a_agent.send_message("action", "mb")
                await asyncio.sleep(0.35)
                await self.a_agent.send_message("action", "stop")
                await asyncio.sleep(0.05)

            print("[Goal:Escape] Executing Left-turns...")
            for _ in range(2):
                await self.a_agent.send_message("action", "tl")
                await asyncio.sleep(0.35)
                await self.a_agent.send_message("action", "nt")
                await asyncio.sleep(0.05)

            await self.a_agent.send_message("action", "stop")
            return True

        except asyncio.CancelledError:
            print("***** TASK EscapeSequence CANCELLED")
            await self.a_agent.send_message("action", "stop")
            return False


class MoveToAstronaut:
    """
    Aggressively chases the astronaut as fast as possible.

    Key improvements over the original:
    - Loop runs every 0.02s (50Hz) instead of 0.1s (10Hz) — 5x faster reactions
    - Moves forward AND turns at the same time instead of stopping to turn
    - Only sends a new action when the decision actually changes, avoiding
      redundant messages that waste a tick doing nothing new
    - Tolerates up to LOST_FRAMES consecutive frames of no detection before
      giving up, so a brief occlusion doesn't abort the chase
    """

    LOST_FRAMES = 8   # frames of no detection before giving up (~0.16s at 50Hz)
    CENTER_TOL  = 1   # ray index tolerance to count as "centred"

    def __init__(self, a_agent):
        self.a_agent = a_agent
        self.rc_sensor = a_agent.rc_sensor

    async def run(self):
        last_action  = None   # track last sent action to avoid redundant sends
        lost_counter = 0

        try:
            while True:
                sensor_obj_info = self.rc_sensor.sensor_rays[Sensors.RayCastSensor.OBJECT_INFO]
                sensor_hits     = self.rc_sensor.sensor_rays[Sensors.RayCastSensor.HIT]

                n   = len(sensor_hits)
                mid = n // 2

                # --- find best (most centred) astronaut ray ---
                best_idx  = None
                best_dist = None
                best_off  = None

                for index, value in enumerate(sensor_obj_info):
                    if value and value.get("tag") == "Astronaut":
                        offset = abs(index - mid)
                        if best_off is None or offset < best_off:
                            best_idx  = index
                            best_dist = value.get("distance", None)
                            best_off  = offset

                if best_idx is None:
                    # astronaut not visible this frame
                    lost_counter += 1
                    if lost_counter >= self.LOST_FRAMES:
                        await self.a_agent.send_message("action", "stop")
                        print("[Goal:MoveToAstronaut] Lost astronaut — aborting chase")
                        return False
                    await asyncio.sleep(0.02)
                    continue

                lost_counter = 0  # reset whenever we see the astronaut

                # --- decide action ---
                offset = best_idx - mid

                if offset < -self.CENTER_TOL:
                    # astronaut is to the left
                    # turn left while still moving forward for a smooth arc
                    action = "tl"
                elif offset > self.CENTER_TOL:
                    # astronaut is to the right
                    action = "tr"
                else:
                    # astronaut is centred — charge straight ahead
                    action = "mf"

                # only send if the action changed — saves a websocket round-trip
                if action != last_action:
                    await self.a_agent.send_message("action", action)
                    last_action = action

                await asyncio.sleep(0.02)  # 50 Hz

        except asyncio.CancelledError:
            print("***** TASK MoveToAstronaut CANCELLED")
            await self.a_agent.send_message("action", "stop")
            return False


class MoveToFlower:
    """
    Steers the astronaut toward a detected flower.
    Returns True once the flower is collected (no longer visible up close),
    or False if the flower disappears from view entirely.

    Adapt the tag string below to match whatever tag your Unity
    flower objects use (e.g. "Flower", "Plant", "CollectibleFlower").
    """
    FLOWER_TAG = "Flower"  # <-- change this to match your Unity tag

    def __init__(self, a_agent):
        self.a_agent = a_agent
        self.rc_sensor = a_agent.rc_sensor

    async def run(self):
        try:
            while True:
                sensor_obj_info = self.rc_sensor.sensor_rays[Sensors.RayCastSensor.OBJECT_INFO]
                sensor_hits = self.rc_sensor.sensor_rays[Sensors.RayCastSensor.HIT]

                n = len(sensor_hits)
                mid = n // 2

                flower_seen = False
                flower_index = None
                flower_dist = None

                for index, value in enumerate(sensor_obj_info):
                    if value and self.FLOWER_TAG in value.get("tag", ""):
                        flower_seen = True
                        flower_index = index
                        flower_dist = value.get("distance", None)
                        break

                if not flower_seen:
                    # Flower disappeared — let the BT decide what to do next
                    await self.a_agent.send_message("action", "nt")
                    return False

                # Close enough to collect? (tune the threshold to your scene)
                if flower_dist is not None and flower_dist < 0.7:
                    await self.a_agent.send_message("action", "stop")
                    print("[Goal:MoveToFlower] Flower reached!")
                    return True

                # Steer toward flower
                if flower_index < mid - 1:
                    await self.a_agent.send_message("action", "tl")
                elif flower_index > mid + 1:
                    await self.a_agent.send_message("action", "tr")
                else:
                    await self.a_agent.send_message("action", "mf")

                await asyncio.sleep(0.1)

        except asyncio.CancelledError:
            print("***** TASK MoveToFlower CANCELLED")
            await self.a_agent.send_message("action", "stop")
            return False
