#!/usr/bin/env python3
"""Writes every course and arena in this repository as the JSON document mg-wipeout reads.

    tools/build.py            # rewrite courses/*.json
    tools/build.py --check    # exit 1 if any file on disk differs from what this would write

WHY A BUILDER AND NOT HAND-WRITTEN JSON: a course is a few hundred numbers that depend on
each other. Moving one gap moves every piece after it, every checkpoint and every route point
a stand-in follows; written by hand that is forty edits and one of them missed. Here a course
is a sequence of SECTIONS on a cursor that runs down -Z from the start pad, and each section
places its pieces, its route points and its checkpoint together.

The JSON is still the truth the game reads, and is committed: a server installs documents, not
this script. `--check` is what CI runs, so a hand edit to a .json that this file does not know
about is caught rather than silently overwritten by the next build.

Every length is metres, every angle degrees, every time seconds. The movement these are sized
against is mg-wipeout's defaults: a 7 m/s run and a 1.25 m jump at 20 m/s^2, which clears about
4.9 m of flat gap at a run and rises onto about 1.1 m. A gap here is never over 3.4 m and a
step up never over 0.8 m, so every jump is made with room; what is hard is the timing.
"""

import json
import math
import os
import sys

ROOT = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "courses")
AUTHOR = "mg-wipeout"


def r(value):
    """Two decimals: the documents are read by people as well as by the game."""
    return round(float(value), 2)


def v(*values):
    return [r(x) for x in values]


