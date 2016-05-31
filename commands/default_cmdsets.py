"""
Command sets

All commands in the game must be grouped in a cmdset.  A given command
can be part of any number of cmdsets and cmdsets can be added/removed
and merged onto entities at runtime.

To create new commands to populate the cmdset, see
`commands/command.py`.

This module wraps the default command sets of Evennia; overloads them
to add/remove commands from the default lineup. You can create your
own cmdsets by inheriting from them or directly from `evennia.CmdSet`.

"""

from evennia import default_cmds
from evennia import CmdSet
from commands import command
from typeclasses import slow_exit

class CharacterCmdSet(default_cmds.CharacterCmdSet):
    """
    The `CharacterCmdSet` contains general in-game commands like `look`,
    `get`, etc available on in-game Character objects. It is merged with
    the `PlayerCmdSet` when a Player puppets a Character.
    """
    key = "DefaultCharacter"

    def at_cmdset_creation(self):
        """
        Populates the cmdset
        """
        super(CharacterCmdSet, self).at_cmdset_creation()
        #
        # any commands you add below will overload the default ones.
        #
        self.add(command.CmdLook())
        self.add(command.CmdRest())
        self.add(command.CmdStats())
        self.add(command.CmdFight())
        self.add(command.CmdRangeMessage())
        self.add(command.CmdMeleeMessage())
        self.add(command.CmdAttack())
        self.add(command.CmdSecond())
        self.add(command.CmdDefend())
        self.add(command.CmdEndure())
        self.add(command.CmdPass())
        self.add(command.CmdDisengage())
        self.add(command.CmdWithdraw())
        self.add(command.CmdDash())
        self.add(command.CmdRange())
        self.add(command.CmdSpecial())
        self.add(command.CmdCharge())
        self.add(command.CmdSpecialMessage())
        self.add(command.CmdShortdesc())
        self.add(command.CmdReturn())
        self.add(command.CmdAlly())
        self.add(slow_exit.CmdStop())
        self.add(command.CmdApproach())

class PlayerCmdSet(default_cmds.PlayerCmdSet):
    """
    This is the cmdset available to the Player at all times. It is
    combined with the `CharacterCmdSet` when the Player puppets a
    Character. It holds game-account-specific commands, channel
    commands, etc.
    """
    key = "DefaultPlayer"

    def at_cmdset_creation(self):
        """
        Populates the cmdset
        """
        super(PlayerCmdSet, self).at_cmdset_creation()
        #
        # any commands you add below will overload the default ones.
        #


class UnloggedinCmdSet(default_cmds.UnloggedinCmdSet):
    """
    Command set available to the Session before being logged in.  This
    holds commands like creating a new account, logging in, etc.
    """
    key = "DefaultUnloggedin"

    def at_cmdset_creation(self):
        """
        Populates the cmdset
        """
        super(UnloggedinCmdSet, self).at_cmdset_creation()
        #
        # any commands you add below will overload the default ones.
        #


class SessionCmdSet(default_cmds.SessionCmdSet):
    """
    This cmdset is made available on Session level once logged in. It
    is empty by default.
    """
    key = "DefaultSession"

    def at_cmdset_creation(self):
        """
        This is the only method defined in a cmdset, called during
        its creation. It should populate the set with command instances.

        As and example we just add the empty base `Command` object.
        It prints some info.
        """
        super(SessionCmdSet, self).at_cmdset_creation()
        #
        # any commands you add below will overload the default ones.
        #

class ChargenCmdset(CmdSet):
    """
    This cmdset is used in character generation areas.
    """
    key = "Chargen"
    def at_cmdset_creation(self):
        # This is called at initialization
        self.add(command.CmdSetStat())
        self.add(command.CmdResetStats())
        self.add(command.CmdSetSpecial())
        self.add(command.CmdRemoveSpecial())
        self.add(command.CmdEnterGame())
