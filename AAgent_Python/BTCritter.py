import py_trees as pt
from Sensors import RayCastSensor


############################################
# Helper functions
############################################

def get_astronaut_rays(aagent):

    sensor_obj_info = aagent.rc_sensor.sensor_rays[RayCastSensor.OBJECT_INFO]
    sensor_hits = aagent.rc_sensor.sensor_rays[RayCastSensor.HIT]

    rays = []

    for i, obj in enumerate(sensor_obj_info):

        if obj and "Astronaut" in obj.get("tag", ""):

            dist = obj.get("distance", None)

            rays.append((i, dist))

    return rays


def astronaut_detected(aagent):

    return len(get_astronaut_rays(aagent)) > 0


def best_astronaut_ray(aagent):

    rays = get_astronaut_rays(aagent)

    if not rays:
        return None

    n = len(aagent.rc_sensor.sensor_rays[RayCastSensor.HIT])

    mid = n // 2

    return min(rays, key=lambda x: abs(x[0] - mid))


def astronaut_in_front(aagent, tolerance=1):

    ray = best_astronaut_ray(aagent)

    if ray is None:
        return False

    idx, dist = ray

    n = len(aagent.rc_sensor.sensor_rays[RayCastSensor.HIT])

    mid = n // 2

    return abs(idx - mid) <= tolerance


def astronaut_touched(aagent):

    ray = best_astronaut_ray(aagent)

    if ray is None:
        return False

    idx, dist = ray

    if dist is None:
        return False

    return dist < 0.7


############################################
# Detect astronaut
############################################

class BN_DetectAstronaut(pt.behaviour.Behaviour):

    def __init__(self, aagent):
        self.my_goal = None
        super(BN_DetectAstronaut, self).__init__("BN_DetectAstronaut")
        self.my_agent = aagent

    def initialise(self):
        pass

    def update(self):

        sensor_obj_info = self.my_agent.rc_sensor.sensor_rays[RayCastSensor.OBJECT_INFO]

        for index, value in enumerate(sensor_obj_info):

            if value:

                if "Astronaut" in value.get("tag", ""):

                    print("[BT] Astronaut detected")

                    return pt.common.Status.SUCCESS

        return pt.common.Status.FAILURE

    def terminate(self, new_status: pt.common.Status):
        pass


############################################
# Detect astronaut touch (close enough to stun)
############################################

class BN_AstronautTouched(pt.behaviour.Behaviour):
    """Returns SUCCESS when the critter is close enough to stun the astronaut."""

    def __init__(self, aagent):
        super().__init__("BN_AstronautTouched")
        self.aagent = aagent

    def update(self):
        if astronaut_touched(self.aagent):
            print("[BT] Astronaut touched — stun!")
            return pt.common.Status.SUCCESS
        return pt.common.Status.FAILURE


############################################
# Turn toward astronaut
############################################

class BN_TurnTowardAstronaut(pt.behaviour.Behaviour):

    def __init__(self, aagent):
        super().__init__("TurnTowardAstronaut")
        self.aagent = aagent

    def update(self):

        if not astronaut_detected(self.aagent):
            return pt.common.Status.FAILURE

        ray = best_astronaut_ray(self.aagent)

        if ray is None:
            return pt.common.Status.FAILURE

        idx, dist = ray

        n = len(self.aagent.rc_sensor.sensor_rays[RayCastSensor.HIT])
        mid = n // 2

        # astronaut already centered
        if abs(idx - mid) <= 1:
            self.aagent.pendingActions.append("nt")
            return pt.common.Status.SUCCESS

        # turn toward astronaut
        if idx < mid:
            self.aagent.pendingActions.append("tl")
        else:
            self.aagent.pendingActions.append("tr")

        return pt.common.Status.RUNNING


############################################
# BN_RunGoal — delegates work to an async Goal
############################################

class BN_RunGoal(pt.behaviour.Behaviour):

    def __init__(self, name, aagent, goal_name):

        super().__init__(name)

        self.aagent = aagent

        self.goal_name = goal_name

        self.started = False

    def update(self):

        if not self.started:

            if self.aagent.currentGoal is None:

                self.aagent.currentGoal = self.goal_name

                self.started = True

                return pt.common.Status.RUNNING

        if self.aagent.currentGoal is None:

            self.started = False

            return pt.common.Status.SUCCESS

        return pt.common.Status.RUNNING


############################################
# Behaviour Tree
############################################

class BTCritter():

    def __init__(self, aagent):

        print("[BT] Initializing Critter Behaviour Tree")

        root = pt.composites.Selector("Root", memory=False)


        ####################################
        # STUN — astronaut is close enough: trigger stun then escape
        ####################################

        stun = pt.composites.Sequence("Stun", memory=True)

        stun.add_children([
            BN_AstronautTouched(aagent),
            BN_RunGoal("EscapeAfterStun", aagent, "EscapeSequence"),
        ])


        ####################################
        # ATTACK — astronaut detected: chase using MoveToAstronaut goal
        ####################################

        attack = pt.composites.Sequence("Attack", memory=True)

        attack.add_children([
            BN_DetectAstronaut(aagent),
            # KEY FIX: use BN_RunGoal to hand off to the async MoveToAstronaut goal.
            # This avoids the one-action-per-tick jitter that happened with
            # pendingActions.append() inside BN_GoToAstronaut.
            BN_RunGoal("MoveToAstronaut", aagent, "MoveToAstronaut"),
        ])


        ####################################
        # ROAM
        ####################################

        roaming = pt.composites.Sequence("Roaming", memory=True)

        roaming.add_children([

            BN_RunGoal("TurnRandom", aagent, "Turn"),

            BN_RunGoal("ForwardRandom", aagent, "ForwardStop")

        ])


        # Priority: stun first, then attack/chase, then roam
        root.add_children([
            stun,
            attack,
            roaming,
        ])


        self.behaviour_tree = pt.trees.BehaviourTree(root)


    ####################################
    # UPDATE LOOP
    ####################################

    def update(self):

        self.behaviour_tree.tick()


    async def tick(self):

        self.update()


    def stop_behaviour_tree(self):

        self.behaviour_tree.root.stop()
