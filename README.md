Introduction
============

Simple script to launch a squeezlite instance for each connected, and
configured, BT device.

Code is forked/modified from https://github.com/oweitman/squeezelite-bluetooth/

Prev/next and play/pause buttons on speakers are forwarded to LMS. Pass
hostname/IP address of server as 1st argument to `btspeaker-monitor.py` - if
none passed 'localhost' is assumed.

Usage
=====

1. Copy `btspeaker-monitor.py` and`bt-devices`, to `/usr/local/bluetooth`
2. `chmod +x /usr/local/bluetooth/btspeaker-monitor.py`
2. Edit `bt-devices` to set LMS player name for a BT device's MAC address
3. Pair BT devices if not already
```
sudo bluetoothctl
[bluetooth]# scan on
...
[bluetooth]# scan off
[bluetooth]# pair 00:00:00:00:00:00
[bluetooth]# trust 00:00:00:00:00:00
[bluetooth]# connect 00:00:00:00:00:00
[bluetooth]# exit
```
4. Copy `btspeaker-monitor.service` to `/etc/systemd/system`
5. Edit `/etc/systemd/system/btspeaker-monitor.service` and add LMS location if
LMS is not running on same machine as this script. e.g.
```
ExecStart=/usr/local/bluetooth/bluetooth/btspeaker-monitor.py 192.168.0.22
```
6. `sudo daemon-reload`
7. `sudo systemctl enable btspeaker-monitor`
8. `sudo systemctl restart btspeaker-monitor`

