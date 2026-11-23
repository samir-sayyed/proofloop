#!/bin/zsh
# usage: score-trial.sh WORKDIR PREFIX CRITERION  (e.g. A "text")   run after the author is done
# Proves the flow: check, 3 clean runs on the good build, bug next-skips-today must fail at PREFIX2.
set -e
W=$1; P=$2; CRIT=$3; REPO=${0:A:h:h:h}; A=$REPO/.scratch/proofloop/apks
mkdir -p $W/score; cp $W/flow.yaml $W/score/flow.yaml; cp $W/map.md $W/app-map.md
cat > $W/score/task.json <<EOT
{"name": "qh-loop/$(basename $W)", "criterion": "$CRIT", "app_id": "com.sam.quiethours",
 "approved_by": "experiment brief (experiments/quiet-hours-loop)",
 "good": "$A/good-e4ba3eb.apk",
 "bugs": [{"name": "next-skips-today", "apk": "$A/bug-next-skips-today-e4ba3eb.apk", "role": "proof", "expect": "${P}2"}],
 "device": {"timezone": "Asia/Kolkata", "clock": "2026-11-18T08:00:00", "grants": ["android.permission.POST_NOTIFICATIONS"]},
 "good_runs": 3, "budget_minutes": 30, "steps": [{"flow": "flow.yaml"}]}
EOT
cd $REPO
# Standing approval for scoring: the experimenter approved the brief, which fixes the checkpoint the bug must
# fail at; the plan is the author's own checkpoint markers. Labelled as such in approved_by, never as a review.
grep -E '^# *checkpoint:' $W/score/flow.yaml | sed -E 's/^# *checkpoint: */- /' > $W/score/plan.md
python3 -m proofloop.cli approve $W/score/task.json --by "standing approval, experiments/quiet-hours-loop brief: the proof bug must fail at ${P}2; plan from author markers" >/dev/null
python3 -m proofloop.cli check $W/score/task.json | tail -3
python3 -m proofloop.cli prove $W/score/task.json --runs 3 --out $W/score/out | grep -E 'Verdict|Good build|^\| next' | cut -c1-130
echo "maestro calls: hierarchy=$(grep -c hierarchy $W/maestro.log) test=$(grep -c ' test' $W/maestro.log) all=$(wc -l < $W/maestro.log | tr -d ' ')"
