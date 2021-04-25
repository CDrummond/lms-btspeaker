#!/usr/bin/python3 -u

# Modified from code at https://github.com/oweitman/squeezelite-bluetooth

from __future__ import absolute_import, print_function, unicode_literals

from gi.repository import GLib

import dbus
import dbus.mainloop.glib
import evdev
import json
import os
import re
import requests
import sys
from subprocess import Popen

dbg = True

CONFIG_FILE = 'bt-devices'
SQUEEZE_LITE = '/usr/bin/squeezelite'
CHECKER = '%s/check-squeezelite' % os.path.dirname(os.path.realpath(__file__))
DEVNULL = open(os.devnull, 'w')
LMS = 'localhost' if len(sys.argv)<2 else sys.argv[1]

players={}
def debug(*args):
    if dbg == True:
        print(*args)

# CPU usage checking...................
CPU_CHECK_TIMEOUT=30000
MAX_CPU_USAGE=70
numPlayers=0
checker=None

def checkPlayersCpuUsage():
    global numPlayers
    global checker
    if numPlayers>0:
        pidlist="-p"
        playerMap={}
        for key in players:
            pidlist+=players[key]['squeeze'].pid+','
            playerMap[''+players[key]['squeeze'].pid]=key
        pidlist=pidlist[:-1]

        result = subprocess.run(['ps', '-o', 'pid,pcpu', pidlist], stdout=subprocess.PIPE)
        for line in result.stdout.decode('utf-8').splitlines():
            if '%CPU' not in line: # Ignore header...
                parts = re.sub(' {2,}', ' ', line.strip()).split(' ')
                if len(parts)>=2 and float(parts[1])>MAX_CPU_USAGE:
                    debug('%d is taking too much CPU (%f%%)' % (parts[1], parts[2]))
                    key = playerMap[parts[0]]
                    dbusPath = players[key]['path']

                    # Kill squeezelite instance
                    players[key]['squeeze'].kill()
                    os.waitpid(players[key]['squeeze'].pid, 0)

                    # Disconnect input monitoring
                    closeInput(key)
                    players.pop(key)

                    # Disconnect DBUS instance
                    bus = dbus.SystemBus()
                    service = bus.get_object('org.bluez', dbusPath)
                    iface = dbus.Interface(service, 'org.bluez.Device1')
                    iface.Disconnect()

                    numPlayers -= 1

        if numPlayers>0:
            checker = GLib.timeout_add(CPU_CHECK_TIMEOUT, checkPlayersCpuUsage)
    else:
        checker = None


def controlChecker(val):
    global numPlayers
    global checker
    numPlayers += val
    if checker is None and numPlayers>0:
        checker = GLib.timeout_add(CPU_CHECK_TIMEOUT, checkPlayersCpuUsage)
# .....................................


# Input handling.......................
DEV_DIR = '/dev/input'
MAC_RE = re.compile('^([0-9A-F]{2}:){5}([0-9A-F]{2})$')

deviceCheckTimeout = None

def sendCommand(mac, cmd):
    url = 'http://%s:9000/jsonrpc.js' % LMS
    debug('Send %s to %s @ %s' % (str(cmd), mac.lower(), url))
    try:
        req = requests.post(url, json={'id':1, 'method':'slim.request', 'params': [mac.lower(), cmd]})
        res = req.json()['result']
        debug('Resp: %s' % str(res))
        return res
    except Exception as e:
        debug("EX:%s" % str(e))


def getDevices():
    devices={}
    for dev in list(map(evdev.device.InputDevice, evdev.util.list_devices(DEV_DIR))):
        if dev.path is not None and dev.name is not None and MAC_RE.match(dev.name):
            devices[dev.name.replace(':', '_')]=dev
    return devices


