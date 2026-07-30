"""
Orchestration: for each selected instance, run the requested solvers
and collect results. Doesn't know HOW instances are sourced or HOW
a solver is invoked -- just wires instance_sources + solvers together.
"""

from .logging_utils import log
from .system_info import print_system_banner
from .results import gap_vs_best_known, write_csv, print_summary
from .instance_sources import get_instances
from .solvers import scip as scip_solver
from .solvers import cplex as cplex_solver
from .solvers import cuopt as cuopt_solver

# NOTE: best-known objective lookup (via SOLU_URL) isn't wired up yet --
# gap_vs_best_known_pct will be None until a loader populates this dict.
SOLU_ENTRIES = {}

ALL_SOLVERS = ("scip", "cplex", "cuopt")


def run_benchmark(args):
    workdir = args.workdir
    instance_dir = workdir / "instances"
    log_dir = workdir / "logs"
    results_dir = workdir / "results"
    for d in (instance_dir, log_dir, results_dir):
        d.mkdir(parents=True, exist_ok=True)

    print_system_banner(args.threads, args.mem_limit_mb)

    if args.scip_mode == "concurrent":
        log("NOTE: SCIP is running in `concurrentopt` mode to actually use "
            f"{args.threads} threads. This parallelizes by racing "
            "independent search copies (different seeds/permutations), "
            "NOT by splitting one tree across cores like CPLEX does. "
            "Treat this as 'best each solver can do with 32 threads', "
            "not an apples-to-apples algorithm comparison. Use "
            "--scip-mode optimize for classic single-thread SCIP.")

    selected = _parse_solvers(args.solvers)

    # cuOpt is CLI-only and has no Python-API runner script to write.
    runner_paths = {
        "cplex": cplex_solver.write_pyapi_runner(workdir),
        "scip": scip_solver.write_pyapi_runner(workdir),
        "cuopt": None,
    }
    modules = {"scip": scip_solver, "cplex": cplex_solver, "cuopt": cuopt_solver}

    log("Checking solver availability (CLI binary, then Python API) ...")
    detected_mode = {
        name: modules[name].report_mode() for name in selected
    }
    have = {name: detected_mode[name] is not None for name in selected}

    if not args.dry_run:
        for name in selected:
            if not have[name]:
                log(f"{name.upper()} unavailable -- install/configure it, "
                    f"or drop it from --solvers.")
        if not any(have.values()):
            raise SystemExit(1)
    print(instance_dir)
    picked = get_instances(args, instance_dir, args.source)

    if args.dry_run:
        log(f"Dry run complete. {len(picked)} instance(s) selected.")
        return

    results = []
    for idx, mps_path in enumerate(picked, 1):
        name = mps_path.name.split(".")[0]
        log("=" * 78)
        log(f"[{idx}/{len(picked)}] Instance: {name}")
        solu_entry = SOLU_ENTRIES.get(name)
        if solu_entry:
            log(f"  reference: {solu_entry[0]}"
                + (f", objective={solu_entry[1]}" if solu_entry[1] is not None else ""))

        for solver_name in selected:
            if not have[solver_name]:
                continue
            mode = detected_mode[solver_name]
            module = modules[solver_name]
            log(f"  running {solver_name.upper()} [{mode}] "
                f"({args.threads} threads, {args.time_limit}s limit, "
                f"{args.mem_limit_mb}MB RAM cap) ...")

            if solver_name == "scip":
                r = module.run(name, mps_path, args.threads, args.time_limit,
                                args.mem_limit_mb, args.scip_mode, instance_dir,
                                log_dir, mode, runner_paths["scip"])
            else:
                r = module.run(name, mps_path, args.threads, args.time_limit,
                                args.mem_limit_mb, instance_dir, log_dir,
                                mode, runner_paths[solver_name])

            r.update(instance=name, solver=solver_name.upper(), threads=args.threads,
                      time_limit_s=args.time_limit,
                      gap_vs_best_known_pct=gap_vs_best_known(r["primal_bound"], solu_entry))
            results.append(r)
            log(f"    -> status={r['status']}  wall={r['wall_time_s']}s  "
                f"peak_mem={r['peak_mem_mb']}MB  nodes={r['nodes']}")

    if not results:
        log("No results produced.")
        return

    csv_path = write_csv(results, results_dir)
    print_summary(results, csv_path, log_dir)


def _parse_solvers(spec):
    """'all' or a comma-separated subset, e.g. 'scip,cuopt'."""
    if spec == "all":
        return list(ALL_SOLVERS)
    names = [s.strip().lower() for s in spec.split(",") if s.strip()]
    bad = [n for n in names if n not in ALL_SOLVERS]
    if bad:
        raise SystemExit(f"Unknown solver(s): {', '.join(bad)}. "
                          f"Choose from: {', '.join(ALL_SOLVERS)}, or 'all'.")
    return names
