#!/bin/zsh
# settime.sh HH:MM:SS -> set the emulator clock to that time on Wed 18 Nov 2026 IST.
ms=$(python3 -c "import datetime,zoneinfo,sys;h,m,s=map(int,sys.argv[1].split(':'));print(int(datetime.datetime(2026,11,18,h,m,s,tzinfo=zoneinfo.ZoneInfo('Asia/Kolkata')).timestamp()*1000))" $1)
~/Library/Android/sdk/platform-tools/adb -s ${DEVICE:-emulator-5554} shell cmd alarm set-time $ms
