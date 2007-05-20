# browsershots.org
# Copyright (C) 2006 Johann C. Rocholl <johann@browsershots.org>
#
# This program is free software; you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation; either version 2 of the License, or
# (at your option) any later version.
#
# This program is distributed in the hope that it will be useful, but
# WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE. See the GNU
# General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with this program; if not, write to the Free Software
# Foundation, Inc., 59 Temple Place - Suite 330, Boston,
# MA 02111-1307, USA.

"""
GUI-specific interface functions for Mozilla Firefox on Microsoft Windows.
"""

__revision__ = '$Rev: 503 $'
__date__ = '$Date: 2006-06-17 08:14:59 +0200 (Sat, 17 Jun 2006) $'
__author__ = '$Author: johann $'

import os, time, sys, shutil
import win32api, win32gui, win32con, pywintypes
from win32com.shell import shellcon, shell
from shotfactory04.gui import windows

class Gui(windows.Gui):
    """
    Special functions for Firefox on Windows.
    """

    def reset_browser(self, verbose=True):
        """
        Delete previous session and browser cache.
        """
        # Delete old session
        appdata = shell.SHGetFolderPath(0, shellcon.CSIDL_APPDATA, 0, 0)
        profiles = os.path.join(appdata, 'Mozilla', 'Firefox', 'Profiles')
        for profile in os.listdir(profiles):
            session = os.path.join(profiles, profile, 'sessionstore.js')
            if os.path.exists(session):
                if verbose:
                    print "deleting previous session:", session
                os.unlink(session)
        # Delete all files from the browser cache
        appdata = shell.SHGetFolderPath(0, shellcon.CSIDL_LOCAL_APPDATA, 0, 0)
        profiles = os.path.join(appdata, 'Mozilla', 'Firefox', 'Profiles')
        for profile in os.listdir(profiles):
            cache =  os.path.join(profiles, profile, 'Cache')
            if os.path.exists(cache):
                if verbose:
                    print "deleting browser cache:", cache
                shutil.rmtree(cache)

    def start_browser(self, config, url, options):
        """
        Start browser and load website.
        """
        if config['command'] == 'firefox':
            command = r'c:\progra~1\mozill~1\firefox.exe'
        else:
            command = config['command']
        print 'running', command
        os.spawnl(os.P_DETACH, command, os.path.basename(command), url)
        print "Sleeping %d seconds while page is loading." % options.wait
        time.sleep(options.wait)

    def down(self, verbose=False):
        """
        Scroll down one line.
        """
        firefox = self.find_window_by_title_suffix(' Firefox', verbose)
        scrollable = self.get_child_window(firefox, verbose)
        self.send_keypress(scrollable, win32con.VK_DOWN)
        time.sleep(0.1)


# Test scrolling from command line
if __name__ == '__main__':
    gui = Gui(1024, 768, 24, 90)
    gui.down(verbose=True)