class Course:
    """A course built forward from the start pad, one section at a time.

    The cursor is the FRONT edge of the last thing placed (`z`, decreasing as the course goes
    on), at height `y` (the top of the ground), on the line `x`.
    """

    def __init__(self, cid, name, blurb, theme, water=-6.0, seconds=0.0):
        self.doc = {
            "format": 1,
            "kind": "course",
            "id": cid,
            "name": name,
            "author": AUTHOR,
            "blurb": blurb,
            "theme": theme,
            "water_height": water,
            "start": {"at": [0, 0, 0], "size": [10, 8], "yaw": 0},
        }
        if seconds:
            self.doc["course_seconds"] = seconds
        self.pieces = []
        self.route = []
        self.checkpoints = []
        self.x = 0.0
        self.y = 0.0
        self.z = -4.0
        # The middle of the pad's front first: the pad is wider than the ground after it, and
        # somebody restarting at its side who ran straight at the next point went off the edge.
        self.point(-3.2, reach=1.0)

    # --- primitives -----------------------------------------------------------

    def add(self, **piece):
        for key, value in list(piece.items()):
            if isinstance(value, float):
                piece[key] = r(value)
        self.pieces.append(piece)
        return len(self.pieces) - 1

    def point(self, z, x=None, y=None, **flags):
        self.route.append({"at": v(self.x if x is None else x, self.y if y is None else y, z), **flags})

    def deck(self, length, width=6.0, role="deck", thick=1.0, x=None):
        """Ground from the cursor forward `length` metres, its top at the cursor's height."""
        cx = self.x if x is None else x
        self.add(kind="box", at=v(cx, self.y - thick / 2, self.z - length / 2),
                 size=v(width, thick, length), role=role)
        self.z -= length

    def gap(self, length, rise=0.0, dx=0.0):
        """A jump: a point just short of the edge that says jump, and the gap itself."""
        self.point(self.z + 0.5, jump=True, reach=0.55)
        self.z -= length
        self.y += rise
        self.x += dx

    def ahead(self, metres=1.0, **flags):
        """A route point `metres` onto whatever is placed next."""
        self.point(self.z - metres, **flags)

    def checkpoint(self, width=6.0):
        """A checkpoint across the ground just placed, a metre and a half back from its edge."""
        self.checkpoints.append({"at": v(self.x, self.y, self.z + 1.6), "size": v(width, 4.0, 2.4)})

    # --- sections -------------------------------------------------------------

    def run_out(self, length=8.0, width=6.0):
        self.deck(length, width)
        self.point(self.z + 1.5)

    def side_sweeper(self, length=14.0, width=6.0, speed=80.0, height=0.55, arms=2, phase=0.0):
        """A deck with a low arm swinging across it from a post at its side. Jump it.

        The arm reaches just short of the far edge, so the far edge is a place a careful runner
        can stand; and the deck is longer than the arm's sweep, so there is ground before it to
        watch it from.
        """
        z0 = self.z
        self.deck(length, width)
        hub_x = self.x + width / 2 + 0.6
        hub_z = z0 - length / 2
        arm = width + 0.4
        self.add(kind="spinner", at=v(hub_x, self.y, hub_z), arm_length=arm, arm_height=height,
                 arm_thickness=0.35, speed=speed, arms=arms, phase=phase)
        self.point(self.z + 1.2)

    def high_sweeper(self, length=14.0, width=6.0, speed=70.0, arms=2, phase=0.0):
        """An arm at head height, swinging across from a post at the side. Duck it.

        1.45 m up and 0.3 m thick: its underside is at 1.3 m, over a crouched player (0.9 m)
        and through a standing one (1.8 m). Running crouched is slow, which is the price.
        """
        z0 = self.z
        self.deck(length, width)
        hub_x = self.x + width / 2 + 0.6
        self.add(kind="spinner", at=v(hub_x, self.y, z0 - length / 2), arm_length=width + 0.4,
                 arm_height=1.45, arm_thickness=0.3, hub_height=2.2, speed=speed, arms=arms,
                 phase=phase)
        self.point(self.z + 1.2)

    def centre_spinner(self, size=11.0, speed=70.0, height=0.6, arms=2, phase=0.0):
        """A square deck with a post in the middle and arms round it; run round the post."""
        z0 = self.z
        self.deck(size, size)
        hub_z = z0 - size / 2
        arm = size / 2 - 0.3
        self.add(kind="spinner", at=v(self.x, self.y, hub_z), arm_length=arm, arm_height=height,
                 arm_thickness=0.35, speed=speed, arms=arms, phase=phase, hub_radius=0.6)
        # Round the post, hopping the arms: with three or four of them on a deck this size the
        # window to walk through untouched is too short to wait for.
        side = self.x - size / 2 + 2.2
        # Straight on first, then out to the side: a diagonal from the narrower ground before
        # cut across its corner and into the water.
        self.route.append({"at": v(self.x, self.y, z0 - 0.8)})
        self.route.append({"at": v(side, self.y, z0 - 2.2)})
        # And back to the middle well short of the far edge, so whatever comes next is run at
        # straight: back to the middle at the edge itself, the jump that follows went sideways.
        self.route.append({"at": v(side, self.y, self.z + 3.4)})
        self.route.append({"at": v(self.x, self.y, self.z + 1.6)})

    def balls(self, count=3, radius=1.5, spacing=4.0, first=3.4, last=2.6):
        """Big balls to hop across, top to top. Land on the top or slide off it.

        Under a running jump apart (4.0 of 4.9 m): a jump is cut short in the air by
        holding back, never stretched, so a top a full jump away is one any slower take-off
        falls short of.
        """
        lift = 0.4
        self.point(self.z + 0.6, jump=True, reach=0.55)
        z = self.z - first
        for i in range(count):
            self.add(kind="ball", at=v(self.x, self.y + lift - radius, z), radius=radius, role="hazard")
            self.route.append({"at": v(self.x, self.y + lift, z), "jump": True, "reach": 0.75})
            z -= spacing
        self.z = z + spacing - last
        self.point(self.z - 1.2)

    def mover_crossing(self, length=9.0, size=4.0, period=6.0, phase=0.0, dx=0.0):
        """A gap only a mover crosses: step on at one end, step off at the other."""
        near = self.z
        far = self.z - length
        start = v(self.x, self.y - 0.4, near - size / 2 - 0.3)
        end = v(self.x + dx, self.y - 0.4, far + size / 2 + 0.3)
        self.add(kind="mover", **{"from": start, "to": end}, size=v(size, 0.6, size), period=period,
                 phase=phase)
        # A point two metres back to wait at, then the mover's middle and the far side as
        # things to land on: a stand-in runs from the wait point and jumps at whichever edge it
        # reaches, and stays on the mover until the far side is in reach.
        self.point(near + 2.0, reach=0.6)
        self.route.append({"at": v(start[0], self.y, start[2]), "board": True, "ride": True,
                           "reach": 0.9})
        self.route.append({"at": v(self.x + dx, self.y, far - 1.4), "board": True, "reach": 0.9})
        self.z = far
        self.x += dx

    def turntable(self, radius=5.0, speed=35.0, spinner_speed=0.0):
        """A disc that turns. Across the middle is steady; the rim is a ride."""
        self.point(self.z + 0.6, jump=True, reach=0.55)
        centre_z = self.z - 1.4 - radius
        self.add(kind="turntable", at=v(self.x, self.y - 0.3, centre_z), radius=radius,
                 thickness=0.6, speed=speed)
        if spinner_speed:
            self.add(kind="spinner", at=v(self.x, self.y, centre_z), arm_length=radius - 0.2,
                     arm_height=0.6, speed=spinner_speed, arms=2, hub_radius=0.5)
            self.route.append({"at": v(self.x - 1.6, self.y, centre_z + radius - 1.2)})
            self.route.append({"at": v(self.x - 1.6, self.y, centre_z - radius + 1.2), "jump": True,
                               "reach": 0.6})
        else:
            self.route.append({"at": v(self.x, self.y, centre_z + radius - 1.0)})
            self.route.append({"at": v(self.x, self.y, centre_z - radius + 1.0), "jump": True,
                               "reach": 0.6})
        self.z = centre_z - radius - 1.4
        self.point(self.z - 1.2)

    def pusher_alley(self, width=2.6, count=3, period=2.6, reach=2.4, step=4.5, length=None):
        """A narrow walkway with rams that strike across it from alternate sides, a step apart.

        4.5 m apart, waited for 2.4 m short of each: at 3.5 m, somebody stopping for the next
        ram slid into its reach, and somebody waiting was in reach of the one behind.
        """
        z0 = self.z
        self.deck((count + 1) * step, width)
        for i in range(count):
            z = z0 - step * (i + 1)
            side = 1 if i % 2 == 0 else -1
            # The ram rests just off the walkway's edge and strikes across it.
            rest_x = self.x + side * (width / 2 + 0.9)
            self.add(kind="pusher", at=v(rest_x, self.y + 0.9, z), size=v(1.6, 1.6, 1.4),
                     yaw=90.0 if side > 0 else -90.0, reach=reach, period=period,
                     duty=0.35, phase=0.27 * i)
            self.add(kind="box", at=v(rest_x + side * 1.1, self.y + 0.8, z), size=v(0.6, 2.6, 2.0),
                     role="pillar")
            self.route.append({"at": v(self.x, self.y, z + 2.4), "wait": True, "reach": 0.7})
        self.route.append({"at": v(self.x, self.y, self.z + 1.0)})

    def pendulums(self, width=3.0, count=3, period=3.0, swing=55.0, step=4.2, length=None):
        """A beam with hammers swinging across it, a step apart, and room between them.

        The hammers are 4.2 m apart and somebody waiting for the next one waits half way
        between two: at 3.2 m the ball behind reached a person standing still in front of it.
        """
        z0 = self.z
        self.deck((count + 1) * step, width)
        for i in range(count):
            z = z0 - step * (i + 1)
            self.add(kind="pendulum", pivot=v(self.x, self.y + 6.2, z), length=5.0, radius=0.95,
                     swing=swing, period=period, phase=0.31 * i, yaw=0.0)
            self.route.append({"at": v(self.x, self.y, z + step / 2), "wait": True, "reach": 0.7})
        self.route.append({"at": v(self.x, self.y, self.z + 1.0)})

    def tiles(self, cols=3, rows=4, tile=2.0, period=3.2, down=0.28, seed=1):
        """A grid of tiles, each of which drops out on its own schedule and comes back."""
        gap = 0.3
        pitch = tile + gap
        depth = rows * pitch - gap
        self.point(self.z + 2.0, reach=0.6)
        z0 = self.z - 1.2
        centre_z = z0 - depth / 2
        self.add(kind="tiles", at=v(self.x, self.y - 0.25, centre_z), cols=cols, rows=rows,
                 tile=tile, gap=gap, thickness=0.5, period=period, down=down, seed=seed)
        for row in range(rows):
            z = z0 - tile / 2 - row * pitch
            self.route.append({"at": v(self.x, self.y, z), "board": True, "reach": 0.6})
        self.z = z0 - depth - 1.2
        self.point(self.z - 1.2, board=True)

    def rollers(self, count=3, radius=1.1, speed=70.0, length=6.0, spacing=3.7, first=3.4, last=2.6):
        """Logs across the way, rolling. Hop from top to top; stand still and go backwards.

        Spaced like the balls, a running jump apart: logs a stride apart were overshot.
        """
        self.point(self.z + 0.6, jump=True, reach=0.55)
        z = self.z - first
        for i in range(count):
            self.add(kind="roller", at=v(self.x, self.y - radius, z), length=length, radius=radius,
                     speed=speed if i % 2 == 0 else -speed)
            self.route.append({"at": v(self.x, self.y, z), "jump": True, "reach": 0.75})
            z -= spacing
        self.z = z + spacing - last
        self.point(self.z - 1.2)

    def seesaws(self, count=3, length=5.0, width=4.0, amplitude=14.0, period=4.0, gap=1.6):
        """Planks that tip on a slow cycle. Cross one while it is level."""
        for i in range(count):
            self.point(self.z + 0.5, jump=True, reach=0.55)
            self.z -= gap
            centre = self.z - length / 2
            self.add(kind="seesaw", at=v(self.x, self.y - 0.25, centre), size=v(width, 0.5, length),
                     amplitude=amplitude, period=period, phase=0.33 * i)
            self.route.append({"at": v(self.x, self.y, centre)})
            self.z -= length
        self.point(self.z - 1.2)

    def conveyor_climb(self, length=12.0, width=4.0, rise=2.0, speed=3.0):
        """A ramp with the belt running against you."""
        pitch = math.degrees(math.atan2(rise, length))
        slope = math.hypot(length, rise)
        centre = v(self.x, self.y + rise / 2 - 0.25 * math.cos(math.radians(pitch)), self.z - length / 2)
        self.add(kind="ramp", at=centre, size=v(width, 0.5, slope), pitch=pitch, role="pillar")
        # The belt lies ON the ramp: the same pitch, a few centimetres proud of it. A belt laid
        # flat at the ramp's middle height was a wall half way up it.
        self.add(kind="conveyor", at=v(self.x, self.y + rise / 2 + 0.03, self.z - length / 2),
                 size=v(width * 0.8, 0.06, slope * 0.95), speed=-speed, pitch=pitch)
        self.z -= length
        self.y += rise
        self.point(self.z + 0.6)

    def flat_belt(self, length=12.0, width=4.0, speed=3.5):
        """A flat belt running backwards: the run is slower than it looks."""
        z0 = self.z
        self.deck(length, width, role="pillar", thick=0.8)
        self.add(kind="conveyor", at=v(self.x, self.y + 0.03, z0 - length / 2),
                 size=v(width * 0.9, 0.06, length * 0.96), speed=-speed)
        self.point(self.z + 1.0)

    def bouncer_up(self, rise=3.5, power=13.0):
        """A pad that throws you up onto the next level."""
        self.add(kind="bouncer", at=v(self.x, self.y - 0.2, self.z - 1.4), size=v(2.4, 0.4, 2.4),
                 power=power)
        self.add(kind="box", at=v(self.x, self.y - 0.5, self.z - 1.4), size=v(3.2, 0.6, 3.2), role="pillar")
        self.point(self.z - 1.4, reach=0.5)
        self.z -= 2.6
        self.y += rise
        self.point(self.z - 1.4)

    def beam(self, length=10.0, width=1.0):
        """A narrow beam, run straight down its middle."""
        self.deck(length, width)
        self.point(self.z + 1.2)

    def finish(self, size=10.0):
        self.deck(size, size, role="safe")
        self.doc["finish"] = {
            "at": v(self.x, self.y, self.z + size - 1.6),
            "size": v(size, 4.0, 2.0),
            "lounge": v(self.x, self.y, self.z + size / 2 - 1.0),
        }
        self.point(self.z + size / 2)

    def build(self):
        self.doc["pieces"] = self.pieces
        self.doc["checkpoints"] = self.checkpoints
        self.doc["route"] = self.route
        return self.doc


