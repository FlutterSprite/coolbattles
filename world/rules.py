from random import randint
from evennia import utils
import math

def roll_atk(character, attack_type, effects):
    "Makes an attack roll based on a character's ATM or ATR stat."
    if attack_type == "melee":
        attack = character.db.ATM
    else:
        attack = character.db.ATR
    if attack == 0:
        return 0
    else:
        attack_roll = randint(1, attack)
        # If there is a precise attack effect, set roll to 6.
        if 'Precise Attack' in effects:
            attack_roll = 6
        # If there is a perfect attack effect, set roll to 10.
        if 'Perfect Attack' in effects:
            attack_roll = 10
        # If there is a boosted attack effect, increase the roll by 2.
        if 'Boosted Attack' in effects:
            attack_roll += 2
        # If attacker has the 'Debuffed ATK' condition, reduce the roll by 1.
        if 'Debuffed ATK' in character.db.Combat_Conditions:
            attack_roll -= 1
        # If attacker has the 'Buffed ATK' condition, increase the roll by 1.
        if 'Buffed ATK' in character.db.Combat_Conditions:
            attack_roll += 1
        return attack_roll

def roll_def(character, def_effects, effects):
    "Makes a defense roll based on a character's DEF stat."
    defense = character.db.DEF
    if defense == 0:
        return 0
    else:
        defense_roll = randint(1, defense)
        # If there's a precise defense effect, set defense roll to 6.
        if 'Precise Defense' in def_effects:
            defense_roll = 6
        # If there's a precise defense effect, set defense roll to 10.
        if 'Perfect Defense' in def_effects:
            defense_roll = 10
        # If there's a boosted defense effect, add 2 to the defense roll.
        if 'Boosted Defense' in def_effects:
            defense_roll += 2
        # If defender has the 'Debuffed DEF' condition, reduce defense roll by 1.
        if 'Debuffed DEF' in character.db.Combat_Conditions:
            defense_roll -= 1
        # If defender has the 'Buffed DEF' condition, increase defense roll by 1.
        if 'Buffed DEF' in character.db.Combat_Conditions:
            defense_roll += 1
        # If there's a bypass defense effect, halve the defense roll.
        if 'Bypass Defense' in effects:
            defense_roll /= 2
        return defense_roll

def roll_init(character):
    "Rolls Mobility to determine initiative."
    mobility = character.db.MOB
    if mobility == 0:
        return 0
    else:
        # I multiply the stat by a super high number here to reduce the chance of ties.
        # Ties are sorted arbitrarily - I have no idea how - but they should be rare.
        return randint(1, mobility * 1000)

def damage_target(target, damage):
    "Subtracts HP from a target, to a minimum of 0"
    if damage >= target.db.HP:
        target.db.HP = 0
        target.location.msg_contents("%s is defeated!" % target)
    else:
        target.db.HP -= damage

def queue_attack(character, target, attack_message, effects, attack_type):
    "Queues an attack against a target, who can choose how to defend"
    target = character.search(target)
    # Check for existing pre-set attack messages
    if attack_message == "default" and attack_type == "melee":
        if len(character.db.Melee_Messages) == 0:
            attack_message = ("<self> attacks <target>!")
        else:
            attack_message = character.db.Melee_Messages[randint(0, len(character.db.Melee_Messages)-1)]
    if attack_message == "default" and attack_type == "ranged":
        if len(character.db.Range_Messages) == 0:
            attack_message = ("<self> attacks <target>!")
        else:
            attack_message = character.db.Range_Messages[randint(0, len(character.db.Range_Messages)-1)]
    # Append "<self>" to the beginning if it's not included, then replace <self> and <target> with names.
    if not "<self>" in attack_message:
        attack_message = str(character) + " " + attack_message
    attack_message = attack_message.replace("<self>", str(character))
    attack_message = attack_message.replace("<target>", str(target))
    # Get the attack roll. Special move effects affecting the attack roll are processed there.
    attack = roll_atk(character, attack_type, effects)
    # The attack is stored on the target as a tuple.
    target.db.Combat_IncomingAttack = (attack, character, effects, attack_type)
    # Give the compiled attack message to the room.
    if attack_type == "melee":
        output = ("%s |522[Melee attack roll vs. %s: |544%i|522]|n" % (attack_message, target, attack))
    else:
        output = ("%s |525[Ranged attack roll vs. %s: |545%i|525]|n" % (attack_message, target, attack))
    if effects:
        effectstring = utils.list_to_string(effects, endsep="|255and|455", addquote=False)
        output += " |255[|455%s|255]|n" % effectstring
    character.location.msg_contents(output)
    # Puts a script on the target that will time them out and auto-defend if they don't respond to the attack quick enough.
    target.scripts.add("scripts.DefenseTimeout")
    # If there's a double attack effect, give the attacker a second attack.
    if 'Double Attack' in effects:
        effectlist = []
        for effect in effects:
            if effect != 'Double Attack':
                effectlist.append(effect)
        character.db.Combat_Second = (attack_type, effectlist)
        character.msg("|255Use the '|455second|255' command to use your second attack!")

