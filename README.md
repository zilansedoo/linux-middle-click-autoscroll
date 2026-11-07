# Autoscroll for Linux

Middle-click autoscroll for Linux, just like on Windows.

Click the middle mouse button (the scroll wheel), then move the mouse up or down. The page scrolls by itself. The farther you move the mouse, the faster it scrolls. It works in every app, not only in browsers, and it works on both X11 and Wayland.

> Tested on Ubuntu 24.04.

## Installation

### Step 1: Open a terminal

Press `Ctrl + Alt + T` on your keyboard.

A window will open. This is the terminal. You will type the commands below into it. After each command, press `Enter`.

### Step 2: Download the required package

```bash
sudo apt update
sudo apt install -y python3-evdev
```

If the terminal asks for your password, type it and press `Enter`. You will not see any characters while you type. This is normal.

### Step 3: Open the file

This command creates a new empty file and opens it in a text editor called nano:

```bash
sudo nano /usr/local/bin/autoscroll.py
```

### Step 4: Paste the Python code

1. Open the `autoscroll.py` file in this repository and copy all of the code.
2. Go back to the terminal. The nano editor should be open and empty.
3. Paste the code with `Ctrl + Shift + V`.

> In the terminal, `Ctrl + V` does not paste. You must use `Ctrl + Shift + V`.

### Step 5: Save the file

Press these keys in this order:

1. `Ctrl + O` (save)
2. `Enter` (confirm the file name)
3. `Ctrl + X` (close nano)

### Step 6: Run it

First, make the file executable:

```bash
sudo chmod +x /usr/local/bin/autoscroll.py
```

Next, create the service file. Copy the **whole** block below, from the first line to the `EOF` line, and paste it into the terminal:

```bash
sudo tee /etc/systemd/system/autoscroll.service > /dev/null << 'EOF'
[Unit]
Description=Global middle-click autoscroll

[Service]
ExecStart=/usr/bin/python3 /usr/local/bin/autoscroll.py
Restart=always
RestartSec=2

[Install]
WantedBy=multi-user.target
EOF
```

Then load the `uinput` module. The program needs it to create the scroll movements:

```bash
sudo modprobe uinput
```

Finally, start the service:

```bash
sudo systemctl daemon-reload
sudo systemctl start autoscroll
```

Check that it is running:

```bash
systemctl status autoscroll
```

If you see a green **`active (running)`** line, it works. Press `q` to leave this screen. Now press the middle mouse button and move the mouse up or down to try it.

### Step 7: Make it run all the time

The commands above only start Autoscroll for now. To start it automatically every time you turn on your computer, run:

```bash
echo uinput | sudo tee /etc/modules-load.d/uinput.conf
sudo systemctl enable autoscroll.service
```

That's it. You only need to install it once.

## How to use

- **Short click on the middle button:** Autoscroll starts. Move the mouse up or down to scroll.
- **Click any button (left, right or middle):** Autoscroll stops.
- **Hold the middle button, move the mouse, then release:** it scrolls while you hold and stops when you release.

While this program is running, the middle button no longer pastes text or opens links in a new tab. This is the same as on Windows.

## Troubleshooting

### If something goes wrong

Restart the service and check the status:

```bash
sudo systemctl restart autoscroll
systemctl status autoscroll
```

If you see `active (running)`, everything is fine. Try the middle button and move the mouse up and down.

If you see `failed`, check the code and read the log to find the reason:

```bash
python3 -c "import ast; ast.parse(open('/usr/local/bin/autoscroll.py').read()); print('script ok')"
journalctl -u autoscroll -n 30 --no-pager
```

If the first command does not print `script ok`, the code was not pasted correctly. Go back to Step 3 and paste the full code again.

### A possible fix: create the service file again

Sometimes the service file is saved wrongly (for example, extra text gets pasted into it). Create it again with this command:

```bash
sudo tee /etc/systemd/system/autoscroll.service > /dev/null << 'EOF'
[Unit]
Description=Global middle-click autoscroll

[Service]
ExecStart=/usr/bin/python3 /usr/local/bin/autoscroll.py
Restart=always
RestartSec=2

[Install]
WantedBy=multi-user.target
EOF
```

Check the Python file again:

```bash
python3 -c "import ast; ast.parse(open('/usr/local/bin/autoscroll.py').read()); print('script ok')"
```

Then run the service again:

```bash
sudo systemctl daemon-reload
sudo systemctl enable --now autoscroll.service
systemctl status autoscroll
```

### Still not working?

Open an issue in this repository and paste the output of this command:

```bash
journalctl -u autoscroll -n 30 --no-pager
```

## Uninstall

```bash
sudo systemctl disable --now autoscroll.service
sudo rm /etc/systemd/system/autoscroll.service
sudo rm /usr/local/bin/autoscroll.py
sudo rm /etc/modules-load.d/uinput.conf
sudo systemctl daemon-reload
```
