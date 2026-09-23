# Repository instructions and session handoff

This file records the owner's project requirements, decisions, and operational
context for future sessions and devices. Keep it current when those decisions
change. Live repository data and workflow settings take precedence over the
dated status snapshot below.

## Owner and project

- Owner: personal GitHub account **gencay**, not a work account.
- Repository: https://github.com/gencay/life-simulation
- Default branch: `main`.
- Public dashboard: https://gencay.github.io/life-simulation/
- Visibility: public, explicitly approved by the owner because their GitHub
  plan did not support Pages for this private repository.
- Preferred coding-assistant model: **GPT-6 Astra (`gpt-6-astra`)**, for both
  the session and user default. This was configured on the original device;
  assistant settings and authentication do not transfer with a Git clone.

## Aim and scientific framing

Explore how life might have begun through simple chemical interactions and
self-organization, and communicate an AI-authored interpretation of the results.
The owner wants a persistent, evolving experiment, not just a static demo.

The current implementation is a Gray-Scott reaction-diffusion model: a toy model
of one possible ingredient in life's origins, not a reconstruction of abiogenesis
or evidence that life has been created. It does not model genetics, membranes,
metabolism, reproduction, or Darwinian evolution. Do not present chemical
patterns as organisms or an increasing probability of life.

Explain what the project aims to explore, how it works, and what is changing.
Keep the README and public dashboard focused on those topics, not instructions
for running the simulation locally.

The interpretation is AI-authored prose plus measurement-driven commentary
implemented with fixed rules. Scheduled runs do not call an AI model. Preserve
this distinction; do not imply fresh model inference where none occurs.

## Owner's ongoing requirements

- Keep the experiment evolving automatically without requiring an open CLI or
  the owner's computer to remain on.
- Run at least a couple of times daily. The original every-two-hours request
  was superseded by the current four-daily schedule.
- There is no universal scientific wall-clock schedule for this model. Describe
  the cadence as a publishing choice, not a scientific standard.
- Publish actual simulation results to the project's own GitHub Pages dashboard.
- Show historical charts and how the field changes over recorded generations.
- Refresh the open dashboard when new results are published. Distinguish
  historical playback from the latest observation and from continuous compute.
- Commit each generation separately. Do not squash multiple generation results
  into one commit or create empty activity commits.
- Attribute author and committer identities to the owner's personal account,
  not `life-simulation[bot]` or `github-actions[bot]`.
- Preserve the persisted experiment state and measurement history. Do not
  reset the simulation or fabricate historical frames.

## Git identity and rewritten history

Use this repository-local identity on every development device:

```shell
git config --local user.name "gencay"
git config --local user.email "gencay.ali@hotmail.com"
```

The workflow uses the same name and email. GitHub was verified to associate
both author and committer with `gencay`. GitHub Actions still runs the automated
job and authenticates its push; personal commit attribution does not make it
a manual run. Do not replace the workflow token with a personal access token
merely to change authorship.

On 2026-09-23 UTC, the owner explicitly requested rewriting all existing commit
owners and using the Hotmail address. All 18 commits then on `main` were rewritten.
Original dates, messages, trees, and generation order were preserved. The change
was pushed with an exact force-with-lease while the workflow was paused, then
automation was re-enabled.

Older clones may have incompatible history. Inspect and protect any local work
before resynchronizing; a fresh clone is the simplest starting point on another
device. The earlier authorization was for that rewrite, not permission for
future force-pushes or history rewrites.

A recovery bundle named `life-simulation-before-identity-rewrite.bundle` was
saved in the original assistant's local session artifacts. It is not committed,
not on GitHub, and not automatically available on another device.

## Current architecture and data

The solver is dependency-free Python; the dashboard uses static HTML, CSS, and
JavaScript without a frontend build system.

