"""
Room

Rooms are simple containers that has no location of their own.

"""

from evennia import DefaultRoom
from world import rules
from evennia import utils


class Room(DefaultRoom):
    """
    Rooms are like any Object, except their location is None
    (which is default). They also use basetype_setup() to
    add locks so they cannot be puppeted or picked up.
    (to change that, use at_object_creation instead)

    See examples/object.py for a list of
    properties and methods available on all Objects.
    """
    def at_object_creation(self):
        # This is called only at creation.
        self.db.RoomSize = 5
        self.db.CombatAllowed = True
    def return_appearance(self, looker):
        """
        This formats a description. It is the hook a 'look' command
        should call.

        Args:
            looker (Object): Object doing the looking.
        """
        if not looker:
            return
        # get and identify all objects
        visible = (con for con in self.contents if con != looker and
                                                    con.access(looker, "view"))
        exits, users, things = [], [], []
        for con in visible:
            key = con.get_display_name(looker)
            if con.destination:
                exits.append("|lc" + str(con) + "|lt" + key + "|le")
            elif con.has_player:
                users.append("%s: %s" % (key, con.db.shortdesc))
            else:
                things.append(key)
        # get description, build string
        roomname = self.get_display_name(looker)
        roomsize = "|525[Area size: |545%i|525 (%s)]|n" % (self.db.RoomSize, rules.size_name(self.db.RoomSize))
        namelength = len(roomname)
        sizelength = len(roomsize) - 12
        paddinglength = 80 - namelength - sizelength
        padding = ('{:-^%i}' % paddinglength).format('')
        string = "|555%s|n |222%s|n %s\n" % (roomname, padding, roomsize)
        desc = self.db.desc
        if desc:
            string += "%s" % desc
        if exits:
            string += "\n\n{wExits:{n " + ", ".join(exits)
        if not users or things:
            string +="\n|222--------------------------------------------------------------------------------|n"
        if users or things:
            string += "\nFighters here:|222 -----------------------------------------------------------------|n" + "".join(things)
            for character in users:
                string += "\n" + character
            string += "\n|222--------------------------------------------------------------------------------|n"
        return string
    def starting_range(self):
        # Returns starting range.
        size = float(self.db.RoomSize)
        startrange = int(round(size / 2.5))
        return startrange


from commands.default_cmdsets import ChargenCmdset

class ChargenRoom(Room):
    """
    This room class is used by character-generation rooms.
    It makes the ChargenCmdset available.
    """
    def at_object_creation(self):
        # This is called only at first creation
        self.db.RoomSize = 5
        self.db.CombatAllowed = False
        self.cmdset.add(ChargenCmdset, permanent=True)
