"""
Scripts

Scripts are powerful jacks-of-all-trades. They have no in-game
existence and can be used to represent persistent game systems in some
circumstances. Scripts can also have a time component that allows them
to "fire" regularly or a limited number of times.

There is generally no "tree" of Scripts inheriting from each other.
Rather, each script tends to inherit from the base Script class and
just overloads its hooks to have it perform its function.

"""

from evennia import DefaultScript
from random import randint


class Script(DefaultScript):
    """
    A script type is customized by redefining some or all of its hook
    methods and variables.

    * available properties

     key (string) - name of object
     name (string)- same as key
     aliases (list of strings) - aliases to the object. Will be saved
              to database as AliasDB entries but returned as strings.
     dbref (int, read-only) - unique #id-number. Also "id" can be used.
     date_created (string) - time stamp of object creation
     permissions (list of strings) - list of permission strings

     desc (string)      - optional description of script, shown in listings
     obj (Object)       - optional object that this script is connected to
                          and acts on (set automatically by obj.scripts.add())
     interval (int)     - how often script should run, in seconds. <0 turns
                          off ticker
     start_delay (bool) - if the script should start repeating right away or
                          wait self.interval seconds
     repeats (int)      - how many times the script should repeat before
                          stopping. 0 means infinite repeats
     persistent (bool)  - if script should survive a server shutdown or not
     is_active (bool)   - if script is currently running

    * Handlers

     locks - lock-handler: use locks.add() to add new lock strings
     db - attribute-handler: store/retrieve database attributes on this
                        self.db.myattr=val, val=self.db.myattr
     ndb - non-persistent attribute handler: same as db but does not
                        create a database entry when storing data

    * Helper methods

     start() - start script (this usually happens automatically at creation
               and obj.script.add() etc)
     stop()  - stop script, and delete it
     pause() - put the script on hold, until unpause() is called. If script
               is persistent, the pause state will survive a shutdown.
     unpause() - restart a previously paused script. The script will continue
                 from the paused timer (but at_start() will be called).
     time_until_next_repeat() - if a timed script (interval>0), returns time
                 until next tick

    * Hook methods (should also include self as the first argument):

     at_script_creation() - called only once, when an object of this
                            class is first created.
     is_valid() - is called to check if the script is valid to be running
                  at the current time. If is_valid() returns False, the running
                  script is stopped and removed from the game. You can use this
                  to check state changes (i.e. an script tracking some combat
                  stats at regular intervals is only valid to run while there is
                  actual combat going on).
      at_start() - Called every time the script is started, which for persistent
                  scripts is at least once every server start. Note that this is
                  unaffected by self.delay_start, which only delays the first
                  call to at_repeat().
      at_repeat() - Called every self.interval seconds. It will be called
                  immediately upon launch unless self.delay_start is True, which
                  will delay the first call of this method by self.interval
                  seconds. If self.interval==0, this method will never
                  be called.
      at_stop() - Called as the script object is stopped and is about to be
                  removed from the game, e.g. because is_valid() returned False.
      at_server_reload() - Called when server reloads. Can be used to
                  save temporary variables you want should survive a reload.
      at_server_shutdown() - called at a full server shutdown.

    """
    pass

from world import rules
from random import randint

class DefenseTimeout(DefaultScript):
    "Automatically makes a character defend after a 30 second delay."
    def at_script_creation(self):
        "Called once, during initial creation"
        self.key = ("%s_def_timeout" % self.obj)
        self.desc = "Defense timeout handler."
        self.interval = 1 # every 1 second
        self.persistent = True
        self.db.TimeRemaining = 30
        self.obj.msg("|530----- |540Incoming Attack! |530-----|n")
    def at_repeat(self):
        "Called every self.interval seconds"
        if not self.obj.db.Combat_IncomingAttack:
            self.stop()
            return
        self.db.TimeRemaining -= 1
        if self.db.TimeRemaining == 10:
            self.obj.msg("|420Respond to %s's attack! Timing out soon!|n" % self.obj.db.Combat_IncomingAttack[1])
        elif self.db.TimeRemaining <= 0:
            self.obj.msg("|420Timed out - defending automatically|n")
            rules.defend_queue(self.obj, "defend", [])
            self.stop()

