"""
Everything cuOpt-specific: availability detection, CLI invocation,
subprocess execution, and solver-log parsing.

Self-contained -- doesn't import anything from other solver modules.
"""

import re
import shutil

from ..monitor import run_with_monitor
from ..logging_utils import log

BINARY_NAME = "cuopt_cli"


def detect_mode():
    """Returns 'cli' if cuopt_cli is available, otherwise None."""
    return "cli" if shutil.which(BINARY_NAME) else None


def report_mode():
    mode = detect_mode()

    if mode == "cli":
        log(f"  cuOpt: found `{BINARY_NAME}` binary on PATH -- using CLI mode")
    else:
        log(
            f"  cuOpt: WARNING -- `{BINARY_NAME}` not found. "
            "Runs for this solver will be skipped."
        )

    return mode


def build_command(
    mps_path,
    threads,
    time_limit,
    log_path,
    solution_path,
):
    return [
        BINARY_NAME,
        str(mps_path),
        "--num-cpu-threads", str(threads),
        "--time-limit", str(time_limit),
        "--mip-relative-gap", "0.0001",
        "--mip-absolute-gap", "1e-10",
        "--mip-integrality-tolerance", "1e-5",
        "--log-file", str(log_path),
        "--solution-file", str(solution_path),
        "--log-to-console", "false",
        "--presolve" , "2",
        "--method", "2",                        
        # "--pdlp-solver-mode", "1",
        "--pdlp-precision", "single" ,
        # "--mip-determinism-mode", "1",
        # "--random-seed", "42",
        # "--cudss-deterministic",  "true",   
        "--work-limit", "inf",         
        "--mip-cut-passes", "100",
        "--mip-mixed-integer-rounding-cuts", "1",
        "--mip-mixed-integer-gomory-cuts", "1",
        "--mip-knapsack-cuts", "1",
        "--mip-clique-cuts", "1",
        "--mip-implied-bound-cuts", "1",
        "--mip-strong-chvatal-gomory-cuts", "1",
        "--mip-reduced-cost-strengthening", "1",

        "--mip-batch-pdlp-strong-branching", "1",
        "--mip-batch-pdlp-reliability-branching", "1",
        "--mip-reliability-branching", "1",

        "--mip-scaling", "1",

        
    ]


def run(
    name,
    mps_path,
    threads,
    time_limit,
    mem_limit_mb,      # unused (reserved for interface compatibility)
    instance_dir,
    log_dir,
    solver_mode,
    pyapi_runner_path=None,
):
    log_path = log_dir / f"{name}.cuopt.log"
    solution_path = log_dir / f"{name}.cuopt.sol"

    cmd = build_command(
        mps_path,
        threads,
        time_limit,
        log_path,
        solution_path,
    )

    wall, peak_mb, timed_out = run_with_monitor(
        cmd,
        stdin_path=None,
        log_path=log_path,
        hard_timeout_s=time_limit + 120,
    )

    text = log_path.read_text(errors="replace")

    return parse_log(
        text=text,
        wall=wall,
        peak_mb=peak_mb,
        timed_out=timed_out,
    )


def parse_log(text, wall, peak_mb, timed_out):
    """
    Regexes are intentionally permissive because cuOpt's
    logging format may change slightly between releases.
    """

    def find(pattern, cast=str, default=None, flags=re.I):
        m = re.search(pattern, text, flags)
        if not m:
            return default
        try:
            return cast(m.group(1))
        except Exception:
            return m.group(1)

    status = (
        find(r"Status\s*:\s*(.+)")
        or find(r"Termination\s*:\s*(.+)")
        or find(r"Result\s*:\s*(.+)")
        or "unknown/parse-failed"
    )

    obj = (
        find(r"Objective(?: value)?\s*[:=]\s*([\-+0-9.eE]+)", float)
        or find(r"Best objective\s*[:=]\s*([\-+0-9.eE]+)", float)
    )

    dual = (
        find(r"Best bound\s*[:=]\s*([\-+0-9.eE]+)", float)
        or find(r"Dual bound\s*[:=]\s*([\-+0-9.eE]+)", float)
    )

    nodes = (
        find(r"Nodes(?: processed)?\s*[:=]\s*(\d+)", int)
        or find(r"Node count\s*[:=]\s*(\d+)", int)
    )

    gap = (
        find(r"Gap\s*[:=]\s*([\-+0-9.eE]+)\s*%", str)
        or find(r"Relative gap\s*[:=]\s*([\-+0-9.eE]+)", str)
    )

    solver_time = (
        find(r"Solve time\s*[:=]\s*([0-9.]+)", float)
        or find(r"Elapsed time\s*[:=]\s*([0-9.]+)", float)
        or wall
    )

    return {
        "status": status,
        "wall_time_s": round(wall, 2),
        "solver_reported_time_s": solver_time,
        "peak_mem_mb": round(peak_mb, 1),
        "nodes": nodes,
        "primal_bound": obj,
        "dual_bound": dual,
        "reported_gap_pct": gap,
        "timed_out_hard": timed_out,
    }