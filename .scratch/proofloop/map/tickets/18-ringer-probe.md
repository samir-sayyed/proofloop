# Which read-only device queries report ringer mode and DND?

**Type:** research
**Assignee:** agent
**Blocked by:** None
**Status:** closed

## Question

On the pinned emulator image, which read-only adb queries reliably report ringer mode (silent, vibrate, normal) and do-not-disturb state, how fast they reflect a change, and do they need any permission? These become the fixed device-state probe set for criterion 2.

## Resolution

proofloop/device.py probe(): ringer mode from 'dumpsys audio' (mode internal), 'settings get global zen_mode', 'settings get system volume_ring_speaker'. No permission needed. Quiet = DND on, ringer not NORMAL, or ring volume 0. Reflected the start and end changes within about 1 s.