| Resource | Responsibility |
| --- | --- |
| `simulation.py` | Numerical evolution, metrics, snapshots, and dashboard data publication |
| `test_simulation.py` | State continuation, generation changes, frame integrity, retention, and history checks |
| `simulation\state.json` | Full-precision U/V fields and parameters; source for the next run |
| `simulation\metrics.json` | Latest generation's measurements and observation timestamp |
| `simulation\history.csv` | Complete measurement history |
| `simulation\frames.json` | Most recent 48 recorded, display-quantized concentration frames |
| `simulation\latest.svg` | Latest field visualization |
| `site\index.html` | Project aim, model explanation, interpretation, and dashboard structure |
| `site\app.js` | Chart selection, replay, scrubbing, commentary, polling, and error reporting |
| `site\styles.css` | Responsive dashboard styling |
| `site\data\dashboard.json` | Coherent bundle of metrics, parameters, full history, and retained frames |
| `site\data\history.json`, `metrics.json`, `latest.svg` | Additional published result files |
| `.github\workflows\evolve.yml` | Generation commits and GitHub Pages deployment |

Current model: periodic 64 x 64 grid, diffusion U 0.16, diffusion V 0.08,
feed 0.060, kill 0.062, timestep 1. Each generation advances 80 numerical
steps; these units are not hours of early-Earth history.

"Active sites" means grid locations with V above 0.10, not biological cells.
Charts offer active-site count, mean V, and spatial standard deviation.
Complete measurements are retained even when the 48-frame replay window rolls
forward. Full prior states remain in Git history. Early playback frames were
recovered from actual commits, not synthesized.

The visible page polls every 60 seconds and refreshes on returning to the tab.
It keeps the last good observation if updates fail, visibly reports errors,
and warns if the latest observation is more than eight hours old.

## Automation and deployment

- Workflow: `Evolve simulation`, file `.github\workflows\evolve.yml`.
- Schedule: `17 2,8,14,20 * * *` (02:17, 08:17, 14:17, 20:17 UTC).
- GitHub schedules are best-effort, not a guarantee of exact timing or uptime.
- Also runs on manual dispatch and pushes to `main` affecting `site/**`,
  `simulation.py`, `test_simulation.py`, or the workflow itself.
- Documentation-only edits to the root README or agent instructions do not
  trigger a new generation or deployment.
- Uses an Ubuntu runner and Python 3.13.
- Sequence: tests, advance one generation, commit state and dashboard data,
  upload `site`, deploy Pages.
- Generation commit format: `simulation: evolve generation N`.
- Permissions: contents write, Pages write, OIDC token write.
- Concurrency group: `pages`, with in-progress runs not cancelled.
- GitHub Pages uses workflow deployment and the `github-pages` environment.

Manual dispatch is available when needed:

```shell
gh workflow run evolve.yml --repo gencay/life-simulation
```

Dispatch advances the experiment; it is not just a refresh of the static page.
The workflow commits through `GITHUB_TOKEN`, so its own data push does not
recursively trigger another push workflow. Deployment occurs within the same
run rather than depending on that push.

If deployment fails after a generation commit, diagnose and recover the
deployment without discarding state or unnecessarily advancing again.

## Continuing safely on another device

1. Clone the current repository and read this file before changing anything.
2. Authenticate GitHub CLI as `gencay` through the normal login flow. Workflow
   edits may require the OAuth `workflow` scope. Never copy credentials or
   device-login codes into the repository.
3. Apply the repository-local Git identity above and select the preferred
   assistant model using that device's supported configuration.
4. Check the worktree, remote `main`, current metrics, recent commits, workflow
   status, and live dashboard. Scheduled runs may have advanced since this
   handoff was written.
5. Preserve uncommitted work and synchronize before editing or pushing; do
   not overwrite newer generated state from a scheduled run.
6. Keep the model, data schema, tests, UI, and scientific explanation consistent
   when behavior changes. Preserve the lightweight implementation.
7. Use `python -m unittest -v` for solver/data changes. For UI changes, check
   chart rendering, playback, scrubbing, refresh, visible failures, and mobile
   layout in a browser. Use scratch output for experiments rather than changing
   the canonical state accidentally.
8. For changes that deploy, verify workflow completion and the public data,
   not only that a push succeeded. GitHub attribution can be checked from
   the commit's author and committer account links.

## Dated handoff status

Recorded on **2026-09-23 UTC**, after the owner's identity-rewrite request:

- Generation **13** was committed and deployed successfully.
- Generation commit: `43f11bb`; both author and committer map to `gencay`.
- Observation timestamp: `2026-09-23T03:01:55.702667+00:00`.
- The workflow was active and the working tree was clean before this
  documentation update.
- No pending implementation task remained; automatic evolution continues.

Treat this as historical context, not a fixed expected generation or commit.
