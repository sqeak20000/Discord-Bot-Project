import os
import asyncio

os.environ.setdefault('DISCORD_BOT_TOKEN', 'test-token')

from config import BLACKLIST_ROLE_NAMES
from moderation import sync_moderation_commands


class DummyTree:
    def __init__(self):
        self.cleared = False
        self.synced = 0

    def command(self, *args, **kwargs):
        def decorator(func):
            return func
        return decorator

    async def clear_commands(self, guild=None):
        self.cleared = True

    async def sync(self, guild=None):
        self.synced += 1
        return []


class DummyBot:
    def __init__(self):
        self.tree = DummyTree()
        self._moderation_commands_setup = False


def test_blacklist_roles_include_expected_entries():
    assert BLACKLIST_ROLE_NAMES['tickets'] == 'ticket blacklist'
    assert BLACKLIST_ROLE_NAMES['code_sharing'] == 'code sharing blacklist'
    assert BLACKLIST_ROLE_NAMES['exalted'] == 'exalted blacklist'
    assert BLACKLIST_ROLE_NAMES['creations'] == 'creations blacklist'


def test_sync_moderation_commands_clears_and_resyncs_command_tree():
    bot = DummyBot()
    asyncio.run(sync_moderation_commands(bot))

    assert bot.tree.cleared is True
    assert bot.tree.synced == 1
