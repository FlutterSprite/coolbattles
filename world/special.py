import rules

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
        rules.recover_hp(target, target.db.VIT)
    # If there's a Heal effect, recover 3 SP.
    if "SP Recover" in effects:
        rules.recover_sp(target, 3)
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
        rules.ms_withdraw(target, user, 2, "forced")
    if 'Knockback+' in effects:
        rules.ms_withdraw(target, user, 4, "forced")
    # If there's a pull in effect, move the target forward two spaces, or four spaces for pull in+.
    if 'Pull In' in effects:
        rules.ms_approach(target, user, 2, "forced")
    if 'Pull In+' in effects:
        rules.ms_approach(target, user, 4, "forced")

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