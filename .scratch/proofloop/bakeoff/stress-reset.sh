#!/bin/zsh
# 40 cold launches with reset.sh; counts launches not displayed within 15 s.
cd ${0:A:h}; a() { ~/Library/Android/sdk/platform-tools/adb -s emulator-5554 "$@"; }; P=com.sam.quiethours; hang=0
for i in {1..40}; do
  ./reset.sh || { echo "launch $i reset failed"; continue; }
  a logcat -c; a shell am start -n $P/.MainActivity >/dev/null; ok=0
  for k in {1..30}; do a logcat -d -s ActivityTaskManager:I | grep -q "Displayed $P" && { ok=1; break; }; sleep 0.5; done
  (( ok )) || { hang=$((hang+1)); echo "launch $i HANG"; a logcat -d | grep -E "Killing [0-9]+:$P.*remove task"; }
done
echo "stress: $hang hangs in 40 launches"