class TurnHandler(DefaultScript):
    "Created when a fight starts and handles turn taking."
    def at_script_creation(self):
        self.key = ("%i_turn_handler" % randint(1,10000))
        self.desc = "Turn order handler."
        self.interval = 2 # every 2 seconds
        self.persistent = True
        # Add a DB object to the room with the script for testing.
        self.obj.db.Combat_TurnHandler = self
        # Add every character who can fight to the turn order.
        self.db.fighters = []
        for thing in self.obj.contents:
            if thing.db.HP:
                self.db.fighters.append(thing)
        for fighter in self.db.fighters:
            fighter.db.Combat_TurnHandler = self
            fighter.db.Combat_LastAction = "null"
            fighter.db.Combat_Conditions = {}
        # Roll initiative for each fighter in the list and sort them.
        ordered_by_roll = sorted(self.db.fighters, key=rules.roll_init, reverse=True)
        turnorderstring = '{:-^80}'.format(" Turn order is: %s " % ", ".join(obj.key for obj in ordered_by_roll))
        self.combat_msg("|445%s|n" % turnorderstring)
        self.db.fighters = ordered_by_roll
        # Set up the current turn and turn timeout delay.
        self.db.turn = 0
        self.db.timer = 60 # 2 minutes
        rules.start_turn(self.db.fighters[0])
        # Set up ranges.
        for fighter in self.db.fighters:
            rules.init_range(fighter, self.db.fighters)
        # Prompt the first character's turn.
        rules.turn_prompt(self.db.fighters[0])
    def at_repeat(self):
        "Called every self.interval seconds"
        currentchar = self.db.fighters[self.db.turn]
        self.db.timer -= 1
        if currentchar.db.Combat_Actions == 0 and currentchar.db.Combat_Moves == 0 and not currentchar.db.Combat_Second:
            # Advance the turn when current character has no actions, moves, or second attack, but only if there are no outstanding attacks
            if not self.attack_check():
                self.next_turn()
        if self.db.timer == 10:
            # Give a timeout warning, but only if there are no outstanding attacks
            if not self.attack_check():
                currentchar.msg("|420WARNING: About to time out!|n")
        if self.db.timer <= 0:
            # Advance the turn when the timer runs out, but only if there are no outstanding attacks
            if not self.attack_check():
                currentchar.db.Combat_LastAction = "disengage"
                self.combat_msg("%s's turn timed out! |222[Disengage]|n" % currentchar)
                self.next_turn()
    def combat_msg(self, message):
        # Sends a message to all characters in combat, even in different rooms.
        for fighter in self.db.fighters:
            fighter.msg(message)
    def attack_check(self):
        # Checks to see if there are any unresolved attacks.
        for fighter in self.db.fighters:
            if fighter.db.Combat_IncomingAttack:
                return True
        return False
    def next_turn(self):
        # Checks to see if every character passed as their last action. If so, end combat.
        DisengageCheck = True
        for fighter in self.db.fighters:
            if fighter.db.Combat_LastAction != "disengage":
                DisengageCheck = False
        if DisengageCheck == True:
            endmessage = '{:-^80}'.format(" All fighters have disengaged! Combat is over! ")
            self.combat_msg("|445%s|n" % endmessage)
            self.stop()
            return
        # Checks to see if only one character is left standing. If so, end combat.
        DefeatedCharacters = 0
        for fighter in self.db.fighters:
            if fighter.db.HP == 0:
                DefeatedCharacters += 1
        if DefeatedCharacters == (len(self.db.fighters) - 1):
            for fighter in self.db.fighters:
                if fighter.db.HP != 0:
                    LastStanding = fighter
            endmessage = '{:-^80}'.format(" Only %s remains! Combat is over! " % LastStanding)
            self.combat_msg("|445%s|n" % endmessage)
            self.stop()
            return
        # Cycles to the next turn.
        currentchar = self.db.fighters[self.db.turn]
        # Ticks down the condition timers on each character.
        for fighter in self.db.fighters:
            rules.condition_tickdown(fighter, currentchar)
        rules.pass_turn(currentchar)
        self.db.turn += 1
        if self.db.turn > len(self.db.fighters) - 1:
            self.db.turn = 0
        newchar = self.db.fighters[self.db.turn]
        self.db.timer = 60
        turnmessage = '{:-^80}'.format(" %s's turn ends - %s's turn begins! " % (currentchar, newchar))
        self.combat_msg("|445%s|n" % turnmessage)
        rules.turn_prompt(newchar)
        rules.start_turn(newchar)
    def at_stop(self):
        "Called at script termination."
        for fighter in self.db.fighters:
            fighter.cmdset.delete("commands.default_cmdsets.CombatCmdset")
            rules.combat_cleanup(fighter)
    def join_fight(self, character):
        "Adds a new character to the fight."
        # Pick a random fighter already in the fight, for later.
        randfighter = self.db.fighters[randint(0, (len(self.db.fighters)-1))]
        # Inserts the fighter to the turn order behind whoever's turn it currently is.
        self.db.fighters.insert(self.db.turn, character)
        # Tick the turn counter forward one to compensate.
        self.db.turn += 1
        # Initialize the character like you do at the start.
        character.db.Combat_TurnHandler = self
        character.db.Combat_LastAction = "null"
        character.db.Combat_Conditions = {}
        # Copy the range from another character.
        character.db.Combat_Range = randfighter.db.Combat_Range
        # Add the new character to everyone else's ranges.
        for fighter in self.db.fighters:
            new_fighters_range = character.location.db.RoomSize
            fighter.db.Combat_Range.update({character:new_fighters_range})
        # Set the range to room's maximum for everyone on the new fighter's range.
        for fighter in self.db.fighters:
            character.db.Combat_Range.update({fighter:character.location.db.RoomSize})
        # Set the new fighter range to themself to 0.
        character.db.Combat_Range.update({character:0})
        # Hopefully, the new fighter is now as far away from every other fighter as possible but themself.
        
        
            
                    
