# Research parameter console

The `参数仿真` route uses `swarmeye/research.py`. The original eight demonstration
scenarios and encrypted archives retain their existing engine and formats.
Research exports are separate parameter/result JSON, not legacy archive imports.
No source browser, source download, or mathematical exposition is presented in
the console. Advanced parameters and individual initial states remain editable.

## Supplied source mapping

- `Simulation code.zip`: triangle and S-formation
  `AdvancedQuantumRiskVisualizationSystem.m` and **full**
  `AdvancedQuantumRiskTraverser.m`, associated by the user with *Predictive dynamic
  encounter spatiotemporal risk analysis of unmanned ship formations via quantum
  field*. The `Fixed` traverser is not used: it contains demonstration outputs.
- `PythonProject3.rar/PythonProject3/main.py`: seed-neighbour clustering,
  heading-dependent elliptical domains, fused radial envelopes, spatial/time
  risk blending. Its paper identity was not independently established.

These are computational adapters of supplied programs, not independent validation
of the papers. Neither source contains an autonomous collision-avoidance controller.
The simulation follows configured courses. Manual decisions in the older route
also do not actuate the ships.

## Implemented calculation

MATLAB defaults: ten independent ships at source positions, 8 m/s, directions
0,36,...324 degrees from east; fleet centre (1000,800), velocity (5,3), radius
60 m. Triangle side 800 m and four samples per edge (nine unique vessels); S
formation fifteen vessels, spacing 80 m, amplitude 200 m, frequency .05 /m.

Wave density is `exp(-distance²/sigma²)`. Entropy is computed over the original
100×100 [0,2000] grid. Independent-pair score is `.7 classic + .3 quantum`, where
quantum is `strength² * (1-(H1+H2)/2) * exp(-distance/100)`.
Ship/fleet-point score is `.76 classic`. Values must exceed the editable source
filter (default .3); displayed risk is the maximum surviving pair score or zero.
Raw quantum contributions can be negative in the supplied algorithm; they are
not silently replaced with fabricated probabilities.

The field combines `.4 shipfield + .3 fleetfield + .3 quantumfield` with the
source spatial widths and weights. Display intensity is normalized per frame;
exports also include `field_peak`. This field is distinct from the pair score.
The source slices a 100×100 density grid into a smaller risk grid with different
coordinates. The adapter evaluates all terms on one aligned display grid (40×40)
instead, an intentional correction; entropy retains the original 100×100 grid.
Wave phase does not affect density or entropy in this calculation, so decorative
phase/interference controls and unused source knobs are not exposed.

Python model keeps the original 14-ship arrangement, knots-to-m/s conversion,
length/speed-dependent domain axes, .6 longitudinal offset, 30-point radial hull,
seed-neighbour clustering and directional weighting. The score is
`sqrt((Us²+Ut²)/2)+.15 Us Ut`, clipped to [0,1], with domain intrusion set to one.
The source's `DCPA_m` is radial clearance, not CPA; the UI does not label it CPA.
The original unused speed-difference clustering constant is not exposed.

## Adaptations and limits

- Python geographic motion is projected to a fixed local metre plane at 38.3°.
  This is a local-projection approximation rather than an exact geographic replay.
- Both models sample one simulated second per frame; 34 samples cover a 33-second
  excerpt. Source Python originally advances in 20-second steps. Continuous
  browser interpolation changes rendering only; risk readouts use actual samples.
- Excerpt selection finds first protective-distance entry within a configurable
  search horizon, otherwise the closest approach. Python selection uses a coarse
  arena-distance gate; it is not an autonomous avoidance onset. A source scenario
  already overlapping a domain can legitimately begin at time zero.
- MATLAB boundary behaviour clamps/reverses independent ships and translates the
  fleet rigidly with its centroid reflecting at 0/2000 m, as in the source.
- Explicit per-ship initial states override the preset positions and velocities;
  fleet shape/heading presets apply when the override checkbox is off. Changing
  vessel count requires resetting the override. Domains still use the chosen
  model. Parameters are finite and range-validated on the server.
- Fixed camera bounds cover the excerpt. No following, alarm-triggered pause or
  full-process playback. Pause, seek, replay and 1/2/4/8× speed run locally without
  Streamlit requests. Only applying parameters invokes the Python calculation.
- The bounded cache retains at most eight computations. Exports contain model
  version, validated configuration, absolute excerpt start, all frames and bounds.

## Verification

`tests/test_research.py` checks source-equation fixtures, parameter sensitivity,
finite deterministic output, rejection of invalid values, motion continuity and
individual initial-state overrides. `tests/browser_research.py` checks three model
routes, re-computation, playback completion, seeking and exported results.
The existing fleet/encrypted-archive browser regression remains applicable.
MATLAB runtime execution and a full paper-result reproduction were not performed.