def defend_queue(character, action, def_effects):
    "Attempts a defense roll against a queued attack."
    if not character.db.Combat_IncomingAttack:
        character.msg("|413There are no attacks aimed at you!")
        return
        
    # Retrieve all the information from the incoming attack.
    attack = character.db.Combat_IncomingAttack[0]
    offender = character.db.Combat_IncomingAttack[1]
    effects = character.db.Combat_IncomingAttack[2]
    attack_type = character.db.Combat_IncomingAttack[3]
    
    if action == "defend":
        # Make a defense roll. Effects that affect the roll are processed in the roll_def function.
        defense = roll_def(character, def_effects, effects)
        rollmessage = "|225[Defense roll: |445%i|225]|n" % defense
    else:
        defense = 0
        rollmessage = "|225[Endure]|n"
    if defense >= attack:
        # If the defense roll is equal or higher to the attack roll, there's no damage.
        character.location.msg_contents("%s defends against %s's attack! %s" % (character, offender, rollmessage))
        # If there's an absorb effect and DEF roll is higher than ATK roll, recover HP equal to difference.
        if 'Absorb' in def_effects and defense > attack:
            recover_hp(character, min(attack, defense - attack))
        # If there's a reflect effect, send an identical attack back at the target.
        if 'Reflect' in def_effects:
            # Instead of using the queue_attack function, just set everything manually to use the same attack roll and effects.
            output = ("%s reflects the attack back at %s! |522[Attack roll vs. %s: |544%i|522]|n" % (character, offender, offender, attack))
            if effects:
                effectstring = utils.list_to_string(effects, endsep="and", addquote=False)
                output += " |255[|455%s|255]|n" % effectstring
            character.location.msg_contents(output)
            offender.db.Combat_IncomingAttack = (attack, character, effects, attack_type)
            offender.scripts.add("scripts.DefenseTimeout")
        # If there's a counterattack effect, attack the target with a regular attack.
        if 'Counterattack' in def_effects:
            countermessage = "<self> counterattacks <target>!"
            counterattack_type = "ranged"
            if character.db.Combat_Range[character.db.Combat_IncomingAttack[1]] == 0:
                counterattack_type = "melee"
            queue_attack(character, offender, "<self> counterattacks <target>!", [], counterattack_type)
        # Get rid of the incoming attack at the end.
        del character.db.Combat_IncomingAttack
    else:
        # Otherwise, the difference is given as damage.
        damage = attack - defense
        # First things first - the defensive effect 'Negate Effects' will strip out all effects from the attack.
        if 'Negate Effects' in def_effects:
            effects = []
        # If there's a double damage effect, multiply damage by 2.
        if 'Double Damage' in effects:
            damage = damage * 2
        if 'Risky Defense' in def_effects:
            damage = damage * 2
        # If there's a half damage effect, divide damage by 2 (minimum 1).
        if 'Half Damage' in effects:
            damage = max(1, damage/2)
        if 'Halve Damage' in def_effects:
            damage = max(1, damage/2)
        # If there's a no damage or negate damage effect, set damage to 0.
        if 'No Damage' in effects or 'Negate Damage' in def_effects:
            damage = 0
        character.location.msg_contents("%s takes |555%i damage|n from %s's attack! %s" % (character, damage, offender, rollmessage))
        damage_target(character, damage)
        # If there's a recoil effect, give half damage back to the attacker.
        if 'Recoil' in effects:
            reduce_hp(offender, max(1, damage/2))
        # If there's a leech effect, heal the attacker equal to the damage.
        if 'Leech' in effects:
            recover_hp(offender, damage)
        # Pass the rest of the effects onto 'special_hinder' instead of defining them all twice.
        special_hinder(character, offender, effects)
        del character.db.Combat_IncomingAttack

def recover(character):
    "Heals a character to full HP and SP."
    character.db.HP = max(1, (character.db.VIT * 3))
    character.db.SP = character.db.SPE * 2
    character.msg("|252HP and SP restored!|n")

def start_turn(character):
    "Makes actions available to a character at the start of their turn."
    # Give the character their action and movement for the round.
    character.db.Combat_Actions = 1
    character.db.Combat_Moves = int(math.floor(character.db.MOB / 2))
    # Clear out special-related stuff.
    if character.db.Combat_UsedSpecial:
        character.db.Combat_UsedSpecial = False
    if character.db.Combat_Second:
        del character.db.Combat_Second
    # Check status effects and conditions here.
    for status in character.db.Combat_Conditions:
        if status == 'Debuffed ATK':
            character.msg("Your attack rolls are reduced by 1. |255[|455Debuffed ATK|255]|n")
        if status == 'Debuffed DEF':
            character.msg("Your defense rolls are reduced by 1. |255[|455Debuffed DEF|255]|n")
        if status == 'Debuffed RNG':
            character.msg("Your range is reduced by 2. |255[|455Debuffed RNG|255]|n")
        if status == 'Debuffed MOB':
            character.db.Combat_Moves -= 1
            character.msg("You have 1 less move available this turn. |255[|455Debuffed MOB|255]|n")
        if status == 'Immobilization':
            character.db.Combat_Moves = 0
            character.msg("You can't move this turn. |255[|455Immobilization|255]|n")
        if status == 'Disabled Action':
            character.db.Combat_Actions = 0
            character.msg("You can't take an action this turn. |255[|455Disabled Action|255]|n")
        if status == 'Buffed ATK':
            character.msg("Your attack rolls are increased by 1. |255[|455Buffed ATK|255]|n")
        if status == 'Buffed DEF':
            character.msg("Your defense rolls are increased by 1. |255[|455Buffed DEF|255]|n")
        if status == 'Buffed MOB':
            character.db.Combat_Moves += 1
            character.msg("You have 1 more move available this turn. |255[|455Buffed MOB|255]|n")
    

