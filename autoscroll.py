#!/usr/bin/env python3
import os
import time
import threading
from evdev import InputDevice, UInput, ecodes as e, list_devices

DEADZONE = 15      # pixels: no scrolling inside this distance
SPEED = 9.6        # hi-res units per pixel per second (120 = 1 line)
CLAMP = 400        # maximum virtual distance
HOLD_EXIT = 0.35   # seconds: if middle button is held longer than this, mode ends on release
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
        self.active = False
        self.off = 0
        self.t0 = 0.0
        self.swallow = set()
        self.hacc = 0.0
        self.wacc = 0

    def start(self):
        self.active, self.off, self.t0 = True, 0, time.time()
        self.hacc, self.wacc = 0.0, 0
        set_state('1')

    def stop(self):
        self.active = False
        set_state('0')

    def scroller(self):
        dt = 0.01
        while True:
            time.sleep(dt)
            with self.lock:
                if not self.active:
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
                if ev.code == TRIGGER:
                    if ev.value == 1:
                        if self.active:
                            self.stop()
                            self.swallow.add(ev.code)
                        else:
                            self.start()
                    elif ev.value == 0:
                        if ev.code in self.swallow:
                            self.swallow.discard(ev.code)
                        elif self.active and time.time() - self.t0 > HOLD_EXIT:
                            self.stop()
                    return
                if ev.code in (e.BTN_LEFT, e.BTN_RIGHT):
                    if ev.value == 1 and self.active:
                        self.stop()
                        self.swallow.add(ev.code)
                        return
                    if ev.value == 0 and ev.code in self.swallow:
                        self.swallow.discard(ev.code)
                        return
            if self.active and ev.type == e.EV_REL and ev.code == e.REL_Y:
                self.off = max(-CLAMP, min(CLAMP, self.off + ev.value))
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
