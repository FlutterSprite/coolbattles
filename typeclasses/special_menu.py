from evennia.utils import evmenu
from evennia.utils import utils
from world import rules

def menunode_specialtype(caller, raw_input):
    "This is the top menu screen."
    # First, initialize all the temporary speical move info.
    caller.ndb.special_name = ""
    caller.ndb.special_type = ""
    caller.ndb.special_effect_1 = ""
    caller.ndb.special_effect_2 = ""
    caller.ndb.special_desc = ""
    
    text = "What kind of special move would you like to create?"
    options = ({"key": "Special Melee Attack", "desc":"Make a melee attack with special properties and effects", "goto": "first_effect"},
               {"key": "Special Ranged Attack", "desc":"Make a ranged attack with special properties and effects", "goto": "first_effect"},
               {"key": "Special Defense", "desc":"Defend from an opponent's attack with extra benefits", "goto": "first_effect"},
               {"key": "Support Self", "desc":"Give yourself a special benefit or condition", "goto": "first_effect"},
               {"key": "Support Other", "desc":"Give another a special benefit or condition", "goto": "first_effect"},
               {"key": "Hinder Other", "desc":"Inflict detriments or harmful conditions on an enemy", "goto": "first_effect"})
    return text, options

    
def first_effect(caller, raw_input):
    "This sets the first special effect."
    # Set the special type to the last menu's input.
    caller.ndb.special_type = raw_input
    # It's case-sensitive, so correct the case first.
    type_list = ["Special Melee Attack", "Special Ranged Attack", "Special Defense", "Support Self", "Support Other", "Hinder Other"]
    for name in type_list:
        if caller.ndb.special_type.lower() in name.lower():
            caller.ndb.special_type = name

    # Import the special dictionary and create a list for valid special moves.
    specialdict = rules.special_dictionary()
    
    text = "Choose a first special effect:"
    options = []
    valid_effect_list = []
    for special in specialdict:
        # Hoo boy, here goes - if the effect matches the special time, has a positive cost, isn't 'second only' in the incompatibilities, and meets the stat requirements, add it to the list of valid effects.
        if caller.ndb.special_type in specialdict[special][1] and specialdict[special][0] >= 0 and 'Second Only' not in specialdict[special][2] and rules.check_stat_requirements(caller, special):
            valid_effect_list.append(special)
    # Then sort the list of valid effects alphabetically.
    valid_effect_list = sorted(valid_effect_list)
    for special in valid_effect_list:
        # Retrieve all the info from the special dictionary and populate the list of special effects with options.
        specialname = special
        specialcost = specialdict[special][0]
        specialdesc = specialdict[special][4]
        description = "|255(|455%i|255 SP)|n: %s" % (specialcost, specialdesc)
        if specialcost < 0:
            description = "|522(|544%i|522 SP)|n: %s" % (specialcost, specialdesc)
        options.append({"key":specialname, "desc":description, "goto":"prompt_second"})
    return text, options

def prompt_second(caller, raw_input):
    "Asks the player if they'd like to choose a second effect."
    # First, let's set the first effect and correct the case.
    caller.ndb.special_effect_1 = raw_input
    specialdict = rules.special_dictionary()
    for special in specialdict:
        if caller.ndb.special_effect_1.lower() == str(special).lower():
            caller.ndb.special_effect_1 = special
    

    text = "You selected: |255[|455%s|255]|n|/Would you like to select a second effect or cost-reducing limit or drawback?" % caller.ndb.special_effect_1
    options = ({"key": "Yes", "desc":"Pick a second effect", "goto": "second_effect"},
               {"key": "No", "desc":"Move on to name & description", "goto": "name_special"}
               )
    return text, options

def second_effect(caller, raw_input):
    "This sets the second special effect."
    # Import the special dictionary and create a list for valid special moves.
    specialdict = rules.special_dictionary()
    
    text = "Choose a second special effect:"
    options = []
    valid_effect_list = []
    for special in specialdict:
        # Matches special type, isn't the first effect, isn't 'first only' in the incompatibilities, and isn't a barred effect in the dictionary
        if caller.ndb.special_type in specialdict[special][1] and special != caller.ndb.special_effect_1 and caller.ndb.special_effect_1 not in specialdict[special][2] and rules.check_stat_requirements(caller, special) and 'First Only' not in specialdict[special][2]:
            # Test for a special case - if the first effect is SP recover, the second effect can only be a drawback (cost less than 0)
            if caller.ndb.special_effect_1 != "SP Recover":
                valid_effect_list.append(special)
            else:
                if specialdict[special][0] < 0:
                    valid_effect_list.append(special)
    valid_effect_list = sorted(valid_effect_list)
    for special in valid_effect_list:
        specialname = special
        specialcost = specialdict[special][0]
        specialdesc = specialdict[special][4]
        description = "|255(|455%i|255 SP)|n: %s" % (specialcost, specialdesc)
        if specialcost < 0:
            description = "|522(|544%i|522 SP)|n: %s" % (specialcost, specialdesc)
        options.append({"key":specialname, "desc":description, "goto":"name_special"})
    return text, options

