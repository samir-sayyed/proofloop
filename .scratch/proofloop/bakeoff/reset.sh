#!/bin/zsh
# Environment-manager reset for Quiet Hours: clear app data, wait until the old task is gone, grant notifications.
# Launching while the clear-data task removal is still pending kills the new process (blank screen, "failed to attach").
a() { ~/Library/Android/sdk/platform-tools/adb -s ${DEVICE:-emulator-5554} "$@"; }
P=com.sam.quiethours
a shell pm clear $P >/dev/null
for k in {1..40}; do
  a shell dumpsys activity activities | grep -q "$P/" || break
  sleep 0.25
done
a shell dumpsys activity activities | grep -q "$P/" && { echo "reset: task still present after 10 s" >&2; exit 1; }
sleep 0.5
# Pinned clock: Wed 18 Nov 2026 08:00 IST unless PIN_TIME_MS is set. Shell can set it via the alarm service, no root needed.
a shell settings put global auto_time 0
a shell settings put global auto_time_zone 0
a shell cmd alarm set-timezone ${PIN_TZ:-Asia/Kolkata}
a shell cmd alarm set-time ${PIN_TIME_MS:-1794969000000}
a shell pm grant $P android.permission.POST_NOTIFICATIONS