def pass_turn(character):
    "Pass on a turn. Can be initiated by command, timeout, or having no actions available."
    character.db.Combat_Actions = 0
    character.db.Combat_Moves = 0
    if character.db.Combat_Second:
        del character.db.Combat_Second

def combat_cleanup(character):
    "Cleans up all the combat-related attributes on a character."
    # Goes through every attribute - if it starts with "combat_", delete it.
    for attr in character.attributes.all():
        if attr.key[:7] == "combat_":
            character.attributes.remove(key=attr.key)
        
def turn_prompt(character):
    "Gives a player combat information when their turn comes up."
    turn_handler = character.db.Combat_TurnHandler
    fighterlist = turn_handler.db.fighters
    promptline = '{:-^88}'.format(" |540It's your turn!|530 ")
    character.msg("|530%s|n" % promptline)
    for fighter in fighterlist:
        character.msg(combat_status_line(fighter, character))
    character.msg("|530--------------------------------------------------------------------------------|n")
    

def is_fighter(character):
    "Determines whether the given object is a fighter (has stats, etc.)"
    for stat in ("ATM", "DEF", "VIT", "MOB", "ATR", "SPE"):
        if character.attributes.has(stat):
            return True
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
            mover.location.msg_contents("%s approaches to %s range with %s! |552[|554%i|552 %s]|n" % (mover, range_name(newrange).lower(), target, moves, pluralmove))
        elif moves > 0 and blocks > 0:
            mover.location.msg_contents("%s has some movement blocked by %s, but approaches to %s range with %s! |552[|554%i|552 %s, |554%i|552 blocked]|n" % (mover, stringofblockers, range_name(newrange).lower(), target, moves, pluralmove, blocks))
        elif moves == 0 and blocks > 0:
            mover.location.msg_contents("%s tries to approach %s, but is blocked by %s! |552[|554%i|552 %s blocked]|n" % (mover, target, stringofblockers, blocks, pluralblock))
    elif mode == "forced":
        mover.location.msg_contents("%s is pulled in to %s range with %s! |552[Forced |554%i|552 %s]|n" % (mover, range_name(newrange).lower(), target, moves, pluralmove))
    elif mode == "free":
        mover.location.msg_contents("%s approaches to %s range with %s! |552[Free |554%i|552 %s]|n" % (mover, range_name(newrange).lower(), target, moves, pluralmove))

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
            mover.location.msg_contents("%s withdraws to %s range with %s! |552[|554%i|552 %s]|n" % (mover, range_name(newrange).lower(), target, moves, pluralmove))
        elif moves > 0 and blocks > 0:
            mover.location.msg_contents("%s has some movement blocked by %s, but withdraws to %s range with %s! |552[|554%i|552 %s, |554%i|552 blocked]|n" % (mover, stringofblockers, range_name(newrange).lower(), target, moves, pluralmove, blocks))
        elif moves == 0 and blocks > 0:
            mover.location.msg_contents("%s tries to withdraw from %s, but is blocked by %s! |552[|554%i|552 %s blocked]|n" % (mover, target, stringofblockers, blocks, pluralblock))
    elif mode == "forced":
        mover.location.msg_contents("%s is pushed back to %s range with %s! |552[Forced |554%i|552 %s]|n" % (mover, range_name(newrange).lower(), target, moves, pluralmove))
    elif mode == "free":
        mover.location.msg_contents("%s withdraws to %s range with %s! |552[Free |554%i|552 %s]|n" % (mover, range_name(newrange).lower(), target, moves, pluralmove))

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

def recover_hp(character, amount):
    "Recovers HP as part of a special move."
    character.db.HP += amount
    if character.db.HP > (max(character.db.VIT * 3, 1)):
        character.db.HP = max(character.db.VIT * 3, 1)
    character.location.msg_contents("%s recovers from some damage! |252[|454+%i|252 HP]" % (character, amount))
    
def recover_sp(character, amount):
    "Recovers HP as part of a special move."
    character.db.SP += amount
    if character.db.SP > character.db.SPE * 2:
        character.db.SP = character.db.SPE * 2
    character.location.msg_contents("%s recovers some SP! |255[|455+%i|255 SP]" % (character, amount))

