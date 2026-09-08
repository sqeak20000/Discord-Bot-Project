import os

os.environ.setdefault('DISCORD_BOT_TOKEN', 'test-token')

from config import BLACKLIST_ROLE_NAMES


def test_blacklist_roles_include_expected_entries():
    assert BLACKLIST_ROLE_NAMES['tickets'] == 'ticket blacklist'
    assert BLACKLIST_ROLE_NAMES['code_sharing'] == 'code sharing blacklist'
    assert BLACKLIST_ROLE_NAMES['exalted'] == 'exalted blacklist'
    assert BLACKLIST_ROLE_NAMES['creations'] == 'creations blacklist'
