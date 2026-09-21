# Life Simulation

A continuously evolving [Gray–Scott reaction-diffusion](https://en.wikipedia.org/wiki/Gray%E2%80%93Scott_model)
system. Two interacting concentrations follow a pair of partial differential
equations that produce organic, life-like spatial patterns.

[Open the live dashboard](https://gencay.github.io/life-simulation/)

![Latest simulation state](simulation/latest.svg)

## Evolution

The `Evolve simulation` GitHub Actions workflow runs at 02:17, 08:17, 14:17,
and 20:17 UTC each day. Each run:

1. Tests the numerical model.
2. Advances the persisted field by 80 time steps.
3. Renders the latest state as an SVG.
4. Records concentration and activity measurements.
5. Regenerates and deploys the GitHub Pages dashboard.
6. Commits the new state only when the simulation genuinely changed.

GitHub schedules are best-effort and can occasionally start later than the
configured time. The workflow can also be started manually from the Actions
tab.

## Run locally

Python 3.10 or newer is sufficient; there are no third-party dependencies.

```shell
python simulation.py
python -m unittest -v
```

Generated artifacts are stored in `simulation/`:

- `state.json` — the complete field used by the next evolution.
- `latest.svg` — a visualization of the current generation.
- `metrics.json` — measurements for the current generation.
- `history.csv` — measurements across all generations.