def reduce_hp(character, amount):
    "Reduces HP as part of a special move or harmful condition."
    character.location.msg_contents("%s takes damage! |252[|454-%i|252 HP]" % (character, amount))
    damage_target(character, amount)

def range_name(value):
    "Converts a range value to a name."
    rangedict = {0:"Engaged", 1:"Very Close", 2:"Close", 3:"Medium-Close", 4:"Medium", 5:"Medium-Far", 6:"Far", 7:"Very Far", 8:"Distant", 9:"Very Distant", 10:"Remote"}
    if value not in rangedict:
        return "Remote"
    return rangedict[value]

def size_name(value):
    "Converts a room size value to a name."
    sizedict = {0:"Claustrophobic", 1:"Cramped", 2:"Tiny", 3:"Small", 4:"Small", 5:"Moderate", 6:"Moderate", 7:"Large", 8:"Large", 9:"Huge", 10:"Expansive"}
    if value not in sizedict:
        return "Expansive"
    return sizedict[value]

def get_engage_group(character):
    "Returns a list of the other characters this character is engaged with, including themself."
    engagegroup = [character]
    for key in character.db.Combat_Range:
        if character.db.Combat_Range[key] == 0 and not character.db.Combat_Range[key] in engagegroup and key != character:
            engagegroup.append(key)
    return engagegroup
    
def is_turn(character):
    "Checks to see if it's a character's turn."
    turnhandler = character.db.Combat_TurnHandler
    currentchar = turnhandler.db.fighters[turnhandler.db.turn]
    if character == currentchar:
        return True
    return False
    
def attack_type_check(character, target, attack_type, effects):
    "Checks to see if the target can make a melee or ranged attack."
    target = character.search(target)
    if attack_type == "melee":
        # If the character has ATM 0 and no special effects that grant them a roll, they can't make melee attacks.
        if character.db.ATM == 0 and 'Boosted Attack' not in effects and 'Perfect Attack' not in effects and 'Precise Attack' not in effects:
            return "|413You can't make melee attacks!|n"
        # If the target is more than 0 spaces away, and they don't have an effect that closes the distance, they can't make the attack.
        if character.db.Combat_Range[target] > 0 and 'Lunge' not in effects and 'Projected Strike' not in effects:
            return "|413You can only use melee attacks on engaged (range 0) targets!|n"
        if character.db.Combat_Range[target] > 2 and 'Lunge' in effects:
            return "|413Your target is more than 2 spaces away - can't lunge!|n"
        return False
    if attack_type == "ranged":
        # If the character has ATR 0 and no special effects that grant them a roll, they can't make ranged attacks.
        if character.db.ATR == 0 and 'Boosted Attack' not in effects and 'Perfect Attack' not in effects and 'Precise Attack' not in effects:
            return "|413You can't make ranged attacks!|n"
        # If the target is at range 0 and there's no effect that lets the character hit melee targets with ranged attacks, they can't attack.
        if character.db.Combat_Range[target] == 0 and 'Point-Blank' not in effects:
            return "|423You can't use ranged attacks on engaged (range 0) targets!|n"
        # If there are other fighters engaged with the character who don't consider the character an ally, no ranged attacks.
        for fighter in character.db.Combat_Range:
            if character.db.Combat_Range[fighter] == 0 and fighter != character and 'Point-Blank' not in effects and character not in fighter.db.Allies:
                return "|423You can't use ranged attacks when there are enemies engaged (range 0) with you!|n"
        return False

def cmd_check(caller, args, action, conditions):
    "A function that can be called to test a variety of conditions in combat before executing a command. Returns false if everything checks out."
    # Split the arguments into a list.
    arglist = args.split(None)
    nargs = len(arglist)
    if 'InCombat' in conditions:
        if not caller.db.Combat_TurnHandler:
            return ("|413You can only do that if you're in a fight!|n")
    if 'HasHP' in conditions:
        if not caller.db.HP:
            return ("|413You can't %s, you've been defeated!|n" % action)
    if 'IsTurn' in conditions:
        if not is_turn(caller):
            return ("|413You can't %s when it's not your turn!|n" % action)
    if 'HasAction' in conditions:
        if not caller.db.Combat_Actions:
            return ("|413You've already used your action this turn!|n")
    if 'HasMove' in conditions or 'HasMoves' in conditions: # Check for both 'HasMove' and 'HasMoves' in case I screw up
        if not caller.db.Combat_Moves:
            return ("|413You've already used all your movement this turn!|n")
    if 'AttacksResolved' in conditions:
        for fighter in caller.db.Combat_TurnHandler.db.fighters:
            if fighter.db.Combat_IncomingAttack:
                return ("|413Please wait for outstanding attacks to resolve!|n")
    # Conditions requiring a target start here.
    if 'NeedsTarget' in conditions:
        if not arglist:
            return ("|413You need to specify a target!|n")
        if caller.search(arglist[0], quiet=True):
            target = caller.search(arglist[0], quiet=True)[0]
        else:
            target = False
        if not target:
            return ("|413That is not a valid target!|n")
        if not is_fighter(target):
            return ("|413That is not a valid target!|n")
        if 'TargetNotSelf' in conditions:
            if target == caller:
                if action == "withdraw":
                    action = "withdraw from"
                return ("|413You can't %s yourself!|n" % action)
        if 'TargetInFight' in conditions:
            if not target.db.Combat_TurnHandler:
                return ("|413%s isn't in the fight!|n" % target)
        if 'TargetNotEngaged' in conditions:
            if caller.db.Combat_Range[target] == 0:
                return ("|413%s is too close to you for you to do that!|n" % target)
        if 'TargetHasHP' in conditions:
            if target.db.HP <= 0:
                return ("|413%s has already been defeated!|n" % target)
    return False
        
