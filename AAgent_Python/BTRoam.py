import asyncio
import random
import py_trees
import py_trees as pt
from py_trees import common
import Goals_BT_Basic
import Sensors


class BN_DoNothing(pt.behaviour.Behaviour):
    def __init__(self, aagent):
        self.my_agent = aagent
        self.my_goal = None
        # print("Initializing BN_DoNothing")
        super(BN_DoNothing, self).__init__("BN_DoNothing")

    def initialise(self):
        self.my_goal = asyncio.create_task(Goals_BT_Basic.DoNothing(self.my_agent).run())

    def update(self):
        if not self.my_goal.done():
            return pt.common.Status.RUNNING
        else:
            if self.my_goal.result():
                # print("BN_DoNothing completed with SUCCESS")
                return pt.common.Status.SUCCESS
            else:
                # print("BN_DoNothing completed with FAILURE")
                return pt.common.Status.FAILURE

    def terminate(self, new_status: common.Status):
        # Finishing the behaviour, therefore we have to stop the associated task
        self.my_goal.cancel()


class BN_ForwardRandom(pt.behaviour.Behaviour):
    def __init__(self, aagent):
        self.my_goal = None
        # print("Initializing BN_ForwardRandom")
        super(BN_ForwardRandom, self).__init__("BN_ForwardRandom")
        self.logger.debug("Initializing BN_ForwardRandom")
        self.my_agent = aagent

    def initialise(self):
        self.logger.debug("Create Goals_BT.ForwardDist task")
        self.my_goal = asyncio.create_task(Goals_BT_Basic.ForwardDist(self.my_agent, -1, 1, 5).run())

    def update(self):
        if not self.my_goal.done():
            return pt.common.Status.RUNNING
        else:
            if self.my_goal.result():
                self.logger.debug("BN_ForwardRandom completed with SUCCESS")
                # print("BN_ForwardRandom completed with SUCCESS")
                return pt.common.Status.SUCCESS
            else:
                self.logger.debug("BN_ForwardRandom completed with FAILURE")
                # print("BN_ForwardRandom completed with FAILURE")
                return pt.common.Status.FAILURE

    def terminate(self, new_status: common.Status):
        # Finishing the behaviour, therefore we have to stop the associated task
        self.logger.debug("Terminate BN_ForwardRandom")
        self.my_goal.cancel()


class BN_TurnRandom(pt.behaviour.Behaviour):
    def __init__(self, aagent):
        self.my_goal = None
        # print("Initializing BN_TurnRandom")
        super(BN_TurnRandom, self).__init__("BN_TurnRandom")
        self.my_agent = aagent

    def initialise(self):
        self.my_goal = asyncio.create_task(Goals_BT_Basic.Turn(self.my_agent).run())

    def update(self):
        if not self.my_goal.done():
            return pt.common.Status.RUNNING
        else:
            res = self.my_goal.result()
            if res:
                # print("BN_Turn completed with SUCCESS")
                return pt.common.Status.SUCCESS
            else:
                # print("BN_Turn completed with FAILURE")
                return pt.common.Status.FAILURE

    def terminate(self, new_status: common.Status):
        # Finishing the behaviour, therefore we have to stop the associated task
        self.logger.debug("Terminate BN_TurnRandom")
        self.my_goal.cancel()


class BN_DetectFlower(pt.behaviour.Behaviour):
    def __init__(self, aagent):
        self.my_goal = None
        super(BN_DetectFlower, self).__init__("BN_DetectFlower")
        self.my_agent = aagent

    def initialise(self):
        pass

    def update(self):
        sensor_obj_info = self.my_agent.rc_sensor.sensor_rays[Sensors.RayCastSensor.OBJECT_INFO]
        for index, value in enumerate(sensor_obj_info):
            if value:  # there is a hit with an object
                if value["tag"] == "AlienFlower":  # If it is a flower
                    return pt.common.Status.SUCCESS

        return pt.common.Status.FAILURE

    def terminate(self, new_status: common.Status):
        pass