def handleInput(event, dev):
    if (event.type in evdev.events.event_factory and evdev.events.event_factory[event.type] is evdev.events.KeyEvent):
        keyEvent = evdev.events.KeyEvent(event)
        if (keyEvent.keystate==evdev.events.KeyEvent.key_up):
            if keyEvent.scancode in [evdev.ecodes.KEY_PLAYCD, evdev.ecodes.KEY_PLAY, evdev.ecodes.KEY_PLAYPAUSE, evdev.ecodes.KEY_PAUSE, evdev.ecodes.KEY_PAUSECD]:
                resp = sendCommand(dev.name, ['mode', '?'])
                if '_mode' in resp and resp['_mode']=='play':
                    sendCommand(dev.name, ['pause'])
                else:
                    sendCommand(dev.name, ['play'])
            elif keyEvent.scancode in [evdev.ecodes.KEY_STOP, evdev.ecodes.KEY_STOPCD]:
                sendCommand(dev.name, ['stop'])
            elif keyEvent.scancode == evdev.ecodes.KEY_NEXTSONG:
                sendCommand(dev.name, ['playlist', 'index', '+1'])
            elif keyEvent.scancode == evdev.ecodes.KEY_PREVIOUSSONG:
                sendCommand(dev.name, ['button', 'jump_rew'])
            else:
                debug("Unhandled: %d" % keyEvent.scancode)


def inputCallback(source, condition, dev):
    #debug("inputCallback %s" % str(dev))
    try:
        event = dev.read_one()
        while (event):
            handleInput(event, dev)
            event = dev.read_one()
    except IOError:
        # The device has no more data or the handle has been closed
        pass
    return True


def openInputDev(key, dev):
    debug("Open %s for %s" % (dev.path, key))
    players[key]['input']['dev']=dev
    players[key]['input']['watch']=GLib.io_add_watch(dev.fd, GLib.IO_IN, inputCallback, dev)


def openInputs():
    global deviceCheckTimeout
    deviceCheckTimeout = None
    for key in players:
        if players[key]['input']['dev'] is None:
            openInput(key)


def openInput(key):
    global deviceCheckTimeout
    devices = getDevices()
    players[key]['input']['checks']+=1
    if key in devices:
        openInputDev(key, devices[key])
    elif deviceCheckTimeout is None and players[key]['input']['checks']<10:
        debug("No dev for %s, check in 2s" % (key))
        deviceCheckTimeout = GLib.timeout_add(2000, openInputs)


def closeInput(key):
    if players[key]['input']['dev'] is not None:
        players[key]['input']['dev'].close()
        GLib.source_remove(players[key]['input']['watch'])
    players[key]['input']={'checks':0, 'dev':None, 'watch': None}
#......................................

def connected(hci, dev, name, path):
    key=dev.replace(':', '_')
    if key in players:
        return

    debug("Connected %s" % name,hci,dev)
    players[key] = {'squeeze':Popen([SQUEEZE_LITE, '-s', LMS, '-o', 'bluealsa:DEV=%s,PROFILE=a2dp' % (dev), '-n', name, '-m', dev, '-M', 'SqueezeLiteBT', '-f', '/dev/null'], stdout=DEVNULL, stderr=DEVNULL, shell=False), 'input':{'checks':0, 'dev':None, 'watch': None}, 'path':path}
    openInput(key)
    controlChecker(1)


def disconnected(dev, name):
    key=dev.replace(':', '_')
    if key not in players:
        return

    debug("Disconnected %s" % name,dev)
    players[key]['squeeze'].kill()
    os.waitpid(players[key]['squeeze'].pid, 0)
    closeInput(key)
    players.pop(key)
    controlChecker(-1)


def getName(dev):
    with open(CONFIG_FILE) as f:
        for line in f:
            parts=line.strip().split('=')
            if 2==len(parts) and dev==parts[0]:
                return parts[1] 
    return None


def catchallHandler(name, attr, *args, **kwargs):
    """Catch all handler.
    Catch and debug information about all signals.
    """
    if name == "org.bluez.MediaControl1" :
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
                connected(hci, dev, name, klwargs['path'])
    elif name == "org.bluez.Device1" and 'member' in kwargs and 'path' in kwargs and kwargs['member']=='PropertiesChanged' and 'Connected' in attr and attr['Connected'] == 1:
        parts=kwargs['path'].split('/')
        if len(parts)>=4:
            key="_".join(parts[4].split('_')[1:])
            if not key in players:
                debug('Call Connect for %s' % key)
                bus = dbus.SystemBus()
                service = bus.get_object('org.bluez', kwargs['path'])
                iface = dbus.Interface(service, name)
                iface.Connect()


if __name__ == '__main__':
    dbus.mainloop.glib.DBusGMainLoop(set_as_default=True)

    bus = dbus.SystemBus()
    bus.add_signal_receiver(catchallHandler, bus_name="org.bluez", interface_keyword='dbus_interface', member_keyword='member', path_keyword='path')

    mainloop = GLib.MainLoop()
    mainloop.run()
