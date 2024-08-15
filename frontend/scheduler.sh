echo "\n\n--- ANTIMODULAR SCHEDULER SCRIPT ---\n"

# edit the times below to adjust the shutdown and poweron times for the computer
sudo pmset repeat poweron MTWRFSU 08:00:00 shutdown MTWRFSU 00:00:00

echo "\ncomputer reset schedule: "

# display the current schedule
pmset -g sched

# remove old job
crontab -r

# echo new cron into cron file
#     mm hh * * *

# edit this line to match the shutdown time above in line 4
echo "@reboot sh /Users/admin/desktop/recognition-2024-1/frontend/startRecognition.sh" >> mycron

# install new cron file
crontab mycron
rm mycron

echo "\n\ncrontab is setup to quit application at: "

# write out current crontab to check
crontab -l

# we're pretty
echo "\n\nemail: lauria@antimodular.com with questions\n\n"
