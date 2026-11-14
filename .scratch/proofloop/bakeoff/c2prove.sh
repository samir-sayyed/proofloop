#!/bin/zsh
# Criterion 2 proof: a Silent schedule restores normal sound at its end time.
# E1: at 16:59:30 sound is quiet and status reads "Active until 5:00 PM". E2: by 17:01:00 sound is normal and status reads "Next: Tomorrow 9:00 AM".
export MAESTRO_CLI_NO_ANALYTICS=1 MAESTRO_CLI_ANALYSIS_NOTIFICATION_DISABLED=true
cd ${0:A:h}; APK=../apks; a() { ~/Library/Android/sdk/platform-tools/adb -s emulator-5554 "$@"; }
now() { a shell date +%H%M%S | tr -d '\r'; }
until_time() { while (( $(now) < $1 )); do sleep 1; done; }
flow() { maestro --device emulator-5554 test $1 --test-output-dir=out/c2-$build-$n-${1%.yaml} >/dev/null 2>&1; }
run() { build=$1; n=$2; s=$SECONDS; r="$build | run $n"
  ./reset.sh || { echo "$r | FAIL | setup: reset"; return; }
  a shell cmd notification allow_dnd com.sam.quiethours; ./settime.sh 08:58:00
  flow c2-setup.yaml || { echo "$r | FAIL | setup: create schedule"; return; }
  ./settime.sh 08:59:55; ok=0
  for k in {1..20}; do ./probe.sh | grep -q state=quiet && { ok=1; break; }; sleep 1; done
  (( ok )) || { echo "$r | FAIL | setup: start never silenced | $(./probe.sh)"; return; }
  ./settime.sh 16:59:15; until_time 165930
  p=$(./probe.sh); [[ $p == *state=quiet* ]] || { echo "$r | FAIL | E1 sound | $p"; return; }
  flow ${ACTIVE_FLOW:-c2-active.yaml} || { echo "$r | FAIL | E1 status | $(./probe.sh)"; return; }
  until_time 170000; ok=0
  while (( $(now) < 170100 )); do ./probe.sh | grep -q state=normal && { ok=1; break; }; sleep 2; done
  p=$(./probe.sh); (( ok )) || { echo "$r | FAIL | E2 sound | $p"; return; }
  flow ${ENDED_FLOW:-c2-ended.yaml} || { echo "$r | FAIL | E2 status | $p"; return; }
  echo "$r | PASS | $((SECONDS-s))s | restored: $p"; }
builds=(${=BUILDS:-good:10 bug-end-hour-late:1 bug-end-5min-early:1})
for spec in $builds; do b=${spec%%:*}; c=${spec##*:}
  apk=$b; [[ $b == good ]] && apk=good-5.3.2
  a install -r $APK/$apk.apk >/dev/null; for i in {1..$c}; do run $b $i; done; done
a install -r $APK/good-5.3.2.apk >/dev/null; a shell settings put global auto_time 1; a shell settings put global auto_time_zone 1
