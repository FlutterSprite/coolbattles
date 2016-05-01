"""
Slow Exit typeclass

Contribution - Griatch 2014


This is an example of an Exit-type that delays its traversal.This
simulates slow movement, common in many different types of games. The
contrib also contains two commands, CmdSetSpeed and CmdStop for changing
the movement speed and abort an ongoing traversal, respectively.

To try out an exit of this type, you could connect two existing rooms
using something like this:

@open north:contrib.slow_exit.SlowExit = <destination>


Installation:

To make all new exits of this type, add the following line to your
settings:

BASE_EXIT_TYPECLASS = "contrib.slow_exit.SlowExit"

To get the ability to change your speed and abort your movement,
simply import and add CmdSetSpeed and CmdStop from this module to your
default cmdset (see tutorials on how to do this if you are unsure).

Notes:

This implementation is efficient but not persistent; so incomplete
movement will be lost in a server reload. This is acceptable for most
game types - to simulate longer travel times (more than the couple of
seconds assumed here), a more persistent variant using Scripts or the
TickerHandler might be better.

"""

from evennia import DefaultExit, utils, Command

class SlowExit(DefaultExit):
    """
    This overloads the way moving happens.
    """
    def at_traverse(self, traversing_object, target_location):
        """
        Implements the actual traversal, using utils.delay to delay the move_to.
        """

        # if the traverser has an Attribute move_speed, use that,
        # otherwise default to "walk" speed
        move_speed = traversing_object.db.move_speed or "walk"
        move_delay = max(traversing_object.location.db.RoomSize / 2, 1)
        
        # Keep players from moving in combat or with 0 HP.
        if traversing_object.db.Combat_TurnHandler:
            traversing_object.msg("You can't move, you're in combat!")
            return
            
        if traversing_object.db.HP <= 0:
            traversing_object.msg("You can't move, you've been defeated! Type 'return' to go back to the Institute and recover!")
            return

        def move_callback():
            "This callback will be called by utils.delay after move_delay seconds."
            source_location = traversing_object.location
            if traversing_object.move_to(target_location):
                self.at_after_traverse(traversing_object, source_location)
            else:
                if self.db.err_traverse:
                    # if exit has a better error message, let's use it.
                    self.caller.msg(self.db.err_traverse)
                else:
                    # No shorthand error message. Call hook.
                    self.at_failed_traverse(traversing_object)

        traversing_object.location.msg_contents("%s starts moving %s." % (traversing_object, self.key))
        # create a delayed movement
        deferred = utils.delay(move_delay, callback=move_callback)
        # we store the deferred on the character, this will allow us
        # to abort the movement. We must use an ndb here since
        # deferreds cannot be pickled.
        traversing_object.ndb.currently_moving = deferred


#
# stop moving - command
#

class CmdStop(Command):
    """
    stop moving

    Usage:
      stop

    Stops the current movement, if any.
    """
    key = "stop"

    def func(self):
        """
        This is a very simple command, using the
        stored deferred from the exit traversal above.
        """
        currently_moving = self.caller.ndb.currently_moving
        if not currently_moving:
            self.caller.msg("You are not moving.")
            return
        else:
            currently_moving.cancel()
            self.caller.msg("You stop moving.")
