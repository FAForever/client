import os
import sys
import traceback
from config import Settings

if sys.platform == 'win32':
    import win32api
    import win32con
    import win32security
    from config import admin

def set_data_path_permissions():
    """
    Set the owner of C:\ProgramData\FAForever recursively to the current user
    """
    if sys.platform != 'win32':
        return

    if not admin.isUserAdmin():
        win32api.MessageBox(0,
                            "FA Forever needs to fix folder permissions due to"
                            "user change. Please confirm the following two"
                            "admin prompts.", "User changed")
    if sys.platform != 'win32' or 'CI' in os.environ:
        return

    data_path = Settings.get('client/data_path')
    if not os.path.exists(data_path):
        return

    my_user = win32api.GetUserNameEx(win32con.NameSamCompatible)
    admin.runAsAdmin(["icacls", data_path, "/setowner", my_user, "/T"])
    admin.runAsAdmin(["icacls", data_path, "/reset", "/T"])

def check_data_path_permissions():
    """
    Checks if the current user is owner of C:\ProgramData\FAForever
    Fixes the permissions in case that FAF was run as different user before
    """
    if sys.platform != 'win32' or 'CI' in os.environ:
        return

    data_path = Settings.get('client/data_path')
    if not os.path.exists(data_path):
        return

    try:
        my_user = win32api.GetUserNameEx(win32con.NameSamCompatible)
        sd = win32security.GetFileSecurity(data_path, win32security.OWNER_SECURITY_INFORMATION)
        owner_sid = sd.GetSecurityDescriptorOwner()
        name, domain, _ = win32security.LookupAccountSid(None, owner_sid)
        data_path_owner = "%s\\%s" % (domain, name)

        if (my_user != data_path_owner):
            set_data_path_permissions()
    except Exception, e:
        # We encountered error 1332 in win32security.LookupAccountSid here:
        # forums.faforever.com/viewtopic.php?f=3&t=13728
        # msdn.microsoft.com/en-us/library/windows/desktop/aa379166.aspx says:
        # "It also occurs for SIDs that have no corresponding account name,
        # such as a logon SID that identifies a logon session." So let's just
        # fix permissions on every exception for now and wait for someone stuck
        # in a permission-loop.
        win32api.MessageBox(0,
                            "FA Forever ran into an exception checking the "
                            "data folder permissions: '{}'\n"
                            "If you get this popup more than one time, please"
                            "report a screenshot of this popup to tech support"
                            " forum. Full stacktrace:\n{}"
                            .format(e, traceback.format_exc()),
                            "Permission check exception")
        set_data_path_permissions()

def make_dirs():
    check_data_path_permissions()
    for dir in [
        'client/data_path',
        'game/logs/path',
        'game/bin/path',
        'game/mods/path',
        'game/engine/path',
        'game/maps/path',
    ]:
        path = Settings.get(dir)
        if path is None:
            raise Exception("Missing configured path for {}".format(path))
        if not os.path.isdir(path):
            try:
                os.makedirs(path)
            except IOError:
                set_data_path_permissions()
                os.makedirs(path)