THEMES = {
    "noon": {"sky": [0.42, 0.66, 0.92], "horizon": [0.80, 0.88, 0.95], "water": [0.12, 0.45, 0.62]},
    "lagoon": {"sky": [0.30, 0.70, 0.86], "horizon": [0.78, 0.92, 0.92], "water": [0.08, 0.55, 0.58]},
    "dusk": {"sky": [0.38, 0.36, 0.62], "horizon": [0.95, 0.66, 0.48], "water": [0.18, 0.24, 0.42],
             "sun": [1.0, 0.78, 0.60]},
    "storm": {"sky": [0.36, 0.42, 0.50], "horizon": [0.64, 0.68, 0.72], "water": [0.14, 0.26, 0.32]},
    "mint": {"sky": [0.50, 0.78, 0.80], "horizon": [0.86, 0.95, 0.90], "water": [0.10, 0.50, 0.46]},
    "peach": {"sky": [0.56, 0.62, 0.86], "horizon": [0.98, 0.84, 0.72], "water": [0.16, 0.38, 0.60],
              "sun": [1.0, 0.90, 0.78]},
}


# --- The ten courses -------------------------------------------------------------

def first_splash():
    c = Course("wo_first_splash", "First Splash",
               "Everything once, and gently: a gap, an arm, three balls and a ride.", THEMES["noon"])
    c.run_out(8)
    c.gap(2.4)
    c.deck(8)
    c.side_sweeper(length=12, speed=70)
    c.checkpoint()
    c.balls(count=3)
    c.deck(8)
    c.checkpoint()
    c.mover_crossing(length=9, period=6.0)
    c.deck(6)
    c.gap(2.2)
    c.finish()
    return c.build()