# will start with the condition nodes 
class BN_IsFrozen(pt.behaviour.Behaviour):
    def __init__(self, aagent):
        super(BN_IsFrozen, self).__init__("BN_IsFrozen")
        self.my_agent = aagent

    def initialise(self):
        pass # there's nothing to initializa as there is no async tasks

    def update(self):
        if self.my_agent.i_state.isFrozen:
            return pt.common.Status.SUCCESS #if agent is frozen then condition is satistfied 
        else:
            return pt.common.Status.FAILURE # if agent is not frozen condition fails
    
    def terminate(self, new_status: common.Status):
        pass   # theres nothing to clean up


class BN_IsInventoryFull(pt.behaviour.Behaviour):
    def __init__(self, aagent):
        super(BN_IsInventoryFull, self).__init__("BN_IsInventoryFull")
        self.my_agent= aagent
    
    def initialise(self):
        pass  #it is a condition node so we check state from update and there is nothing to prepare in initialize
    def update(self):
        for item in self.my_agent.i_state.myInventoryList:
            if (item["name"] == "AlienFlower" and item["amount"]>=2):
                return pt.common.Status.SUCCESS
        return pt.common.Status.FAILURE
    
    def terminate(self, new_status: common.Status):
        pass

class BN_IsFlowerVisible (pt.behaviour.Behaviour): # it is a condition node where we check if any ray hits a flower - no async needed
    def __init__(self, aagent):
        super(BN_IsFlowerVisible, self).__init__("BN_IsFlowerVisible")
        self.my_agent= aagent
    def initialise(self):
        pass
    def update(self):
        sensor_obj_info = self.my_agent.rc_sensor.sensor_rays[Sensors.RayCastSensor.OBJECT_INFO]
        for value in sensor_obj_info:
            if value and value["tag"] == "AlienFlower":
                return pt.common.Status.SUCCESS
        return pt.common.Status.FAILURE
    def terminate(self, new_status: common.Status):
        pass

# now let's move on to the action nodes 

#go to base 
# action node where the aqstranuat walks to basealpha
# we wrap gotobase in goals_bt_basic 
class BN_GoToBase(pt.behaviour.Behaviour):
    def __init__(self, aagent):
        self.my_goal= None
        super(BN_GoToBase, self).__init__("BN_GoToBase")
        self.my_agent= aagent

    def initialise(self):
        self.my_goal= asyncio.create_task(
            Goals_BT_Basic.GoToBase(self.my_agent).run())
    
    def update(self): # return running while the agent is still walking and success whenever the agent arrives 
        if not self.my_goal.done():
            return pt.common.Status.RUNNING
        else: 
            if self.my_goal.result():
                return pt.common.Status.SUCCESS
            else:
                return pt.common.Status.FAILURE
    
    def terminate(self, new_status: common.Status):
        self.my_goal.cancel()


# unload 
#action node where the agent unloads the flowers at te base
# wrap unnload in goals_bt_basic 
class BN_Unload(pt.behaviour.Behaviour):
    def __init__(self, aagent):
        self.my_goal= None
        super(BN_Unload, self).__init__("BN_Unload")
        self.my_agent= aagent

    def initialise(self):
        self.my_goal= asyncio.create_task(
            Goals_BT_Basic.Unload(self.my_agent).run()
        )

    def update(self):
        if not self.my_goal.done():
            return pt.common.Status.RUNNING
        else:
            try: # we added an exception in case the async task crashes then BT won't crash but return failure
                if self.my_goal.result():
                    return pt.common.Status.SUCCESS
                else:
                    return pt.common.Status.FAILURE
            except Exception:
                return pt.common.Status.FAILURE

    def terminate(self, new_status:common.Status):
        self.my_goal.cancel()

# move to flower 
# action node where turnd towards the nearest flower and walks to it 
# will wrap movetoflower in goalsbtbasics

class BN_MoveToFlower(pt.behaviour.Behaviour):
    def __init__(self, aagent):
        self.my_goal = None
        super(BN_MoveToFlower, self).__init__("BN_MoveToFlower")
        self.my_agent = aagent
    
    def initialise(self):
        self.my_goal = asyncio.create_task(
            Goals_BT_Basic.MoveToFlower(self.my_agent).run()
        )

    def update(self):
        if not self.my_goal.done():
            return pt.common.Status.RUNNING
        else:
            try:
                if self.my_goal.result():
                    return pt.common.Status.SUCCESS
                else:
                    return pt.common.Status.FAILURE
            except Exception:
                return pt.common.Status.FAILURE
            
    def terminate(self, new_status: common.Status):
        self.my_goal.cancel()