def health_bar(value, maximum, length):
    "Returns a health bar of given length. Fancy!"
    gradientlist = ["|[300", "|[300", "|[310", "|[320", "|[330", "|[230", "|[130", "|[030", "|[030"]
    # First, we convert the values to floats so we can do fine division on them.
    value = float(value)
    maximum = float(maximum)
    length = float(length)
    # And let's make sure the value isn't larger than the maximum so we don't get errors.
    value = min(value, maximum)
    # Then, let's pick a bar color from the gradient list!
    barcolor = gradientlist[max(0,(int(round((value / maximum) * 9)) - 1))]
    # Next, we divide the value by the maximum and multiply that by the length.
    # The result is converted to an integer - the index of where we'll put the color code ending the health bar.
    rounded_percent = int(min(round((value / maximum) * length), length - 1))
    # Now, we create our base health bar string. This string is going to be padded to the length given.
    barstring = (("{:<%i}" % int(length)).format("HP: %i / %i" % (int(value), int(maximum))))
    # Lastly, we insert the color codes into the index calculated earlier to finish our health bar.
    barstring = ("|555" + barcolor + barstring[:rounded_percent] + '|[011' + barstring[rounded_percent:])
    # For some reason, sometimes the health bar is one character too long, so I fixed it here. Whatever.
    return barstring[:int(length) + 13] + "|n"

def combat_status_line(fighter, caller):
    "Prints out a one-line readout with a character's name, health bar, and range to the caller."
    hbar = health_bar(fighter.db.HP, max(fighter.db.VIT * 3, 1), 20)
    pluralstep = "steps"
    if caller.db.Combat_Range[fighter] == 1:
        pluralstep = "step"
    spreadout = ("|255SP: |455%i|255/|455%i|n" % (fighter.db.SP, (fighter.db.SPE * 2)))
    rangereadout = ("- |525%s (|545%i|525 %s)" % (range_name(caller.db.Combat_Range[fighter]), caller.db.Combat_Range[fighter], pluralstep))
    # Let's color the range readout red if they're engaged.
    if caller.db.Combat_Range[fighter] == 0:
        rangereadout = ("- |522%s (|544%i|522 %s)" % (range_name(caller.db.Combat_Range[fighter]), caller.db.Combat_Range[fighter], pluralstep))
    beforeformat_name = str(fighter)
    if fighter == caller:
        beforeformat_name = "> " + str(fighter)
        rangereadout = ""
    name = "{:>20}".format(beforeformat_name + ":")
    return (name + " " + hbar + " " + spreadout + " " + rangereadout)

def special_cost(effects):
    "Returns the cost of a special move based on its effects."
    cost = 0
    special_info = special_dictionary()
    # Fetch each effect's cost from the special dictionary and add them together.
    for effect in effects:
        if effect in special_info:
            cost += special_info[effect][0]
    if cost < 0:
        cost = 0
    return cost

def special_support(target, user, effects):
    "Performs special support effects."
    # If there's a Heal effect, recover random target's VIT in HP.
    if "Heal" in effects:
        recover_hp(target, target.db.VIT)
    # If there's a Heal effect, recover 3 SP.
    if "SP Recover" in effects:
        recover_sp(target, 3)
    # If there's a Super Dash effect, gain a dash's worth of movement +2.
    if "Super Dash" in effects:
        # But not if you're immobilized.
        if 'Immobilization' in target.db.Combat_Conditions:
            target.msg("You're immobilized! You can't move!")
            return
        target.db.Combat_Moves += int(math.ceil(float(target.db.MOB) / 2) + 2)
        target.location.msg_contents("%s gains a huge burst of movement! |552[|554+%i|552 Movement]|n" % (target, int(math.ceil(float(target.db.MOB) / 2) + 2)))
    # If there's a Grant Buffed ATK effect, give the Buffed ATK condition to the target for 3 turns.
    if 'Grant Buffed ATK' in effects:
        add_condition(target, user, 'Buffed ATK', 3 + 1)
    # If there's a Grant Buffed DEF effect, give the Buffed DEF condition to the target for 3 turns.
    if 'Grant Buffed DEF' in effects:
        add_condition(target, user, 'Buffed DEF', 3 + 1)
    # If there's a Grant Buffed MOB effect, give the Buffed MOB condition to the target for 3 turns.
    if 'Grant Buffed MOB' in effects:
        add_condition(target, user, 'Buffed MOB', 3 + 1)