def spin_cycle():
    c = Course("wo_spin_cycle", "Spin Cycle",
               "Turntables, and arms that turn on top of them. Nothing here stands still.",
               THEMES["lagoon"])
    c.run_out(6)
    c.turntable(radius=5.0, speed=30.0)
    c.deck(6)
    c.checkpoint()
    c.centre_spinner(size=11, speed=65)
    c.gap(2.4)
    c.deck(5)
    c.turntable(radius=5.5, speed=-40.0, spinner_speed=55.0)
    c.deck(6)
    c.checkpoint()
    c.side_sweeper(length=12, speed=95, arms=3)
    c.gap(2.6)
    c.finish()
    return c.build()


def big_balls():
    c = Course("wo_big_balls", "Big Balls",
               "Three sets of balls, each set further apart, and something swinging between them.",
               THEMES["peach"])
    c.run_out(8)
    c.balls(count=3, radius=1.4)
    c.deck(6)
    c.checkpoint()
    c.pendulums(width=3.2, count=2, period=3.2)
    c.balls(count=4, radius=1.6)
    c.deck(6)
    c.checkpoint()
    c.balls(count=3, radius=1.8)
    c.deck(4)
    c.finish()
    return c.build()


def punch_alley():
    c = Course("wo_punch_alley", "Punch Alley",
               "Narrow walkways and rams that strike across them. Wait for the window.",
               THEMES["storm"])
    c.run_out(8)
    c.pusher_alley(count=3, period=2.6)
    c.deck(5)
    c.checkpoint()
    c.flat_belt(length=12, speed=3.0)
    c.deck(4)
    c.pusher_alley(count=4, period=2.2, reach=2.6)
    c.deck(5)
    c.checkpoint()
    c.gap(2.6)
    c.deck(5)
    c.pusher_alley(count=2, period=1.8)
    c.gap(2.2)
    c.finish()
    return c.build()


