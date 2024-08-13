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
echo "00 21 * * * /Users/admin/Desktop/quit_voice_array.sh" >> mycron

# these lines shutdown the voice array app and restart it one minute later
echo "00 11 * * * /Users/admin/Desktop/quit_voice_array.sh" >> mycron
echo "01 11 * * * /Users/admin/Desktop/focus_voice_array.sh" >> mycron
echo "00 14 * * * /Users/admin/Desktop/quit_voice_array.sh" >> mycron
echo "01 14 * * * /Users/admin/Desktop/focus_voice_array.sh" >> mycron
echo "00 17 * * * /Users/admin/Desktop/quit_voice_array.sh" >> mycron
echo "01 17 * * * /Users/admin/Desktop/focus_voice_array.sh" >> mycron
echo "40 19 * * * /Users/admin/Desktop/quit_voice_array.sh" >> mycron
echo "41 19 * * * /Users/admin/Desktop/focus_voice_array.sh" >> mycron

# this line ensures that the voice array application is on top, it runs every hour at 5, 20, and 35 minutes past
echo "05 * * * * /Users/admin/Desktop/focus_voice_array.sh" >> mycron
echo "20 * * * * /Users/admin/Desktop/focus_voice_array.sh" >> mycron
echo "35 * * * * /Users/admin/Desktop/focus_voice_array.sh" >> mycron



# install new cron file
crontab mycron
rm mycron

echo "\n\ncrontab is setup to quit application at: "

# write out current crontab to check
crontab -l

# we're pretty
echo "\n\nemail: lauria@antimodular.com with questions\n\n"