class BN_Wander(pt.behaviour.Behaviour):
    def __init__(self, aagent):
        self.my_goal = None
        super(BN_Wander, self).__init__("BN_Wander")
        self.my_agent = aagent

    def initialise(self):
        self.my_goal = asyncio.create_task(
            Goals_BT_Basic.Wander(self.my_agent).run()
        )

    def update(self):
        if not self.my_goal.done():
            return pt.common.Status.RUNNING
        else:
            try:
                if self.my_goal.result():
                    return pt.common.Status.SUCCESS
                else:
                    return pt.common.Status.FAILURE
            except Exception:
                return pt.common.Status.FAILURE

    def terminate(self, new_status: common.Status):
        if self.my_goal is not None:
            self.my_goal.cancel()
class BN_IsCritterVisible(pt.behaviour.Behaviour):
    def __init__(self, aagent):
        super(BN_IsCritterVisible, self).__init__("BN_IsCritterVisible")
        self.my_agent = aagent

    def initialise(self):
        pass

    def update(self):
        sensor_obj_info = self.my_agent.rc_sensor.sensor_rays[Sensors.RayCastSensor.OBJECT_INFO]
        for value in sensor_obj_info:
            if value and value.get("tag") == "CritterMantaRay":
                return pt.common.Status.SUCCESS
        return pt.common.Status.FAILURE

    def terminate(self, new_status: common.Status):
        pass


class BN_EvadeCritter(pt.behaviour.Behaviour):
    def __init__(self, aagent):
        self.my_goal = None
        super(BN_EvadeCritter, self).__init__("BN_EvadeCritter")
        self.my_agent = aagent

    def initialise(self):
        self.my_goal = asyncio.create_task(
            Goals_BT_Basic.EvadeCritter(self.my_agent).run()
        )

    def update(self):
        if not self.my_goal.done():
            return pt.common.Status.RUNNING
        else:
            try:
                if self.my_goal.result():
                    return pt.common.Status.SUCCESS
                else:
                    return pt.common.Status.FAILURE
            except Exception:
                return pt.common.Status.FAILURE

    def terminate(self, new_status: common.Status):
        if self.my_goal is not None:
            self.my_goal.cancel()

# here is the main bt
# it has the structure of a root selector and then multiple sequences each addressing a different case
class BTRoam:
    def __init__(self, aagent):
        self.aagent = aagent
        
        #frozen branch sequece 
        frozen= pt.composites.Sequence(name= "Frozen_seq", memory= False)
        frozen.add_children([
                BN_IsFrozen(aagent),
                BN_DoNothing(aagent)
            ]
        )
        
        # unload branch seq (if full , walk to base  then unload)
        unload= pt.composites.Sequence(name="Unload_seq", memory= False)
        unload.add_children([
            BN_IsInventoryFull(aagent),
            BN_GoToBase(aagent),
            BN_Unload(aagent)
        ])

        #collect branch if flower visible, move towards it
        collect= pt.composites.Sequence(name= "Collect_seq", memory=False)
        collect.add_children([
            BN_IsFlowerVisible(aagent),
            BN_MoveToFlower(aagent)
        ])

        wander = BN_Wander(aagent)

        avoid_critter = pt.composites.Sequence(name="AvoidCritter_seq", memory=False)
        avoid_critter.add_children([
            BN_IsCritterVisible(aagent),
            BN_EvadeCritter(aagent)
        ])

        #root selector
        self.root = pt.composites.Selector(name="Root_sel", memory=False)
        self.root.add_children([
            frozen,
            avoid_critter,
            unload,
            collect,
            wander
        ])


        self.behaviour_tree = pt.trees.BehaviourTree(self.root)

    def stop_behaviour_tree(self):
        print("Stopping the BehaviorTree")
        self.root.tick_once()
        for node in self.root.iterate():
            if node.status != pt.common.Status.INVALID:
                node.status = pt.common.Status.INVALID
                # For nodes that weren't RUNNING, manually call terminate
                if hasattr(node, "terminate"):
                    node.terminate(pt.common.Status.INVALID)

    async def tick(self):
        self.behaviour_tree.tick()
        await asyncio.sleep(0)