def trapdoor_run():
    c = Course("wo_trapdoor_run", "Trapdoor Run",
               "Floors that drop out from under you, and two rides across the gaps between them.",
               THEMES["mint"])
    c.run_out(8)
    c.tiles(cols=3, rows=4, period=3.4, down=0.25, seed=3)
    c.deck(6)
    c.checkpoint()
    c.mover_crossing(length=10, period=6.5)
    c.deck(5)
    c.tiles(cols=4, rows=5, period=2.8, down=0.3, seed=11)
    c.deck(6)
    c.checkpoint()
    c.bouncer_up(rise=3.0)
    c.deck(6)
    c.tiles(cols=3, rows=3, period=2.4, down=0.34, seed=29)
    c.deck(4)
    c.finish()
    return c.build()


def log_roll():
    c = Course("wo_log_roll", "Log Roll",
               "Rolling logs and tipping planks over open water. Keep moving or go backwards.",
               THEMES["lagoon"])
    c.run_out(8)
    c.rollers(count=3)
    c.deck(6)
    c.checkpoint()
    c.seesaws(count=3, amplitude=12, period=4.2)
    c.deck(6)
    c.checkpoint()
    c.rollers(count=4, speed=90.0)
    c.deck(4)
    c.gap(2.4)
    c.finish()
    return c.build()


