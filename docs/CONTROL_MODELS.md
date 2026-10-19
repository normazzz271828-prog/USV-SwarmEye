# Control adapters and reconstructed helpers

`程序.zip` supplied three scripts: o3.m, s3.m and z3.m. These contain LOS
guidance, lateral obstacle deflection, heading PID, virtual-leader synchronization
and speed PID. They call five functions not included in the archive.

The five files in `matlab_helpers/` are newly written replacements, not recovered
author code. `smooth_omega_command` applies a backward-Euler first-order low-pass
(`dt/(tau+dt)`), then a per-step angular acceleration limit, then angular velocity
saturation. The Python adapter uses the same expression. The other four helpers
provide a palette, ship glyph creation/update and CSV/MAT tracking export.

To use with the supplied scripts, put the helper directory on MATLAB's path.
Before running s3.m, run `palette = apply_matlab_white_theme();` because its own
palette initialization is commented out. The original scripts are not overwritten.

## Web integration

Three additional models are available under 参数仿真. They preserve the supplied
0.02-second integration step, obstacle arrangements, trigger radii, forward-half-
plane gate, LOS direction and heading/speed PID. Z preserves its strongest-obstacle
selection, direction memory and command smoothing; O preserves phase synchronization.
Web headings are converted to clockwise degrees from north. Snapshot output is
one second; positions are interpolated locally for playback. The excerpt starts
eight seconds before the first active avoidance step when possible. A finished
route can shorten the requested excerpt, and the displayed duration reflects it.

The browser shows stationary obstacles as diamonds, moving targets as vessels,
and a brief tracking/avoiding state. The displayed control-model metric is proximity
to the trigger domain, not the quantum-field risk score. Original research models
remain risk-only; these controllers are not silently applied to S8/F6 or fused domains.

Implementation differences: MATLAB drawing/export is replaced by the site's Canvas
and JSON export; no GUI loop is executed on the server. Computation stops on a
whole-second boundary after route completion. Per-ship overrides set positions,
headings and base cruise speeds for controlled ships, rather than a constant speed
that would bypass control. All functions are kinematic demonstrations; no rudder,
thrust or full vessel hydrodynamics are modeled. Original speed PID saturation is
retained; anti-windup and a separate acceleration limit are not added.

The original source does not include teammates as obstacles. Adapter 2 adds the
separate coordination layer described below. The source does not supply obstacle hull dimensions or a
collision-free guarantee. Trigger radius is not a physical hull radius. The code's
simple side-selection heuristic is not a complete COLREGs implementation.

## Verification

MATLAB batch verification exercised all five helpers, checked turning amplitude
and slew limits through a sign reversal, checked glyph updates and exported a
three-ship report. Full original MATLAB trajectories have not been cross-validated
against the port. Python tests cover continuity, limits, finite exports, duration,
and actual trajectory changes with avoidance disabled/enabled. Browser acceptance
covers all three models, changing avoidance strength, export, 8x replay and mobile
layout.

Default full computed-route closest centre distances, metres:

| Route | Avoidance off | Avoidance on | Minimum teammate distance (on) |
|---|---:|---:|---:|
| O | 5.188 | 8.641 | 17.692 |
| S | 4.784 | 10.612 | 38.741 |
| Z | 8.011 | 18.373 | 32.599 |

These demonstrate improved separation on these fixtures, not safety under all
parameters. No automatic risk pause, following camera or full-route playback is added.


## Adapter 2: teammate coordination

Engineering extension, enabled by default for O/S/Z only. Each 0.02 s step uses
one immutable pre-integration snapshot to predict pair CPA over 12 s. Expected
centre separation defaults to 18 m (editable 12–40 m). This is a simulation
setting, not a certified vessel safety distance. Constant-velocity prediction can
trigger before the current protective distance is reached.

Head-on pairs both turn starboard; the following boat yields in same-course
encounters; crossing uses fixed boat-ID priority. Yield direction is remembered
until the pair is separating, outside the predicted conflict, and over the desired
separation plus 8 m. Closest active conflict takes heading priority when one boat
has multiple partners. Emergency braking affects both partners based on a
conservative stopping-distance check. It is a heuristic, not a collision-free
optimization or complete COLREGs controller.

A yielding boat is capped at 1 m/s; emergency caps can reach zero. With the module
on, all speed changes are limited to +0.8/-1.5 m/s². The virtual leader pauses
while a pair is active; PID integrators decay during avoidance, and heading returns
to the path over four seconds after release. The original speed floor cannot
prevent emergency stopping. Setting member avoidance to zero disables this layer
and restores source-style speed updates for comparisons.

Exports include pair enter/clear events, per-frame member avoidance, recovery,
member distance, and full-computed-route minimum distances. Cyan lines identify
active teammate pairs. The closest-distance metric now includes both teammates
and external obstacles; the control proximity score still measures external
trigger-domain proximity (it is not a joint safety probability).

Verification fixtures for isolated two-vessel head-on, crossing and overtaking
(with bounded turn dynamics and bounded acceleration) remained above 18 m and
released coordination within 60 s. Parallel formation does not trigger. Default O
route member minimum increased from 17.692 to 18.610 m. Default S and Z member
minima were 39.809 and 32.599 m. Full-route external obstacle centre minima with
coordination on were 6.568, 6.411 and 18.374 m, respectively: O/S external clearance
is smaller than with coordination off. This interaction remains a limitation;
we do not claim that improving teammate separation guarantees external safety.
Arbitrary user initial states (especially already-overlapping vessels), multiple
simultaneous conflicts and all parameter extremes are not proven safe. The
MATLAB helper package remains a reconstruction of the earlier source helpers;
this new coordinator is implemented in the website Python engine.
