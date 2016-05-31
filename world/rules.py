from random import randint
from evennia import utils
import math

# Import all movement / range related functions.
from movement import distance_dec, distance_inc, approach, withdraw, ms_approach, ms_withdraw, move_block_test, init_range, get_engage_group
# Import all value-to-text, display, and prompt functions.
from display import range_name, size_name, turn_prompt, health_bar, combat_status_line, prompt_update, pretty_special
# Import all special move / condition related functions.
from special import special_cost, special_support, special_hinder, special_drawback, add_condition, condition_tickdown, check_stat_requirements, verify_special_move, special_dictionary

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
    prompt_update(target)
    target.msg(effect="Damage")

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
    prompt_update(character)

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
    prompt_update(character)
    

def pass_turn(character):
    "Pass on a turn. Can be initiated by command, timeout, or having no actions available."
    character.db.Combat_Actions = 0
    character.db.Combat_Moves = 0
    if character.db.Combat_Second:
        del character.db.Combat_Second
    prompt_update(character)

def combat_cleanup(character):
    "Cleans up all the combat-related attributes on a character."
    # Goes through every attribute - if it starts with "combat_", delete it.
    for attr in character.attributes.all():
        if attr.key[:7] == "combat_":
            character.attributes.remove(key=attr.key)

def is_fighter(character):
    "Determines whether the given object is a fighter (has stats, etc.)"
    for stat in ("ATM", "DEF", "VIT", "MOB", "ATR", "SPE"):
        if character.attributes.has(stat):
            return True
    return False

def recover_hp(character, amount):
    "Recovers HP as part of a special move."
    character.db.HP += amount
    if character.db.HP > (max(character.db.VIT * 3, 1)):
        character.db.HP = max(character.db.VIT * 3, 1)
    character.location.msg_contents("%s recovers from some damage! |252[|454+%i|252 HP]" % (character, amount))
    prompt_update(character)
    
def recover_sp(character, amount):
    "Recovers HP as part of a special move."
    character.db.SP += amount
    if character.db.SP > character.db.SPE * 2:
        character.db.SP = character.db.SPE * 2
    character.location.msg_contents("%s recovers some SP! |255[|455+%i|255 SP]" % (character, amount))
    prompt_update(character)

def reduce_hp(character, amount):
    "Reduces HP as part of a special move or harmful condition."
    character.location.msg_contents("%s takes damage! |252[|454-%i|252 HP]" % (character, amount))
    damage_target(character, amount)
    prompt_update(character)
    
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