def name_special(caller, raw_input):
    # First, let's set the second effect and correct the case, if the answer 'no' wasn't given to get here.
    specialdict = rules.special_dictionary()
    if raw_input.lower() != "no":
        caller.ndb.special_effect_2 = raw_input
        for special in specialdict:
            if caller.ndb.special_effect_2.lower() == str(special).lower():
                caller.ndb.special_effect_2 = special
    else:
        caller.ndb.special_effect_2 = ""
    effectlist = [caller.ndb.special_effect_1]
    if caller.ndb.special_effect_2:
        effectlist.append(caller.ndb.special_effect_2)
    effectstring = utils.list_to_string(effectlist, endsep="|255and|455", addquote=False)

    text = "The effects you chose are:\n|255[|455%s|255] (|455%i|255 SP)\n|nGive your special move a name! (30 characters maximum)\nExample: \"Burning Fury Punch\", \"Magic Bubble\", \"Psionic Blast\", etc." % (effectstring, rules.special_cost(effectlist))
    options = ({"key": "_default", "goto": "verify_name"})
    return text, options

def verify_name(caller, raw_input):
    "Sets the special name and asks the player to verify it."
    specialname = raw_input
    if len(specialname) > 30:
        specialname = specialname[:29]
    if specialname == "":
        specialname = "The Nameless Special"
    caller.ndb.special_name = specialname

    text = "You chose the name:|/|255[|455%s|255]|n\nIs this all right?" % specialname
    options = ({"key": "Yes", "desc":"Move on to description", "goto": "desc_special"},
               {"key": "No", "desc":"Enter a new name", "goto": "name_special"}
               )
    return text, options

def desc_special(caller, raw_input):

    text = "Describe your special move! This can include how your character performs the move,\nand what power, technique, or equipment gives them this ability. (300 characters maximum)"
    options = ({"key": "_default", "goto": "verify_desc"})
    return text, options

def verify_desc(caller, raw_input):
    "Sets the special desc and asks the player to verify it."
    specialdesc = utils.wrap(raw_input, width=80)
    if len(specialdesc) > 300:
        specialdesc = specialdesc[:299]
    if specialdesc == "":
        specialdesc = "A special move called %s" % callder.ndb.special_name
    caller.ndb.special_desc = specialdesc
    effectlist = [caller.ndb.special_effect_1]
    if caller.ndb.special_effect_2:
        effectlist.append(caller.ndb.special_effect_2)
    effectstring = utils.list_to_string(effectlist, endsep="|255and|455", addquote=False)
    effectstringlength = len(effectstring)
    if "|255and|455" in effectstring:
        effectstringlength -= 8
    paddinglength = max((80 - effectstringlength - len(caller.ndb.special_name) - 9), 0)
    padding = ('{:-^%i}' % paddinglength).format('')
    text = "Your special move:\n\n|455%s |255[|455%s|255] %s |455%i|255 SP|n\n%s\n\nIs this all right?" % (caller.ndb.special_name, effectstring, padding, rules.special_cost(effectlist), caller.ndb.special_desc)
    options = ({"key": "Yes", "desc":"Finalize special move", "goto": "finalize_special"},
               {"key": "No", "desc":"Enter a new description", "goto": "desc_special"}
               )
    return text, options

def finalize_special(caller, raw_input):
    "Sets the new special move on the player."
    effectlist = [caller.ndb.special_effect_1]
    if caller.ndb.special_effect_2:
        effectlist.append(caller.ndb.special_effect_2)
    # Adds the special move to the character! Yay!
    caller.db.Special_Moves.update({caller.ndb.special_name:(caller.ndb.special_type, effectlist, caller.ndb.special_desc)})
    
    text = "Special move set!"

    return text, None



    
