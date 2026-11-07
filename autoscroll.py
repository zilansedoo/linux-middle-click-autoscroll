#!/usr/bin/env python3
import os
import time
import threading
from evdev import InputDevice, UInput, ecodes as e, list_devices

DEADZONE = 15        # pixels: no scrolling inside this distance
SPEED = 9.6          # hi-res units per pixel per second (120 = 1 line)
CLAMP = 400          # maximum virtual distance
MOVE_START = 8       # pixels: moving this far while holding the middle button starts autoscroll
PASS_TIMEOUT = 0.5   # seconds: holding the button this long without moving passes it through as a normal press
TRIGGER = e.BTN_MIDDLE
STATE = '/run/autoscroll-state'


def set_state(v):
    try:
        with open(STATE, 'w') as f:
            f.write(v)
        os.chmod(STATE, 0o644)
    except Exception:
        pass


class Handler:
    # states:
    #   idle        - nothing happening
    #   pending     - middle button is down, not decided yet (click or autoscroll)
    #   active      - autoscroll running, middle button still held
    #   sticky      - autoscroll running, middle button released (any click stops it)
    #   passthrough - middle button is held as a normal button press
    def __init__(self, dev):
        caps = dev.capabilities()
        caps.pop(e.EV_SYN, None)
        rel = list(caps.get(e.EV_REL, []))
        for c in (e.REL_WHEEL, e.REL_WHEEL_HI_RES):
            if c not in rel:
                rel.append(c)
        caps[e.EV_REL] = rel
        self.dev = dev
        self.ui = UInput(caps, name="autoscroll-" + dev.name)
        self.lock = threading.Lock()
        self.state = 'idle'
        self.off = 0
        self.dist = 0
        self.t0 = 0.0
        self.hacc = 0.0
        self.wacc = 0
        self.swallow = set()

    def emit_key(self, code, value):
        self.ui.write(e.EV_KEY, code, value)
        self.ui.syn()

    def stop_scroll(self):
        self.state = 'idle'
        set_state('0')

    def scroller(self):
        dt = 0.01
        while True:
            time.sleep(dt)
            with self.lock:
                if self.state == 'pending' and time.time() - self.t0 > PASS_TIMEOUT:
                    self.emit_key(TRIGGER, 1)
                    self.state = 'passthrough'
                    continue
                if self.state not in ('active', 'sticky'):
                    continue
                d = abs(self.off) - DEADZONE
                if d <= 0:
                    continue
                direction = 1 if self.off > 0 else -1  # down = positive
                self.hacc += -direction * d * SPEED * dt
                n = int(self.hacc)
                if n == 0:
                    continue
                self.hacc -= n
                self.ui.write(e.EV_REL, e.REL_WHEEL_HI_RES, n)
                self.wacc += n
                w = int(self.wacc / 120)
                if w:
                    self.wacc -= w * 120
                    self.ui.write(e.EV_REL, e.REL_WHEEL, w)
                self.ui.syn()

    def handle(self, ev):
        with self.lock:
            if ev.type == e.EV_KEY:
                # swallow the rest of a click that was used to stop autoscroll
                if ev.code in self.swallow:
                    if ev.value == 0:
                        self.swallow.discard(ev.code)
                    return

                # any click stops a running (sticky) autoscroll
                if self.state == 'sticky' and ev.value == 1 \
                        and ev.code in (TRIGGER, e.BTN_LEFT, e.BTN_RIGHT):
                    self.stop_scroll()
                    self.swallow.add(ev.code)
                    return

                if ev.code == TRIGGER:
                    if ev.value == 1:
                        if self.state == 'idle':
                            self.state = 'pending'
                            self.t0 = time.time()
                            self.dist = 0
                            self.off = 0
                            self.hacc, self.wacc = 0.0, 0
                    elif ev.value == 0:
                        if self.state == 'pending':
                            # no movement: this was a normal middle click
                            self.emit_key(TRIGGER, 1)
                            self.emit_key(TRIGGER, 0)
                            self.state = 'idle'
                        elif self.state == 'passthrough':
                            self.emit_key(TRIGGER, 0)
                            self.state = 'idle'
                        elif self.state == 'active':
                            # button released: keep scrolling until the next click
                            self.state = 'sticky'
                    return

            if ev.type == e.EV_REL and ev.code in (e.REL_X, e.REL_Y) \
                    and self.state in ('pending', 'active', 'sticky'):
                if ev.code == e.REL_Y:
                    self.off = max(-CLAMP, min(CLAMP, self.off + ev.value))
                if self.state == 'pending':
                    self.dist += abs(ev.value)
                    if self.dist >= MOVE_START:
                        self.state = 'active'
                        set_state('1')
            self.ui.write_event(ev)

    def run(self):
        self.dev.grab()
        threading.Thread(target=self.scroller, daemon=True).start()
        try:
            for ev in self.dev.read_loop():
                self.handle(ev)
        finally:
            try:
                self.dev.ungrab()
            except Exception:
                pass


def is_mouse(dev):
    caps = dev.capabilities()
    rel = caps.get(e.EV_REL, [])
    keys = caps.get(e.EV_KEY, [])
    return (e.REL_X in rel and e.REL_Y in rel and e.BTN_MIDDLE in keys
            and not dev.name.startswith("autoscroll-"))


if __name__ == "__main__":
    set_state('0')
    mice = [d for d in map(InputDevice, list_devices()) if is_mouse(d)]
    if not mice:
        raise SystemExit("No mouse found")
    threads = [threading.Thread(target=Handler(d).run) for d in mice]
    for t in threads:
        t.start()
    for t in threads:
        t.join()
