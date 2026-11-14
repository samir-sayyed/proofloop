#!/bin/zsh
# Build Sunflower (github.com/android/sunflower, Apache-2.0) good and seeded-bug debug APKs.
# Usage: build-apks.sh [SUNFLOWER_REPO] [OUT_DIR]. Leaves the repo unchanged.
set -e
REPO=${1:-${0:A:h}/../../.scratch/oss/sunflower}; OUT=${2:-${0:A:h}/../../.scratch/proofloop/apks}; BUGS=${0:A:h}/bugs
mkdir -p $OUT; cd $REPO
export JAVA_HOME=${JAVA_HOME_17:-/opt/homebrew/Cellar/openjdk@21/21.0.9/libexec/openjdk.jdk/Contents/Home}
trap 'git checkout -q -- .' EXIT
build() { ./gradlew -q :app:assembleDebug >/dev/null && cp app/build/outputs/apk/debug/app-debug.apk $OUT/$1.apk && echo "built $1"; }
build sunflower-good
for p in $BUGS/*.patch; do git apply $p && build sunflower-${p:t:r}; git checkout -q -- .; done
