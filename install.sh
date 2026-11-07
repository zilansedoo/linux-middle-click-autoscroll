# Autoscroll installation commands
# Run these from inside the project folder.
# You can type them one by one, or run the whole file with: bash install.sh

# 1) Install the dependency
sudo apt update
sudo apt install -y python3-evdev

# 2) Copy the script and the service file to the system
sudo cp autoscroll.py /usr/local/bin/autoscroll.py
sudo chmod +x /usr/local/bin/autoscroll.py
sudo cp autoscroll.service /etc/systemd/system/autoscroll.service

# 3) Load the uinput module now and on every boot
echo uinput | sudo tee /etc/modules-load.d/uinput.conf
sudo modprobe uinput

# 4) Start the service and enable it at boot
sudo systemctl daemon-reload
sudo systemctl enable --now autoscroll.service

# 5) Check that it is running (you should see: active (running))
systemctl status autoscroll