def the_sweeper():
    c = Course("wo_the_sweeper", "The Sweeper",
               "Low arms to jump and high arms to duck, faster every time.", THEMES["dusk"])
    c.run_out(8)
    c.side_sweeper(length=12, speed=60, height=0.55)
    c.gap(2.2)
    c.side_sweeper(length=12, speed=75, height=0.55, arms=3, phase=40)
    c.deck(4)
    c.checkpoint()
    c.high_sweeper(length=14, speed=60, arms=2)
    c.gap(2.2)
    c.centre_spinner(size=12, speed=80, height=0.6, arms=3)
    c.gap(2.4)
    c.side_sweeper(length=13, speed=90, height=0.55, arms=2, phase=90)
    c.deck(4)
    c.checkpoint()
    c.centre_spinner(size=12, speed=85, height=0.6, arms=3, phase=30)
    c.gap(2.2)
    c.finish()
    return c.build()


def uphill_belt():
    c = Course("wo_uphill_belt", "Uphill Belt",
               "Up the belts, up the bouncers, and the hammers at the top.", THEMES["noon"])
    c.run_out(8)
    c.conveyor_climb(length=12, rise=2.0, speed=2.5)
    c.deck(6)
    c.checkpoint()
    c.bouncer_up(rise=3.2)
    c.deck(6)
    c.conveyor_climb(length=14, rise=2.4, speed=3.2)
    c.deck(5)
    c.checkpoint()
    c.pendulums(width=3.4, count=2, period=3.0)
    c.bouncer_up(rise=3.0)
    c.deck(4)
    c.finish()
    return c.build()


def hammer_gauntlet():
    c = Course("wo_hammer_gauntlet", "Hammer Gauntlet",
               "Narrow beams under swinging hammers, and rams along the way.", THEMES["storm"])
    c.run_out(8)
    c.pendulums(width=3.0, count=3, period=3.0)
    c.deck(5)
    c.checkpoint()
    c.gap(2.2)
    c.beam(length=8, width=1.6)
    c.gap(2.0)
    c.deck(5)
    c.pendulums(width=2.4, count=4, period=2.6, swing=60)
    c.deck(5)
    c.checkpoint()
    c.pusher_alley(count=2, period=2.4)
    c.pendulums(width=2.4, count=2, period=2.2, swing=60)
    c.deck(3)
    c.finish()
    return c.build()


