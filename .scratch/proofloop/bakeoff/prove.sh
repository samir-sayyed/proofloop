#!/bin/zsh
# Runs criterion1.yaml: 10x on the good build, then once per criterion-1 bug build.
# Prints one line per run: build, run, result, seconds, failing step, checkpoint.
export MAESTRO_CLI_NO_ANALYTICS=1 MAESTRO_CLI_ANALYSIS_NOTIFICATION_DISABLED=true
cd ${0:A:h}; APK=../apks; ADB=~/Library/Android/sdk/platform-tools/adb
cp_of() { case "$1" in
  *"Step 1 of 2"*) echo C1;; *'"Smoke"'*) echo C2;; *'"Weekdays" is visible'*) echo C3;; *"Next:"*) echo C4;; *) echo "setup/action";; esac; }
run() { build=$1; n=$2; s=$SECONDS
  ./reset.sh || { echo "$build | run $n | RESET FAILED"; return; }
  out=$(maestro --device emulator-5554 test criterion1.yaml --test-output-dir=out/$build-$n 2>&1)
  failed=$(print -r -- "$out" | grep -m1 "FAILED" | sed 's/\.\.\. FAILED//')
  if [[ -z "$failed" ]]; then echo "$build | run $n | PASS | $((SECONDS-s))s"; else echo "$build | run $n | FAIL | $((SECONDS-s))s | step: $failed | checkpoint: $(cp_of "$failed")"; fi; }
$ADB -s emulator-5554 install -r $APK/good-5.3.2.apk >/dev/null
for i in {1..10}; do run good $i; done
for b in bug-weekdays-off-by-one bug-next-skips-today; do $ADB -s emulator-5554 install -r $APK/$b.apk >/dev/null; run $b 1; done
$ADB -s emulator-5554 install -r $APK/good-5.3.2.apk >/dev/null
~/Library/Android/sdk/platform-tools/adb -s emulator-5554 shell settings put global auto_time 1
