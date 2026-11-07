# Autoscroll removal commands
# You can type them one by one, or run the whole file with: bash uninstall.sh

sudo systemctl disable --now autoscroll.service
sudo rm /etc/systemd/system/autoscroll.service
sudo rm /usr/local/bin/autoscroll.py
sudo rm /etc/modules-load.d/uinput.conf
sudo systemctl daemon-reload
