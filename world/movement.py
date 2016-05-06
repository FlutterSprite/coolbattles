from random import randint
from evennia import utils
import rules

def distance_dec(mover, target):
    "Decreases distance between two characters."
    mover.db.Combat_Range[target] -= 1
    target.db.Combat_Range[mover] -= 1
    # If this brings them range 0 (Engaged):
    if mover.db.Combat_Range[target] <= 0:
        # Reset range to each other to 0 and copy target's ranges to mover.
        target.db.Combat_Range[mover] = 0
        mover.db.Combat_Range = target.db.Combat_Range
        # Copy mover's new range to all others in combat, just in case.
        for fighter in mover.db.Combat_TurnHandler.db.fighters:
            if fighter != mover and fighter != target:
                fighter.db.Combat_Range[mover] = mover.db.Combat_Range[fighter]

def distance_inc(mover, target):
    "Increases distance between two characters."
    mover.db.Combat_Range[target] += 1
    target.db.Combat_Range[mover] += 1
    # Set a cap of the room size:
    if mover.db.Combat_Range[target] > mover.location.db.RoomSize:
        target.db.Combat_Range[mover] = mover.location.db.RoomSize
        mover.db.Combat_Range[target] = mover.location.db.RoomSize
    # Copy mover's new range to all others in combat, just in case.
        for fighter in mover.db.Combat_TurnHandler.db.fighters:
            if fighter != mover and fighter != target:
                fighter.db.Combat_Range[mover] = mover.db.Combat_Range[fighter]

def ms_approach(mover, target, distance, mode):
    # Performs multiple approach steps and spits out the result.
    moves = 0
    blocks = 0
    blockers = []
    steps = distance
    while steps > 0:
        result = approach(mover, target, mode)
        if result[0] == "move":
            moves += 1
        elif result[0] == "block":
            blocks += 1
            if not result[1] in blockers:
                blockers.append(result[1])
        elif result[0] == "stop":
            steps = 0
        steps -= 1
    # Then spit out a pretty message detailing what happened.
    if moves == 1:
        pluralmove = "step"
    else:
        pluralmove = "steps"
    if blocks == 1:
        pluralblock = "step"
    else:
        pluralblock = "steps"
    newrange = mover.db.Combat_Range[target]
    stringofblockers = utils.list_to_string(blockers, endsep="and", addquote=False)
    if mode == "normal":
        if moves > 0 and blocks == 0:
            mover.location.msg_contents("%s approaches to %s range with %s! |552[|554%i|552 %s]|n" % (mover, rules.range_name(newrange).lower(), target, moves, pluralmove))
        elif moves > 0 and blocks > 0:
            mover.location.msg_contents("%s has some movement blocked by %s, but approaches to %s range with %s! |552[|554%i|552 %s, |554%i|552 blocked]|n" % (mover, stringofblockers, rules.range_name(newrange).lower(), target, moves, pluralmove, blocks))
        elif moves == 0 and blocks > 0:
            mover.location.msg_contents("%s tries to approach %s, but is blocked by %s! |552[|554%i|552 %s blocked]|n" % (mover, target, stringofblockers, blocks, pluralblock))
    elif mode == "forced":
        mover.location.msg_contents("%s is pulled in to %s range with %s! |552[Forced |554%i|552 %s]|n" % (mover, rules.range_name(newrange).lower(), target, moves, pluralmove))
    elif mode == "free":
        mover.location.msg_contents("%s approaches to %s range with %s! |552[Free |554%i|552 %s]|n" % (mover, rules.range_name(newrange).lower(), target, moves, pluralmove))

def ms_withdraw(mover, target, distance, mode):
    # Performs multiple withdraw steps and spits out the result.
    moves = 0
    blocks = 0
    blockers = []
    steps = distance
    while steps > 0:
        result = withdraw(mover, target, mode)
        if result[0] == "move":
            moves += 1
        elif result[0] == "block":
            blocks += 1
            if not result[1] in blockers:
                blockers.append(result[1])
        elif result[0] == "stop":
            steps = 0
        steps -= 1
    # Then spit out a pretty message detailing what happened.
    if moves == 1:
        pluralmove = "step"
    else:
        pluralmove = "steps"
    if blocks == 1:
        pluralblock = "step"
    else:
        pluralblock = "steps"
    newrange = mover.db.Combat_Range[target]
    stringofblockers = utils.list_to_string(blockers, endsep="and", addquote=False)
    if mode == "normal":
        if moves > 0 and blocks == 0:
            mover.location.msg_contents("%s withdraws to %s range with %s! |552[|554%i|552 %s]|n" % (mover, rules.range_name(newrange).lower(), target, moves, pluralmove))
        elif moves > 0 and blocks > 0:
            mover.location.msg_contents("%s has some movement blocked by %s, but withdraws to %s range with %s! |552[|554%i|552 %s, |554%i|552 blocked]|n" % (mover, stringofblockers, rules.range_name(newrange).lower(), target, moves, pluralmove, blocks))
        elif moves == 0 and blocks > 0:
            mover.location.msg_contents("%s tries to withdraw from %s, but is blocked by %s! |552[|554%i|552 %s blocked]|n" % (mover, target, stringofblockers, blocks, pluralblock))
    elif mode == "forced":
        mover.location.msg_contents("%s is pushed back to %s range with %s! |552[Forced |554%i|552 %s]|n" % (mover, rules.range_name(newrange).lower(), target, moves, pluralmove))
    elif mode == "free":
        mover.location.msg_contents("%s withdraws to %s range with %s! |552[Free |554%i|552 %s]|n" % (mover, rules.range_name(newrange).lower(), target, moves, pluralmove))