def grand_tour():
    c = Course("wo_grand_tour", "Grand Tour",
               "The long one: a bit of everything, four checkpoints and no time to stand still.",
               THEMES["peach"], seconds=300.0)
    c.run_out(8)
    c.side_sweeper(length=12, speed=70)
    c.balls(count=3)
    c.deck(6)
    c.checkpoint()
    c.turntable(radius=5.0, speed=35)
    c.deck(5)
    c.pusher_alley(count=2, period=2.4)
    c.deck(5)
    c.checkpoint()
    c.rollers(count=3)
    c.deck(5)
    c.mover_crossing(length=9, period=6.0)
    c.deck(5)
    c.checkpoint()
    c.tiles(cols=3, rows=4, period=3.2, down=0.25, seed=7)
    c.deck(5)
    c.pendulums(width=3.0, count=2, period=3.0)
    c.deck(4)
    c.checkpoint()
    c.conveyor_climb(length=10, rise=1.6, speed=2.5)
    c.deck(4)
    c.centre_spinner(size=11, speed=80, arms=3)
    c.gap(2.4)
    c.finish()
    return c.build()


# --- The arenas --------------------------------------------------------------------

def arena(aid, name, blurb, theme, pieces, spawns, drops, gallery, kill=-8.0):
    return {
        "format": 1, "kind": "arena", "id": aid, "name": name, "author": AUTHOR, "blurb": blurb,
        "theme": theme, "kill_height": kill, "pieces": pieces,
        "spawns": [{"at": v(*at), "size": v(*size)} for at, size in spawns],
        "drops": [{"at": v(*at), "size": v(*size)} for at, size in drops],
        "gallery": {"at": v(*gallery[0]), "size": v(*gallery[1])},
    }


def box(at, size, role="arena", yaw=0.0):
    return {"kind": "box", "at": v(*at), "size": v(*size), "role": role, "yaw": r(yaw)}


