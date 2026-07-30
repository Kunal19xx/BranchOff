"""
Everything CPLEX-specific: availability detection, the `cplex` Python
module runner script, CLI script building, subprocess invocation, and
solver-log parsing. Self-contained -- doesn't import anything from
scip.py.
"""

import re
import shutil
import subprocess
import sys

from ..monitor import run_with_monitor
from ..logging_utils import log

BINARY_NAME = "cplex"
MODULE_NAME = "cplex"

PYAPI_RUNNER_SOURCE = '''
import sys, time

def main():
    mps_path = sys.argv[1]
    threads = int(sys.argv[2])
    time_limit = int(sys.argv[3])
    mem_limit_mb = int(sys.argv[4])

    import cplex
    c = cplex.Cplex(mps_path)

    def trysetp(fn):
        try:
            fn()
        except Exception:
            pass

    trysetp(lambda: c.parameters.threads.set(threads))
    trysetp(lambda: c.parameters.timelimit.set(time_limit))
    trysetp(lambda: c.parameters.workmem.set(max(512, mem_limit_mb // 4)))
    trysetp(lambda: c.parameters.mip.limits.treememory.set(mem_limit_mb))
    trysetp(lambda: c.parameters.mip.strategy.file.set(2))
    trysetp(lambda: c.parameters.mip.display.set(2))

    start = time.time()
    try:
        c.solve()
    except Exception as e:
        print("MIP - solve() raised an exception: %s" % e)
        return
    elapsed = time.time() - start

    try:
        status = c.solution.get_status_string()
    except Exception:
        status = "unknown"
    print("MIP - %s" % status)

    try:
        obj = c.solution.get_objective_value()
        print("Objective =  %r" % obj)
    except Exception:
        pass

    nodes = None
    for getter in (
        lambda: c.solution.progress.get_num_nodes_processed(),
        lambda: c.solution.MIP.get_num_nodes(),
    ):
        try:
            nodes = getter()
            break
        except Exception:
            continue
    line = "Solution time =   %.2f sec." % elapsed
    if nodes is not None:
        line += "  Nodes = %d" % nodes
    print(line)

    try:
        gap = c.solution.MIP.get_mip_relative_gap() * 100.0
        print("gap = %.4f%%," % gap)
    except Exception:
        pass

if __name__ == "__main__":
    main()
'''


def write_pyapi_runner(workdir):
    path = workdir / "cplex_pyapi_runner.py"
    path.write_text(PYAPI_RUNNER_SOURCE)
    return path


def detect_mode(python_exe=None):
    """Returns 'cli' if the `cplex` binary is on PATH, 'pyapi' if the
    `cplex` python module is importable under python_exe instead, or
    None if neither is available."""
    if shutil.which(BINARY_NAME):
        return "cli"
    python_exe = python_exe or sys.executable
    try:
        r = subprocess.run(
            [python_exe, "-c", f"import {MODULE_NAME}"],
            capture_output=True, timeout=20,
        )
        if r.returncode == 0:
            return "pyapi"
    except Exception:
        pass
    return None


def report_mode(python_exe=None):
    mode = detect_mode(python_exe)
    if mode == "cli":
        log(f"  CPLEX: found `{BINARY_NAME}` binary on PATH -- using CLI mode")
    elif mode == "pyapi":
        log(f"  CPLEX: no `{BINARY_NAME}` binary on PATH, but "
            f"`{MODULE_NAME}` is importable under {python_exe or sys.executable} "
            f"-- using Python-API mode")
    else:
        log(f"  CPLEX: WARNING -- neither `{BINARY_NAME}` binary nor "
            f"`{MODULE_NAME}` python module found under "
            f"{python_exe or sys.executable}. Runs for this solver will be "
            f"skipped. If the cplex module lives in a different venv, "
            f"point --cplex-python at it.")
    return mode


def build_cli_script(mps_path, threads, time_limit, mem_limit_mb):
    # workmem: RAM for active working storage before spilling to disk.
    # treememory: hard cap on total B&B tree memory (MB) -- once hit,
    # CPLEX writes nodes to disk (strategy file 2) instead of crashing.
    workmem = max(2024, mem_limit_mb // 4)
    lines = [
        f"read {mps_path}",
        f"set threads {threads}",
        f"set timelimit {time_limit}",
        f"set workmem {workmem}",
        f"set mip limits treememory {mem_limit_mb}",
        "set mip strategy file 2",
        "set mip display 2",
        "optimize",
        "display solution objective",
        "quit",
    ]
    return "\n".join(lines) + "\n"


def run(name, mps_path, threads, time_limit, mem_limit_mb,
        instance_dir, log_dir, solver_mode, pyapi_runner_path,
        python_exe=None):
    log_path = log_dir / f"{name}.cplex.log"
    if solver_mode == "cli":
        script_path = instance_dir / f"{name}.cplex.cmd"
        script_path.write_text(
            build_cli_script(mps_path, threads, time_limit, mem_limit_mb)
        )
        cmd = ["cplex"]
        stdin_path = script_path
    else:  # pyapi (cplex python module)
        cmd = [python_exe or sys.executable, str(pyapi_runner_path),
               str(mps_path), str(threads), str(time_limit),
               str(mem_limit_mb)]
        stdin_path = None

    wall, peak_mb, timed_out = run_with_monitor(
        cmd, stdin_path, log_path, hard_timeout_s=time_limit + 120
    )
    text = log_path.read_text(errors="replace")
    return parse_log(text, wall, peak_mb, timed_out)


def parse_log(text, wall, peak_mb, timed_out):
    status_line = None
    for m in re.finditer(r"^MIP\s*-\s*(.+)$", text, re.MULTILINE):
        status_line = m.group(1).strip()  # keep the last one

    def find(pat, cast=str, default=None):
        m = re.search(pat, text)
        if not m:
            return default
        try:
            return cast(m.group(1))
        except Exception:
            return m.group(1)

    obj = find(r"Objective\s*=\s*([\-0-9.eE+]+)", float)
    sol_time = find(r"Solution time\s*=\s*([\d.]+)\s*sec", float, wall)
    nodes = find(r"Nodes\s*=\s*(\d+)", int)
    gap = find(r"gap\s*=\s*([\-0-9.eE]+)\s*%", str)

    return {
        "status": status_line or "unknown/parse-failed",
        "wall_time_s": round(wall, 2),
        "solver_reported_time_s": sol_time,
        "peak_mem_mb": round(peak_mb, 1),
        "nodes": nodes,
        "primal_bound": obj,
        "dual_bound": None,
        "reported_gap_pct": gap,
        "timed_out_hard": timed_out,
    }
