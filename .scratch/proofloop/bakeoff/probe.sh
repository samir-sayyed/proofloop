#!/bin/zsh
# Read-only device-state probe: ringer mode, do-not-disturb, speaker ring volume, device time.
a() { ~/Library/Android/sdk/platform-tools/adb -s ${DEVICE:-emulator-5554} "$@"; }
r=$(a shell dumpsys audio | grep -m1 "mode (internal)" | sed 's/.*= //' | tr -d '\r')
z=$(a shell settings get global zen_mode | tr -d '\r')
v=$(a shell settings get system volume_ring_speaker | tr -d '\r')
t=$(a shell date +%H:%M:%S | tr -d '\r')
state=normal; [[ "$r" != NORMAL || "$z" != 0 || "$v" == 0 ]] && state=quiet
echo "time=$t ringer=$r zen=$z ring=$v state=$state"
