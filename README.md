# Life Simulation: From Chemistry to Order

**Aim:** explore how life might begin by asking how simple chemical interactions
can organize themselves into persistent patterns. This AI-authored experiment
offers a visual interpretation of one possible ingredient in life's origins:
self-organization in a system supplied with matter.

The current model is a [Gray–Scott reaction-diffusion](https://en.wikipedia.org/wiki/Gray%E2%80%93Scott_model)
system, not a reconstruction of early Earth or a simulation of living organisms.
It does not model genetic information, membranes, metabolism, reproduction, or
Darwinian evolution. An organized pattern is not evidence that life has emerged.

[Open the live dashboard](https://gencay.github.io/life-simulation/)

![Latest simulation state](simulation/latest.svg)

## Watch the experiment evolve

The dashboard combines a concentration field, a selectable historical chart
(active area, mean concentration, and spatial variation), and recorded-generation
playback. The newest 48 field snapshots are available for replay; the complete
measurement history is retained. These are actual saved results, not a fabricated
animation. "Active sites" means grid sites above a concentration threshold, not
biological cells.

An AI-authored interpretation explains self-organization and relates the latest
measurements to the previous observation. The changing text uses transparent,
fixed rules; no AI model is called during scheduled runs, and it does not make
claims about life appearing.

The page checks for new published results every minute while visible. New
simulation observations are computed four times daily, not continuously in the
browser. Historical playback is labelled separately from the latest observation.

## Observations and publication

The `Evolve simulation` GitHub Actions workflow runs at 02:17, 08:17, 14:17,
and 20:17 UTC each day. Each run:

1. Tests the numerical model.
2. Advances the persisted field by 80 time steps.
3. Renders the latest state as an SVG.
4. Records concentration and activity measurements.
5. Commits the evolved state and dashboard data.
6. Deploys the updated GitHub Pages dashboard.

GitHub schedules are best-effort and can occasionally start later than the
configured time. The workflow can also be started manually from the Actions
tab, and dashboard/model changes pushed to `main` also trigger publication.
There is no universal scientific wall-clock schedule for this model: four
daily observations are a publishing choice. Each observation advances 80
numerical steps with timestep 1 in model units, not hours of early-Earth history.

Full concentration fields, measurements, and previous versions remain auditable
in this repository's commit history.
