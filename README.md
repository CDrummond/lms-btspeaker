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

1. Copy `btspeaker-monitor.py`, `bt-devices`, and `check-squeezelite` to `/usr/local/bluetooth`
2. `chmod +x /usr/local/bluetooth/btspeaker-monitor.py /usr/local/bluetooth/check-squeezelite`
2. Edit `bt-devices` to set LMS player name for a BT devices MAC address
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
5. `sudo daemon-reload`
6. `sudo systemctl enable btspeaker-monitor`
7. `sudo systemctl restart btspeaker-monitor`