def special_hinder(target, user, effects):
    "Performs special hinder effects."
    # If there's an inflict Debuffed ATK effect, give the Debuffed ATK condition to the target for 3 turns.
    if 'Inflict Debuffed ATK' in effects:
        add_condition(target, user, 'Debuffed ATK', 3 + 1)
    # If there's an inflict Debuffed DEF effect, give the Debuffed DEF condition to the target for 3 turns.
    if 'Inflict Debuffed DEF' in effects:
        add_condition(target, user, 'Debuffed DEF', 3 + 1)
    # If there's an inflict Debuffed MOB effect, give the Debuffed MOB condition to the target for 3 turns.
    if 'Inflict Debuffed MOB' in effects:
        add_condition(target, user, 'Debuffed MOB', 3 + 1)
    # If there's an inflict Debuffed RNG effect, give the Debuffed RNG condition to the target for 3 turns.
    if 'Inflict Immobilization' in effects:
        add_condition(target, user, 'Immobilization', 1 + 1)
    # If there's an inflict disabled action effect, give the disabled action condition to the target for 1 turn.
    if 'Inflict Disabled Action' in effects:
        add_condition(target, user, 'Disabled Action', 1 + 1)
    # If there's a knockback effect, move the target back two spaces, or four spaces for knockback+.
    if 'Knockback' in effects:
        ms_withdraw(target, user, 2, "forced")
    if 'Knockback+' in effects:
        ms_withdraw(target, user, 4, "forced")
    # If there's a pull in effect, move the target forward two spaces, or four spaces for pull in+.
    if 'Pull In' in effects:
        ms_approach(target, user, 2, "forced")
    if 'Pull In+' in effects:
        ms_approach(target, user, 4, "forced")

def special_drawback(target, user, effects):
    "Inflicts drawbacks on a special move's user."
    # If there's a take immobilization effect, give the immobilization condition to the user for 1 turn.
    if 'Take Immobilization' in effects:
        add_condition(user, target, 'Immobilization', 1 + 1)
    # If there's an inflict disabled action effect, give the disabled action condition to the user for 1 turn.
    if 'Take Disabled Action' in effects:
        add_condition(user, target, 'Disabled Action', 1 + 1)

def add_condition(character, turnchar, condition, duration):
    "Adds a condition to a fighter."
    # The first value is the remaining turns - the second value is whose turn to count down on.
    character.db.Combat_Conditions.update({condition:[duration, turnchar]})
    # Tell everyone!
    character.location.msg_contents("%s gains the |255[|455%s|255]|n condition." % (character, condition))

def condition_tickdown(character, turnchar):
    "Ticks down the duration of conditions on a character at the end of a given character's turn."
    for key in character.db.Combat_Conditions:
        # The first value is the remaining turns - the second value is whose turn to count down on.
        condition_duration = character.db.Combat_Conditions[key][0]
        condition_turnchar = character.db.Combat_Conditions[key][1]
        # Count down if the given turn character matches the condition's turn character.
        if condition_turnchar == turnchar:
            character.db.Combat_Conditions[key][0] -= 1
        if character.db.Combat_Conditions[key][0] <= 0:
            # If the duration is brought down to 0, remove the condition and inform everyone.
            character.location.msg_contents("%s no longer has the |255[|455%s|255]|n condition." % (str(character), str(key)))
            del character.db.Combat_Conditions[key]

def pretty_special(character, specialname):
    "Returns a pretty-looking readout of a special move."
    effectlist = character.db.Special_Moves[specialname][1]
    effectstring = utils.list_to_string(effectlist, endsep="|255and|455", addquote=False)
    effectstringlength = len(effectstring)
    if "|255and|455" in effectstring:
        effectstringlength -= 8
    specialdesc = character.db.Special_Moves[specialname][2]
    paddinglength = max((80 - effectstringlength - len(specialname) - 9), 0)
    padding = ('{:-^%i}' % paddinglength).format('')
    text = "|455%s |255[|455%s|255] %s |455%i|255 SP|n\n%s" % (specialname, effectstring, padding, special_cost(effectlist), specialdesc)
    return text
    
def check_stat_requirements(character, effect):
    "Verifies if a character meets the stat requirements to take a special effect. Returns false if fail, true if pass."
    specialdict = special_dictionary()
    # Get the character's stats.
    char_stats = [character.db.ATM, character.db.DEF, character.db.VIT, character.db.ATR, character.db.MOB, character.db.SPE]
    # Get the prerequisite stats from the special dictionary.
    special_req = [specialdict[effect][3][0], specialdict[effect][3][1], specialdict[effect][3][2], specialdict[effect][3][3], specialdict[effect][3][4], specialdict[effect][3][5]]
    current_loop = 0
    # Compare each stat to each prerequisite - if the prereq exceeds the stat, return False.
    for stat in special_req:
        if stat > char_stats[current_loop]:
            return False
        current_loop += 1
    return True
    
