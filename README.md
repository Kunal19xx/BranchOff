# branchoff

Stress-test **SCIP vs CPLEX** (optionally **cuOpt** too) on real
[MIPLIB 2017](https://miplib.zib.de) benchmark instances, on your own
hardware, and get a CSV comparison plus full raw solver logs.

## What it does

1. Downloads a random sample of MIPLIB 2017 benchmark instances
   (filtered by decision-variable count) into
   `<workdir>/instances`.
2. Runs each selected instance through every available solver, with
   the same thread count, time limit, and memory ceiling.
3. Tracks wall time and peak RSS per run, parses each solver's log
   for objective/bound/node-count/gap, and writes it all to a CSV.
4. Keeps the full raw solver log for every run so you can dig in
   manually.

## Install

```bash
pip install MIPLIBing --break-system-packages
```

You'll also need at least one solver actually installed/licensed:

- **SCIP** — `scip` binary on `PATH`, or the `pyscipopt` module.
- **CPLEX** — `cplex` binary on `PATH`, or the `cplex` Python module
  (requires a license).
- **cuOpt** *(optional)* — `cuopt_cli` binary on `PATH`.

Availability is auto-detected at run time; anything missing is
skipped with a warning (or the whole run aborts if *nothing* is
available and it's not a dry run).

## Usage

```bash
# sane defaults -- downloads instances, runs SCIP + CPLEX + cuOpt
python -m branchoff

# more instances, longer time limit
python -m branchoff --num-instances 10 --time-limit 1200

# only SCIP
python -m branchoff --solvers scip

# SCIP + cuOpt, skip CPLEX
python -m branchoff --solvers scip,cuopt

# just pick/download instances, don't actually solve anything
python -m branchoff --dry-run
```

### Options

| Flag | Default | Meaning |
|---|---|---|
| `--threads` | 32 | Threads given to each solver |
| `--mem-limit-mb` | 13000 | Hard RAM ceiling per solver run (MB) |
| `--time-limit` | 900 | Per-instance, per-solver time limit (s) |
| `--num-instances` | 6 | How many instances to download and run |
| `--min-var` / `--max-var` | 1000 / 50000 | Decision-variable count filter |
| `--size-min-kb` / `--size-max-kb` | 300 / 4000 | Compressed `.mps.gz` size filter |
| `--solvers` | `all` | `all`, or a comma-separated subset of `scip,cplex,cuopt` |
| `--scip-mode` | `concurrent` | `concurrent` = SCIP's `concurrentopt` (actually uses `--threads` cores by racing independent search copies); `optimize` = classic ~single-threaded SCIP |
| `--seed` | 42 | Random seed for instance sampling |
| `--workdir` | `~/branchoff` | Root for `instances/`, `logs/`, `results/` |
| `--dry-run` | off | Only select/download instances, don't solve |

> **Note on `--scip-mode concurrent`:** it parallelizes by racing
> independent search copies (different seeds/permutations), *not* by
> splitting one search tree across cores the way CPLEX does. Treat
> results as "best each solver can do with N threads," not a strictly
> apples-to-apples algorithm comparison.

## Where files go

Everything lives under `--workdir` (default `~/branchoff`):

```
~/branchoff/
├── instances/    # downloaded .mps/.mps.gz files -- always end up here
├── logs/         # one raw solver log per (instance, solver) run
└── results/      # results_<timestamp>.csv
```

Instances are always downloaded fresh via the `MIPLIBing` package.
The download step is now self-verifying: after asking `MIPLIBing` to
fetch instances, branchoff resolves `instances/` to an absolute path,
copies in any file `MIPLIBing` reports outside that folder, then
re-reads the folder from disk and samples from *what's actually
there* rather than trusting the library's reported paths blindly. So
whatever solvers end up running on is guaranteed to be sitting in
`<workdir>/instances` where you can inspect it yourself — run with
`--dry-run` to just populate that folder without solving anything.

## Output

`results/results_<timestamp>.csv` columns:

```
instance, solver, threads, time_limit_s,
status, wall_time_s, solver_reported_time_s,
peak_mem_mb, nodes, primal_bound, dual_bound,
reported_gap_pct, gap_vs_best_known_pct, timed_out_hard
```

A summary table is also printed to the console at the end of the run,
and every individual run's raw solver output is kept in `logs/` for
manual inspection (e.g. if a status looks like `unknown/parse-failed`,
check the corresponding log).

## Package layout

```
branchoff/
├── __main__.py, cli.py       # entry point, argument parsing
├── config.py                 # all constants/defaults in one place
├── runner.py                 # orchestrates sourcing + solving + results
├── instance_sources/
│   ├── download.py           # fetches instances into <workdir>/instances
│   └── local.py              # reads back whatever's on disk (used by download.py)
├── solvers/
│   ├── scip.py, cplex.py     # CLI + Python-API runners, log parsing
│   └── cuopt.py
├── monitor.py                 # subprocess run + peak-RSS tracking
├── results.py, system_info.py, logging_utils.py, http_utils.py
```

## Known limitations

- `gap_vs_best_known_pct` is always `None` for now — the best-known
  objective lookup (`SOLU_ENTRIES` in `runner.py`, meant to be
  populated from MIPLIB's `.solu` file) isn't wired up yet.
- Log parsing uses regexes tuned to each solver's default output
  format; if a solver's log format changes across versions, some
  fields may come back as `None` — check the raw log in `logs/`.
