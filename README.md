The courses and arenas for [**mg-wipeout**](https://github.com/gamemann/mg-wipeout): obstacle courses over open water, and the arenas a final death is fought in. Ten courses and five arenas to start with.

Every course and arena is a **JSON document**, not a scene. A server reads the documents in its course directory and sends the one it is playing to every client as the round begins, so players need no course files at all and a new course is one file dropped into a directory.

## Using it
[dot-bootstrap](https://github.com/modcommunity/dot-bootstrap) clones this repository next to mg-wipeout and links it into the game as `courses/`, so `./game.sh` in mg-wipeout plays these courses with nothing else to do. On a server they are delivered as a pack of their own (`wipeout_maps`), which mg-wipeout's `./game.sh online` and `./game.sh server` build for you.

## The courses

| Course | What it is |
| --- | --- |
| `wo_first_splash` (First Splash) | Everything once, and gently: a gap, an arm, three balls and a ride |
| `wo_spin_cycle` (Spin Cycle) | Turntables, and arms that turn on top of them |
| `wo_big_balls` (Big Balls) | Three sets of balls, each set further apart, and hammers between them |
| `wo_punch_alley` (Punch Alley) | Narrow walkways and rams that strike across them |
| `wo_trapdoor_run` (Trapdoor Run) | Floors that drop out from under you, and rides across the gaps |
| `wo_log_roll` (Log Roll) | Rolling logs and tipping planks over open water |
| `wo_the_sweeper` (The Sweeper) | Low arms to jump, faster every time |
| `wo_uphill_belt` (Uphill Belt) | Up the belts, up the bouncers, and the hammers at the top |
| `wo_hammer_gauntlet` (Hammer Gauntlet) | Narrow beams under swinging hammers, and rams |
| `wo_grand_tour` (Grand Tour) | The long one: a bit of everything, four checkpoints |
| `wo_lily_pond` (Lily Pond) | Spinning pads to hop across, planks that tip you into the pond, and a ferry to catch |

| Arena | What it is |
| --- | --- |
| `wo_arena_ring` (The Ring) | A round floor with a slow arm in the middle |
| `wo_arena_islands` (Four Islands) | Four islands and four narrow bridges |
| `wo_arena_tiers` (The Steps) | A three-step pyramid; the top is worth having |
| `wo_arena_pit` (The Pit) | A square round a hole, with two rides across it |
| `wo_arena_turntable` (Merry-Go-Round) | The whole floor turns |

## How they are made

`tools/build.py` writes every document in `courses/` from a short description of each course as a run of **sections** (a gap, a sweeper, a set of balls, a mover crossing), each of which places its pieces, its checkpoint and the route a stand-in follows together. Moving one gap moves everything after it.

```bash
python3 tools/build.py            # rewrite courses/*.json
python3 tools/build.py --check    # exit 1 if a file differs from what the builder writes
```

The JSON is still what the game reads and is committed; CI runs `--check`, so a hand edit to a document the builder does not know about is caught instead of being lost on the next build. Hand-written documents that the builder does not produce are fine too: anything in `courses/` with a `.json` extension is loaded.

Every course is played to the finish by a stand-in in mg-wipeout's `examples/headless_courses.tscn`, with every hazard live. A course it cannot finish inside its own clock is a course with no window somewhere, and the suite says where it got to.

## The format

Every length is metres, every angle degrees, every time seconds. Courses run toward **−Z** (yaw 0 faces −Z). A position is the **centre** of what it places, except where a field says otherwise. Colours are `[r, g, b]` in 0–1.

```json
{
  "format": 1,
  "kind": "course",
  "id": "wo_my_course",
  "name": "My Course",
  "author": "you",
  "blurb": "One line the server shows at the top of the round.",
  "theme": {"sky": [0.4, 0.66, 0.92], "horizon": [0.8, 0.88, 0.95], "water": [0.12, 0.45, 0.62]},
  "water_height": -6,
  "course_seconds": 240,
  "start": {"at": [0, 0, 0], "size": [10, 8], "yaw": 0},
  "pieces": [ ... ],
  "checkpoints": [{"at": [0, 0, -30], "size": [6, 4, 2.4]}],
  "finish": {"at": [0, 0, -80], "size": [10, 4, 2], "lounge": [0, 0, -84]},
  "route": [ ... ]
}
```

- `start.at` is the **top** of the start pad; the game builds the pad, its side walls and the gate the countdown holds closed across its −Z edge.
- `checkpoints` and `finish` are volumes whose `at` is their **bottom** centre: a runner is through when they stand inside one. Falling in puts a runner back at the last checkpoint they crossed. `lounge` is where finishers wait.
- `water_height` is where falling in starts. `course_seconds` is optional and is capped by the server's `wo_course_seconds`.
- Ids are lowercase `a-z`, `0-9` and `_`. A document a server cannot read is refused with the reason, and every other course still plays: `wo_courses` on the server lists refusals.

### Pieces

Every piece has a `kind`, and may have `yaw` and a `role` (`deck`, `pillar`, `cannon`, `arena`, `hazard`, `safe`), which decides its texture.

**Still**

| kind | fields | |
| --- | --- | --- |
| `box` | `at`, `size` | ground |
| `ramp` | `at`, `size`, `pitch` | a box tilted about its X axis; positive raises its −Z end |
| `ball` | `at`, `radius` | stand only near the top (about 35°) |
| `cylinder` | `at`, `radius`, `height` | upright |

**Carriers:** solid, and whoever stands on one moves with it

| kind | fields | |
| --- | --- | --- |
| `mover` | `from`, `to`, `size`, `period`, `phase` | slides between two centres, eased at both ends |
| `turntable` | `at`, `radius`, `speed`, `thickness`, `phase` | turns at `speed` degrees a second |
| `roller` | `at`, `length`, `radius`, `speed` | a log along its X axis, rolling at `speed` degrees a second |
| `seesaw` | `at`, `size`, `amplitude`, `period`, `phase` | tips about its X axis |
| `conveyor` | `at`, `size`, `speed`, `pitch` | a belt moving whoever is on it along its −Z at `speed` m/s (negative runs back toward the start); `pitch` lays it on a slope |
| `tiles` | `at`, `cols`, `rows`, `tile`, `gap`, `thickness`, `period`, `down`, `seed` | a grid; each tile drops out for `down` of every `period`, each at its own point in the cycle |
| `bouncer` | `at`, `size`, `power` | throws whoever lands on it up at `power` m/s |

**Hazards:** not solid; whatever they touch is thrown

| kind | fields | |
| --- | --- | --- |
| `spinner` | `at` (the base of its post), `arm_length`, `speed`, `arms`, `arm_height`, `arm_thickness`, `hub_radius`, `hub_height`, `phase` | arms round a solid post; jump a low one, duck a high one |
| `pendulum` | `pivot`, `length`, `radius`, `swing`, `period`, `phase` | a ball on a rod, swinging `swing` degrees either side along its X axis (yaw 0 swings across a course) |
| `pusher` | `at`, `size`, `reach`, `period`, `duty`, `phase` | a ram that strikes `reach` metres along its −Z, holds for `duty` of its period, and goes home |

`phase` is a fraction of a period (0–1) for anything with a period, and degrees for anything that turns. Everything that moves is a function of time and nothing else, which is what lets every machine agree about where it is without being told.

### The route

The points a stand-in runs through, in order. Each is `{"at": [x, y, z]}` with any of:

- `jump`: jump here (once on the ground); a jump point that is a top to land on is braked toward in the air;
- `wait`: wait here until the way to the next point is clear of every hazard for the time it takes to run it;
- `board`: this is something to land on: wait until it will be there, then run and jump at the edge;
- `ride`: this point is ON something that moves: standing on any carrier reaches it;
- `walk`, `reach` (metres, default 1.2).

### Arenas

```json
{
  "format": 1, "kind": "arena", "id": "wo_arena_mine", "name": "Mine", "author": "you",
  "kill_height": -8,
  "pieces": [ ... ],
  "spawns": [{"at": [-9, 0, -9], "size": [4, 4]}, ... ],
  "drops": [{"at": [0, 0, 0], "size": [12, 12]}],
  "gallery": {"at": [0, 6, 20], "size": [14, 5]}
}
```

`spawns` are the areas a side can be put down in (at least two; give it four or more so the draw of who goes where varies), `drops` where props and weapons land, and `gallery` a walled box where everybody who did not finish watches from. An arena can use any piece a course can.

## License

MIT. See [LICENSE](LICENSE).
