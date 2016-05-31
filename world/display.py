import rules
from evennia import ansi
from evennia import utils

def turn_prompt(character):
    "Gives a player combat information when their turn comes up."
    turn_handler = character.db.Combat_TurnHandler
    fighterlist = turn_handler.db.fighters
    promptline = '{:-^88}'.format(" |540It's your turn!|530 ")
    character.msg("|530%s|n" % promptline)
    for fighter in fighterlist:
        character.msg(combat_status_line(fighter, character))
    character.msg("|530--------------------------------------------------------------------------------|n")
    
def range_name(value):
    "Converts a range value to a name."
    rangedict = {0:"Engaged", 1:"Very Close", 2:"Close", 3:"Medium-Close", 4:"Medium", 5:"Medium-Far", 6:"Far", 7:"Very Far", 8:"Distant", 9:"Very Distant", 10:"Remote"}
    if value not in rangedict:
        return "Unknown"
    return rangedict[value]

def size_name(value):
    "Converts a room size value to a name."
    sizedict = {0:"Claustrophobic", 1:"Cramped", 2:"Tiny", 3:"Small", 4:"Small", 5:"Moderate", 6:"Moderate", 7:"Large", 8:"Large", 9:"Huge", 10:"Expansive"}
    if value not in sizedict:
        return "Unknown"
    return sizedict[value]
    
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
    barstring = ("|555" + barcolor + barstring[:rounded_percent] + '|n|[011' + barstring[rounded_percent:])
    # For some reason, sometimes the health bar is one character too long, so I fixed it here. Whatever.
    return barstring[:int(length) + 15] + "|n"

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
    
def prompt_update(character):
    "Updates the given character's prompt. Called at the end of every command or when the character takes/heals damage."
    if not rules.is_fighter(character):
        return
    hbar = health_bar(character.db.HP, max(character.db.VIT * 3, 1), 20)
    action = ""
    moves = ""
    sptotal = "|255SP: |455%i |255/|455 %i|n" % (character.db.SP, character.db.SPE * 2)
    engaged = False
    # Checks to see if there are any fighters engaged with character:
    if character.db.Combat_TurnHandler and character.db.Combat_Range and character.db.Combat_TurnHandler.db.fighters:
        for fighter in character.db.Combat_TurnHandler.db.fighters:
            if fighter != character and character.db.Combat_Range[fighter] == 0:
                engaged = True
    if character.db.Combat_Actions:
        action = "|525[Action Ready]|n "
        if engaged:
        # Colors the 'Action Ready' text red if engaged with anyone.
            action = "|522[Action Ready]|n "
    if character.db.Combat_Moves:
        moves = "|552[Moves: |554%i|552]|n" % character.db.Combat_Moves
    if character.db.Combat_Second:
        action = "|255[Second Attack Ready] |n"
    promptline = ("%s: %s %s %s%s" % (str(character), hbar, sptotal, action, moves))
    character.msg(prompt=promptline)
    
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
    text = "|455%s |255[|455%s|255] %s |455%i|255 SP|n\n%s" % (specialname, effectstring, padding, rules.special_cost(effectlist), specialdesc)
    return text