def approach(mover, target, mode):
    "Manages a character's whole approach, including changes in ranges to other characters."
    fighters = mover.db.Combat_TurnHandler.db.fighters
    # Before anything happens, 'stop' when reaching range 0 or when running out of moves.
    if mover.db.Combat_Range[target] == 0 or mover.db.Combat_Moves <= 0:
        if mode == "normal":
            return ["stop"]
    # Then test for other characters blocking movement.
    for character in fighters:
        if character != mover and character != target and mover.db.Combat_Range[character] == 0 and mode == "normal":
            if move_block_test(mover, character):
                mover.db.Combat_Moves -= 1
                return ["block", character]
    # First, move closer to each character closer to the target than you.
    for character in fighters:
        if character != mover and character != target:
            if mover.db.Combat_Range[character] > target.db.Combat_Range[character]:
                distance_dec(mover, character)
    # Then, move further from each character further from you than the target.
    for character in fighters:
        if character != mover and character != target:
            if mover.db.Combat_Range[character] < target.db.Combat_Range[character]:
                distance_inc(mover, character)
    # Lastly, move closer to your target and give the combat message.
    distance_dec(mover, target)
    newrange = mover.db.Combat_Range[target]
    if mode == "normal":
        mover.db.Combat_Moves -= 1
    return ["move"]

def withdraw(mover, target, mode):
    "Manages a character's whole withdrawal, including changes in ranges to other characters."
    fighters = mover.db.Combat_TurnHandler.db.fighters
    # Before anything happens, 'stop' when reaching the room's max range.
    if mover.db.Combat_Range[target] >= mover.location.db.RoomSize:
        return ["stop"]
    # If the movement mode is normal, return 'stop' when running out of moves.
    if mover.db.Combat_Moves <= 0 and mode == "normal":
        return ["stop"]
    # Then, test for other characters blocking movement.
    for character in fighters:
        if character != mover and mover.db.Combat_Range[character] == 0 and mode == "normal":
            if move_block_test(mover, character):
                mover.db.Combat_Moves -= 1
                return ["block", character]
    # Move away from each character closer to the target than you, if they're also closer to you than you are to the target.
    for character in fighters:
        if character != mover and character != target:
            if mover.db.Combat_Range[character] >= target.db.Combat_Range[character] and mover.db.Combat_Range[character] < mover.db.Combat_Range[target]:
                distance_inc(mover, character)
            # Make sure you always move away from other character's your engaged with when you retreat.
            if mover.db.Combat_Range[character] == 0:
                distance_inc(mover, character)
    # Then, move away from your target and give the combat message.
    distance_inc(mover, target)
    newrange = mover.db.Combat_Range[target]
    if mode == "normal":
        mover.db.Combat_Moves -= 1
    return ["move"]

def move_block_test(mover, blocker):
    "If a character tries to move away from someone they're engaged with, the other tries to block them automatically."
    blockstat = max(blocker.db.ATM, blocker.db.DEF)
    moveroll = randint(1, mover.db.MOB)
    # Let the mover go if they're an ally of the blocker.
    if mover in blocker.db.Allies:
        return False
    if blockstat > 0:
        blockroll = randint(1, blockstat)
    else:
        blockroll = 0
    if blockroll >= moveroll:        
        # mover.location.msg_contents("%s keeps %s from moving away! |552[Mobility roll |554%i|552 vs. Blocking roll |554%i|552]|n" % (blocker, mover, moveroll, blockroll))
        return True
    else:
        return False

def init_range(character, fighterlist):
    "Initializes range values."
    rangelist = {}
    for fighter in fighterlist:
        if fighter == character:
            rangelist.update({fighter:0})
        else:
            rangelist.update({fighter:fighter.location.starting_range()})
    character.db.Combat_Range = rangelist
    
def get_engage_group(character):
    "Returns a list of the other characters this character is engaged with, including themself."
    engagegroup = [character]
    for key in character.db.Combat_Range:
        if character.db.Combat_Range[key] == 0 and not character.db.Combat_Range[key] in engagegroup and key != character:
            engagegroup.append(key)
    return engagegroup