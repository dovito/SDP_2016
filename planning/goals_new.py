from constants import *
from globalObjects import me, ally, ball, enemies, ourGoal, opponentGoal
from helperClasses import Point, Goals, BallStatus
from helperFunctions import tan, nearEnough, lineOfSight, isEnemyBox
import sys
import random
sys.path.append(ROOT_DIR+'comms/')
from RobotController import RobotController


controller = RobotController(pitch = PITCH)

# save the amount we're randomly turning between ticks
confusionTarget = 0

# K: What if the vision feed loses the ball or we obscure it after having grabbed it?!
def collectBall():
    """Move towards then grab the ball"""
    me.goal=Goals.collectBall
    
    # if we've caught up to the ball, stop and grab
    if nearEnough(me.bearing(ball), me.currentRotation, near_enough_angle=30) and ball.distance(me)< BALL_OWNERSHIP_DISTANCE:
        controller.stop_robot()
        controller.grab(True)
    # otherwise, go to the ball
    else:
        me.goal = Goals.collectBall
        angle_to_face = me.bearing(ball)
        angle_to_move = angle_to_face
        distance_to_move = me.distance(ball)
        if lineOfSight(me.currentPoint,ball.currentPoint):
            print "Real"
            controller.move(angle_to_face,angle_to_move,distance_to_move,True)
        else:
            ghost_walk(angle_to_face)
            
# K: you can simply only send move and kick(both of the only once), since we prefer the compass' orientation!
def shoot():
    """Kick the ball full power towards the goal"""
    me.goal = Goals.shoot
    angle_to_face = me.bearing(opponentGoal)
    # if we're facing the goal, shoot!
    if nearEnough(angle_to_face, me.currentRotation):
        controller.stop_robot()
        print controller.haveIkicked
        if not controller.haveIkicked:
            controller.kick(255)
    # otherwise, turn to face the goal
    else:
        controller.move(angle_to_face,0,0,False,rotate_in_place=True)

#K: you can simply only send move and kick(both of the only once), since we prefer the compass' orientation!
def passBall():
    """Kick the ball full power towards our ally"""
    me.goal = Goals.passBall
    angle_to_face = me.bearing(ally)
    # if we're facing the ally, pass them the ball
    if nearEnough(angle_to_face, me.currentRotation):
        controller.stop_robot()
        if not controller.haveIkicked:
            controller.kick(255)
    # otherwise, turn to face our ally
    else:
        controller.move(angle_to_face,0,0,False,rotate_in_place=True)

#K: Do we never move?
def receivePass():
    """Face our ally and get ready to grab the ball if they kick it to us"""
    me.goal = Goals.receivePass
    angle_to_face = me.bearing(ally)
    # if we're facing the ally, ungrab and get ready to receive the ball
    if nearEnough(angle_to_face, me.currentRotation):
        controller.stop_robot()
        controller.ungrab(True)
    # otherwise, turn to face our ally
    else:
        controller.move(angle_to_face,0,0,False,rotate_in_place=True)

#K: if we're exactly where we want to be, we can rotate in place instead!#
def blockPass():
    """Move to inbetween the two enemies"""

    me.goal = Goals.blockPass
    # work out where to move to
    e0 = enemies[0].currentPoint
    e1 = enemies[1].currentPoint
    x = (e0.x + e1.x)/2
    y = (e0.y + e1.y)/2
    point_to_be = Point(x, y)

    # work out the parameters for the move command
    angle_to_face = point_to_be.bearing(ball.currentPoint)
    angle_to_move = me.bearing(point_to_be)
    distance = me.distance(point_to_be)
    if not isEnemyBox(point_to_be):
        controller.move(angle_to_move,angle_to_move,distance)
    else:
        ghost_walk(angle_to_face)


def confuseEnemy():
    """Shoogle around a bit to confuse the enemy and hopefully make them move"""
    global confusionTarget
    # if just started this new goal, choose an amount to shoogle
    if me.goal!=Goals.confuse:
        confusionTarget = me.currentRotation + random.uniform(-90,90)
        me.goal = Goals.confuse
    # if we've reached our confusion target, we're done for now
    if nearEnough(confusionTarget, me.currentRotation):
        clearPlan()
    # otherwise, shoogle!
    else:
        controller.move(confusionTarget,0,0,False,rotate_in_place=True)


def guardGoal():
    """Go to the goal line and face the enemy with the ball"""
    me.goal = Goals.guardGoal
    angle_to_face = me.bearing(ball)

    # if not on our goal line, move into the middle of it
    if abs(me.currentPoint.x - ourGoal.x) > 15:
        angle_to_move = me.bearing(ourGoal)
        distance = me.distance(ourGoal)
        controller.move(angle_to_move,angle_to_move,distance)
    # if we're on our goal line, move to block the ball
    else:
        # work out which enemy has the ball
        if ball.status == BallStatus.enemyA:
            enemyNum=0
        elif ball.status == BallStatus.enemyB:
            enemyNum=1
        else:
            print("just guarding lol")
            controller.move(angle_to_face,0,0,False,rotate_in_place=True)
            return

        # calculate where on the y axis the ball would hit if kicked now
        x_dist = enemies[enemyNum].currentPoint.x  - ourGoal.x
        y_dist = x_dist * tan(enemies[enemyNum].currentRotation)
        y_intersection = enemies[enemyNum].currentPoint.y + y_dist

        # calculate where we should therefore go to (we don't want to leave the goal line)
        minY = PITCH_WIDTH/2 - 0.5*GOAL_WIDTH + ROBOT_WIDTH/2
        maxY = PITCH_WIDTH/2 + 0.5*GOAL_WIDTH - ROBOT_WIDTH/2
        point_to_be = Point(ourGoal.x, max(minY, min(maxY, y_intersection)))

        # if we're not where we should be, move there holonomically
        if not nearEnough(point_to_be, me.currentPoint, near_enough_point=10):
            # turn to face the opposite side of the pitch before the holo movement
            if OUR_GOAL=='left':
                angle_to_face=0
            else:
                angle_to_face=180
            # calculate the parameters to send to the robot
            distance = me.distance(point_to_be)
            # we want to move holonomically up and down
            if point_to_be.y<me.currentPoint.y:
                angle_to_move = 90
            else:
                angle_to_move = -90
            controller.move(angle_to_face,angle_to_move,distance)

        # if we're in position already but just facing wrongly, turn to face the robot with the ball
        elif not nearEnough(angle_to_face, me.currentRotation):
            controller.move(angle_to_face,0,0,False,rotate_in_place=True)
        # if we're all set, just wait for something to happen
        else:
            controller.stop_robot()

def ghost_walk(angle_to_face):
    ghost_flag = False
    for i in range(0, 10):
        ghost_pt_x = random.random() * 30 * random.choice([1, -1])
        ghost_pt_y = random.random() * 30 * random.choice([1, -1])
        target = me.currentPoint.x + ghost_pt_y, me.currentPoint.y + ghost_pt_y
        if target[0] > 0 and target[0] < PITCH_LENGTH and target[1] > 0 and target[1] < PITCH_WIDTH and not isEnemyBox(Point(target[0],target[1])) and lineOfSight(me.currentPoint, Point(target[0],target[1])):
            ghost_flag = True
            break;
    if ghost_flag:
        angle_to_move = me.bearing(Point(target[0],target[1]))
        print "Ghost"
        controller.move(angle_to_face, angle_to_move, 60, None, None)
    else:
        print "None"
        controller.stop_robot()

def clearPlan():
    """Reset the robot's goal and plan"""
    me.goal = Goals.none
    controller.stop_robot()
    