def arenas():
    out = []

    # A round floor (a ring of boxes would be a polygon; a big cylinder is exact) with a slow
    # arm in the middle that sweeps the props as well as the people.
    out.append(arena("wo_arena_ring", "The Ring",
        "A round floor, a slow arm in the middle, and nowhere to hide from it.", THEMES["dusk"],
        [{"kind": "cylinder", "at": v(0, -0.5, 0), "radius": 14.0, "height": 1.0, "role": "arena"},
         {"kind": "spinner", "at": v(0, 0, 0), "arm_length": 9.0, "arm_height": 0.6, "speed": 40.0,
          "arms": 2, "hub_radius": 0.9}],
        [((0, 0, -11), (4, 3)), ((0, 0, 11), (4, 3)), ((-11, 0, 0), (3, 4)), ((11, 0, 0), (3, 4)),
         ((8, 0, 8), (3, 3)), ((-8, 0, -8), (3, 3))],
        [((0, 0, 0), (14, 14))],
        ((0, 6, 20), (16, 5))))

    # Four islands joined by narrow bridges: the bridges are where a thrown crate counts.
    islands = []
    for sx, sz in ((-1, -1), (1, -1), (-1, 1), (1, 1)):
        islands.append(box((sx * 9, -0.5, sz * 9), (9, 1, 9)))
    islands += [box((0, -0.5, -9), (9, 1, 2.2)), box((0, -0.5, 9), (9, 1, 2.2)),
                box((-9, -0.5, 0), (2.2, 1, 9)), box((9, -0.5, 0), (2.2, 1, 9))]
    out.append(arena("wo_arena_islands", "Four Islands",
        "Four islands and four narrow bridges. Hold yours, or cross.", THEMES["lagoon"],
        islands,
        [((-9, 0, -9), (4, 4)), ((9, 0, 9), (4, 4)), ((9, 0, -9), (4, 4)), ((-9, 0, 9), (4, 4))],
        [((-9, 0, -9), (6, 6)), ((9, 0, 9), (6, 6)), ((9, 0, -9), (6, 6)), ((-9, 0, 9), (6, 6))],
        ((0, 7, 22), (16, 5))))

    # A stepped pyramid: high ground in the middle, reached by steps a jump climbs.
    tiers = [box((0, -0.5, 0), (28, 1, 28)), box((0, 0.4, 0), (16, 0.8, 16)),
             box((0, 1.2, 0), (8, 0.8, 8), role="safe")]
    out.append(arena("wo_arena_tiers", "The Steps",
        "A pyramid of three steps. The top is worth having, and everybody can see you on it.",
        THEMES["peach"], tiers,
        [((-11, 0, -11), (4, 4)), ((11, 0, 11), (4, 4)), ((11, 0, -11), (4, 4)),
         ((-11, 0, 11), (4, 4))],
        [((0, 1.6, 0), (6, 6)), ((-10, 0, 0), (4, 12)), ((10, 0, 0), (4, 12))],
        ((0, 7, 22), (16, 5))))

    # A square with a hole in the middle and two movers that cross it.
    pit = [box((0, -0.5, -10), (26, 1, 6)), box((0, -0.5, 10), (26, 1, 6)),
           box((-10, -0.5, 0), (6, 1, 14)), box((10, -0.5, 0), (6, 1, 14)),
           {"kind": "mover", "from": v(-4.5, -0.4, 0), "to": v(4.5, -0.4, 0), "size": v(3.5, 0.6, 3.5),
            "period": 5.0},
           {"kind": "mover", "from": v(0, -0.4, -4.5), "to": v(0, -0.4, 4.5), "size": v(3.5, 0.6, 3.5),
            "period": 6.0, "phase": 0.25}]
    out.append(arena("wo_arena_pit", "The Pit",
        "A square round a hole, with two rides across it. Knock somebody in.", THEMES["storm"], pit,
        [((-10, 0, -10), (4, 3)), ((10, 0, 10), (4, 3)), ((10, 0, -10), (4, 3)),
         ((-10, 0, 10), (4, 3))],
        [((0, 0, -10), (18, 4)), ((0, 0, 10), (18, 4)), ((-10, 0, 0), (4, 10)), ((10, 0, 0), (4, 10))],
        ((0, 7, 21), (16, 5))))

    # The whole floor turns.
    out.append(arena("wo_arena_turntable", "Merry-Go-Round",
        "The floor turns, and everything on it goes round with you, crates included.",
        THEMES["mint"],
        [{"kind": "turntable", "at": v(0, -0.3, 0), "radius": 13.0, "thickness": 0.6, "speed": 18.0},
         box((0, 0.5, 0), (2.4, 1.0, 2.4), role="pillar")],
        [((0, 0, -9), (4, 3)), ((0, 0, 9), (4, 3)), ((-9, 0, 0), (3, 4)), ((9, 0, 0), (3, 4))],
        [((0, 0, 0), (12, 12))],
        ((0, 6, 19), (16, 5))))

    return out


def documents():
    courses = [first_splash(), spin_cycle(), big_balls(), punch_alley(), trapdoor_run(), log_roll(),
               the_sweeper(), uphill_belt(), hammer_gauntlet(), grand_tour()]
    return courses + arenas()


def main():
    check = "--check" in sys.argv
    os.makedirs(ROOT, exist_ok=True)
    stale = []

    for doc in documents():
        path = os.path.join(ROOT, doc["id"] + ".json")
        text = json.dumps(doc, indent=1, sort_keys=False) + "\n"

        if check:
            old = open(path).read() if os.path.exists(path) else ""
            if old != text:
                stale.append(path)
            continue

        with open(path, "w") as out:
            out.write(text)

    if check:
        if stale:
            print("out of date (run tools/build.py):")
            for path in stale:
                print("  " + os.path.relpath(path))
            return 1
        print("every document is what tools/build.py writes")
        return 0

    print("wrote %d documents to %s" % (len(documents()), os.path.relpath(ROOT)))
    return 0


if __name__ == "__main__":
    sys.exit(main())