def verify_special_move(character, specialname):
    "Verifies if a character can use a special move they've defined. Returns an error message if one is found, or False if it checks out."
    effectlist = character.db.Special_Moves[specialname][1]
    # First, make sure they have enough SP to use it.
    if special_cost(effectlist) > character.db.SP:
        return "You don't have enough total SP to ever use |255[|455%s|255].|n" % specialname
    # Then, check to make sure they meet the stat requirements for the effects.
    for effect in effectlist:
        if not check_stat_requirements(character, effect):
            return "You don't meet the stat requirements for the |255[|455%s|255]|n effect - you may have changed your stats after defining the special move." % effect
    # If it's all good, return False.
    return False

def special_dictionary():
    "A great big dictionary of special move effects and various info about them!"
    # Name: (Cost, Move types, Incompatibilities, Minimum Stat Requirement [AM,D,V,AR,M,S], Description)
    special_dictionary = {
        'Absorb':(2, ['Special Defense'], [], [0,0,0,0,0,0], 'Recover HP from a successful defense roll'),
        'Bonus Action':(2, ['Support Other', 'Support Self', 'Hinder Other'], ['Second Only'], [0,0,0,0,0,0], 'Take another non-special action after using your special move'),
        'Boosted Attack':(2, ['Special Melee Attack', 'Special Ranged Attack'], ['Reduced Attack'], [0,0,0,0,0,0], 'Adds 2 to your attack roll'),
        'Boosted Defense':(2, ['Special Defense'], [], [0,0,0,0,0,0], 'Adds 2 to your defense roll'),
        'Bypass Defense':(2, ['Special Melee Attack', 'Special Ranged Attack'], [], [0,0,0,0,0,0], 'Target\'s defense roll is halved against your attack'),
        'Charge Move':(-2, ['Special Melee Attack', 'Special Ranged Attack', 'Special Defense', 'Support Other', 'Support Self', 'Hinder Other'], [''], [0,0,0,0,0,0], 'Move must be prepared with \'charge\' command'),
        'Counterattack':(2, ['Special Defense'], ['Reflect'], [0,0,0,0,0,0], 'On successful defense, attack your opponent'),
        'Desperation Move':(-1, ['Special Melee Attack', 'Special Ranged Attack', 'Special Defense', 'Support Other', 'Support Self', 'Hinder Other'], [], [0,0,1,0,0,0], 'Can only use this move if at 1/3 HP or less'),
        'Double Attack':(2, ['Special Melee Attack', 'Special Ranged Attack'], ['Lunge Attack', 'Parting Attack', 'No Damage'], [0,0,0,0,0,0], 'Make two attacks - effects apply to both'),
        'Double Damage':(2, ['Special Melee Attack', 'Special Ranged Attack'], ['Half Damage', 'No Damage'], [0,0,0,0,0,0], 'Multiply your attack\'s damage by 2 on hit'),
        'Grant Buffed ATK':(2, ['Support Other', 'Support Self'], [], [0,0,0,0,0,0], 'Target has +1 to attack rolls for 3 turns'),
        'Grant Buffed DEF':(2, ['Support Other', 'Support Self'], [], [0,0,0,0,0,0], 'Target has +1 to defense rolls for 3 turns'),
        'Grant Buffed MOB':(2, ['Support Other', 'Support Self'], [], [0,0,0,0,0,0], 'Target has +1 movement for 3 turns'),
        'Half Damage':(-1, ['Special Melee Attack', 'Special Ranged Attack'], ['Double Damage', 'No Damage'], [0,0,0,0,0,0], 'Divide your attack\'s damage by 2 on hit'),
        'Halve Damage':(2, ['Special Defense'], ['Negate Damage'], [0,0,0,0,0,0], 'Reduce incoming attack\'s damage by half if it hits'),
        'Heal':(2, ['Support Other', 'Support Self'], [], [0,0,0,0,0,0], 'Recover HP, from 1 to target\'s VIT stat'),
        'Inflict Debuffed ATK':(2, ['Special Melee Attack', 'Special Ranged Attack', 'Hinder Other'], [], [0,0,0,0,0,0], 'Target has -1 to attack rolls for 3 turns'),
        'Inflict Debuffed DEF':(2, ['Special Melee Attack', 'Special Ranged Attack', 'Hinder Other'], [], [0,0,0,0,0,0], 'Target has -1 to defense rolls for 3 turns'),
        'Inflict Debuffed MOB':(2, ['Special Melee Attack', 'Special Ranged Attack', 'Hinder Other'], [], [0,0,0,0,0,0], 'Target has -1 movement for 3 turns'),
        'Inflict Immobilization':(2, ['Special Melee Attack', 'Special Ranged Attack', 'Hinder Other'], [], [0,0,0,0,0,0], 'Target can\'t move next turn'),
        'Inflict Disabled Action':(3, ['Special Melee Attack', 'Special Ranged Attack', 'Hinder Other'], [], [0,0,0,0,0,0], 'Target can\'t take an action next turn'),
        'Knockback':(1, ['Special Melee Attack', 'Special Ranged Attack', 'Hinder Other'], ['Pull In', 'Knockback+', 'Pull In+'], [0,0,0,0,0,0], 'Target is pushed 2 steps away from you'),
        'Knockback+':(2, ['Special Melee Attack', 'Special Ranged Attack', 'Hinder Other'], ['Pull In', 'Pull In+', 'Knockback'], [0,0,0,0,0,0], 'Target is pushed 4 steps away from you'),
        'Leech':(2, ['Special Melee Attack', 'Special Ranged Attack'], ['No Damage'], [0,0,0,0,0,0], 'If your attack hits, recover given damage to HP'),
        'Lunge Attack':(2, ['Special Melee Attack'], ['Parting Attack'], [0,0,0,0,0,0], 'Move 2 steps forward for free before attacking'),
        'Melee-Only Defense':(-1, ['Special Defense'], ['Ranged-Only Defense'], [0,0,0,0,0,0], 'Only works against melee attacks'),
        'Negate Damage':(4, ['Special Defense'], ['Halve Damage'], [0,0,0,0,0,0], 'Negate incoming attack\'s damage - effects still happen'),
        'Negate Effects':(2, ['Special Defense'], [''], [0,0,0,0,0,0], 'Negate incoming attack\'s effects - still take damage'),
        'No Damage':(-2, ['Special Melee Attack'], ['Double Damage', 'Half Damage'], [0,0,0,0,0,0], 'Deals no damage on hit, but other effects still occur'),
        'Opening Gambit':(-3, ['Special Melee Attack', 'Special Ranged Attack', 'Support Other', 'Support Self', 'Hinder Other'], ['Heal'], [0,0,0,0,0,0], 'Move can only be used on your first turn'),
        'Parting Attack':(2, ['Special Melee Attack', 'Special Ranged Attack'], ['Lunge Attack'], [0,0,0,0,0,0], 'Move 2 steps away for free after attacking'),
        'Perfect Attack':(4, ['Special Melee Attack', 'Special Ranged Attack'], ['Precise Attack'], [0,0,0,0,0,0], 'Set attack roll to 10'),
        'Perfect Defense':(4, ['Special Defense'], ['Precise Defense'], [0,0,0,0,0,0], 'Set defense roll to 10'),
        'Point-Blank':(2, ['Special Ranged Attack'], [], [0,0,0,0,0,0], 'Use a ranged attack in melee'),
        'Precise Attack':(2, ['Special Melee Attack', 'Special Ranged Attack'], ['Perfect Attack'], [0,0,0,0,0,0], 'Set attack roll to 6'),
        'Precise Defense':(2, ['Special Defense'], ['Precise Defense'], [0,0,0,0,0,0], 'Set defense roll to 6'),
        'Projected Strike':(2, ['Special Melee Attack'], ['Lunge'], [0,0,0,0,0,0], 'Use a melee attack at range'),
        'Pull In':(1, ['Special Ranged Attack', 'Hinder Other'], ['Knockback', 'Knockback+', 'Pull In+'], [0,0,0,0,0,0], 'Target is pulled 2 steps closer to you'),
        'Pull In+':(1, ['Special Ranged Attack', 'Hinder Other'], ['Knockback', 'Knockback+', 'Pull In+'], [0,0,0,0,0,0], 'Target is pulled 4 steps closer to you'),
        'Ranged-Only Defense':(-1, ['Special Defense'], ['Melee-Only Defense'], [0,0,0,0,0,0], 'Only works against ranged attacks'),
        'Risky Defense':(-1, ['Special Defense'], ['Precise Defense', 'Perfect Defense', 'Negate Damage'], [0,0,0,0,0,0], 'Take double damage if defense fails'),
        'Reflect':(2, ['Special Defense'], ['Counterattack'], [0,0,0,0,0,0], 'On successful defense, send attack back at attacker'),
        'Recoil':(-1, ['Special Melee Attack', 'Special Ranged Attack'], ['No Damage'], [0,0,0,0,0,0], 'If your attack hits, take half damage given'),
        'SP Recover':(2, ['Support Self'], ['First Only'], [0,0,0,0,0,0], 'Regain 3 SP (1 without drawbacks)'),
        'Super Dash':(2, ['Support Self'], [], [0,0,0,0,0,0], 'Dash with +2 extra movement'),
        'Take Disabled Action':(-2, ['Special Melee Attack', 'Special Ranged Attack', 'Special Defense', 'Support Other', 'Support Self', 'Hinder Other'], [''], [0,0,0,0,0,0], 'You can\'t take an action on your next turn'),
        'Take Immobilization':(-1, ['Special Melee Attack', 'Special Ranged Attack', 'Special Defense', 'Support Other', 'Support Self', 'Hinder Other'], [''], [0,0,0,0,6,0], 'You can\'t move on your next turn'),
        'Touch Effect':(-1, ['Support Other', 'Hinder Other'], [''], [0,0,0,0,0,0], 'Can only use this move on engaged targets'),
        'Vital Move':(-1, ['Special Melee Attack', 'Special Ranged Attack', 'Special Defense', 'Support Other', 'Support Self', 'Hinder Other'], [], [0,0,3,0,0,0], 'Can only use this move if at 2/3 HP or more'),
        }
    return special_dictionary


