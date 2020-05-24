#!/usr/bin/python3 -u

# Modified from code at https://github.com/oweitman/squeezelite-bluetooth

from __future__ import absolute_import, print_function, unicode_literals

#from gi.repository import GObject as gobject
from gi.repository import GLib as glib

import dbus
import dbus.mainloop.glib
import os
from subprocess import Popen

dbg = True

CONFIG_FILE='bt-devices'
SQUEEZE_LITE='/usr/bin/squeezelite'
CHECKER='%s/check-squeezelite' % os.path.dirname(os.path.realpath(__file__))
DEVNULL = open(os.devnull, 'w')

players={}
def debug(*args):
    if dbg == True:
        print(*args)

numPlayers=0
checker=None
def controlChecker(val):
    global numPlayers
    global checker
    numPlayers += val 
    if 0==numPlayers and checker is not None:
        checker.kill()
        os.waitpid(checker.pid, 0)
        checker=None
    elif 1==numPlayers and checker is None:
        checker=Popen([CHECKER], stdout=DEVNULL, stderr=DEVNULL, shell=False)


def connected(hci, dev, name):
    key=dev.replace(':', '_')
    if key in players:
        return

    debug("Connected %s" % name,hci,dev)
    players[key] = Popen([SQUEEZE_LITE, '-o', 'bluealsa:DEV=%s,PROFILE=a2dp' % (dev), '-n', name, '-m', dev, '-M', 'SqueezeLiteBT', '-f', '/dev/null'], stdout=DEVNULL, stderr=DEVNULL, shell=False)
    controlChecker(1)

def disconnected(dev, name):
    key=dev.replace(':', '_')
    if key not in players:
        return

    debug("Disconnected %s" % name,dev)
    players[key].kill()
    os.waitpid(players[key].pid, 0)
    players.pop(key)
    controlChecker(-1)

def getName(dev):
    with open(CONFIG_FILE) as f:
        for line in f:
            parts=line.strip().split('=')
            if 2==len(parts) and dev==parts[0]:
                return parts[1] 
    return None

def bluealsa_handler(path, *args, **kwargs):
    """Catch all handler.
    Catch and debug information about all signals.
    """ 
    dbus_interface = kwargs['dbus_interface']
    member = kwargs['member']
    dev = None
    hci = None
    if path:
        parts=path.split('/')
        if len(parts)>=4:
            hci=parts[3]
            dev=":".join(parts[4].split('_')[1:])

    name = None
    if None!=dev and None!=hci:
        name = getName(dev)

    if None==name:
        debug("Unknown device") 
    else:
        if member == "PCMRemoved" :
            disconnected(dev, name)
        elif member == "PCMAdded" :
            connected(hci, dev, name)


def catchall_handler(name, attr, *args, **kwargs):
    """Catch all handler.
    Catch and debug information about all signals.
    """
    if name != "org.bluez.MediaControl1" :
        return
    dev = None
    hci = None
    if 'path' in kwargs:
        parts=kwargs['path'].split('/')
        if len(parts)>=4:
            hci=parts[3]
            dev=":".join(parts[4].split('_')[1:])

    name = None
    if None!=dev and None!=hci:
        name = getName(dev)

    if None==name:
        debug("Unknown device")
    else:
        # kwargs['member']='InterfacesRemoved' / 'InterfacesAdded'
        if attr["Connected"] == 0 :
            disconnected(dev, name)
        elif attr["Connected"] == 1 :
            connected(hci, dev, name)


if __name__ == '__main__':
    dbus.mainloop.glib.DBusGMainLoop(set_as_default=True)

    bus = dbus.SystemBus()
    #bus.add_signal_receiver(bluealsa_handler, dbus_interface="org.bluealsa.Manager1", interface_keyword='dbus_interface', member_keyword='member')
    bus.add_signal_receiver(catchall_handler, bus_name="org.bluez", interface_keyword='dbus_interface', member_keyword='member', path_keyword='path')


    #mainloop = gobject.MainLoop()
    mainloop = glib.MainLoop()
    mainloop.run()
