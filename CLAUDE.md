# mg-wipeout-maps

The courses and arenas mg-wipeout plays, as JSON documents. Read `../../CLAUDE.md` and `../mg-wipeout/CLAUDE.md` first: the format is defined and validated by `mg-wipeout/game/wo_course_doc.gd`, built by `wo_course.gd`, and this README is the mapper's copy of it.

**`courses/` is what the game reads**, through a dot-bootstrap link (`mg-wipeout/.gitignore` names it: `# bootstrap-link: mg-wipeout-maps/courses`). The game reads every `.json` there plus one practice course and arena built into it; a refused document is a WARN with the reason, never a server that will not start.

**`tools/build.py` writes every document, and the JSON is committed.** Edit the builder, run it, commit both. `--check` (CI) fails when a committed file differs from what the builder writes, so a hand edit to a built course is caught rather than silently lost; a hand-written course the builder does not produce is fine. Sections place pieces, checkpoints and route points together on a cursor running down −Z — that is the reason for the builder: moving one gap moves everything after it.

## What makes a course finishable, measured

Sized against mg-wipeout's defaults: a 7 m/s run, a 1.25 m jump at 20 m/s², which clears about 4.9 m of flat gap. Gaps here are 3.4 m at the most and steps 0.8 m. **Every number below came from a stand-in failing in `mg-wipeout/tools/trace_course`**, and the builder's own comments say which:

- **Balls 4.0 m apart, logs 3.7 m** (top to top): under a full jump, because a jump is cut short in the air and never stretched, and a landing on a ball or a turning log costs speed.
- **Hammers 4.2 m apart, rams 4.5 m**, with the wait point halfway / 2.4 m short: closer, and somebody waiting for the next one is in reach of the one behind.
- **Side sweepers reach just short of the far edge**, and the deck is longer than their sweep, so there is ground to watch from; **centre spinners are walked round 2.2 m in from the edge**, back to the middle 3.4 m before the far edge, so the next jump is taken straight.
- **Pendulums `yaw` 0**, which swings them across the course. `yaw` 90 swings them along it, where they hit a person waiting for them.
- **A belt on a ramp has the ramp's `pitch`.** Flat at the ramp's middle height it is a wall.
- **Every route starts at the middle of the pad's front**: the pad is wider than the run-out after it.

`mg-wipeout/examples/headless_courses.tscn` runs every course with a stand-in that never fumbles, every hazard live; all ten finish (2026-10-05: 14 s to 77 s against a 210 s clock). A course that newly fails there is a course to fix, or a bot that has found a real hole in its timing.

## What a level is here, for the nightly quota

A level is **a course or an arena that plays differently from every other**, or a section that changes how one plays. In order of preference, as everywhere in this family:

1. **An existing course rebuilt so it plays the way its blurb says** (The Sweeper's "high arms to duck" has no high arm yet; Trapdoor Run's tiles give no warning before they drop — that one is a game change too).
2. **A new section kind in the builder**, made of existing piece kinds, used in at least one course.
3. **A new course or arena** — only with a blurb that says what makes it different, a stand-in finishing it in `headless_courses`, and a render (`mg-wipeout/tools/shot.sh --view=course --wo-course-ids=<id>`).

A new piece KIND is a game change (`wo_course_doc.gd` and `wo_course.gd`), and a level after that.

## Not here yet

- **Publishing.** Nothing here is in any pack. The game repository's pack does not include `courses/` (it is a link), so a delivered server has only the built-in practice course until this repository publishes its documents somewhere a server mounts. See mg-wipeout's "Still to do".
