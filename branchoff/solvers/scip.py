"""
Everything SCIP-specific: availability detection, the pyscipopt
Python-API runner script, CLI (.set/.cmd) script building, subprocess
invocation, and solver-log parsing. Self-contained -- doesn't import
anything from cplex.py.
"""

import re
import shutil
import subprocess
import sys

from ..monitor import run_with_monitor
from ..logging_utils import log

BINARY_NAME = "scip"
MODULE_NAME = "pyscipopt"

PYAPI_RUNNER_SOURCE = '''
import sys

def main():
    mps_path = sys.argv[1]
    threads = int(sys.argv[2])
    time_limit = int(sys.argv[3])
    mem_limit_mb = int(sys.argv[4])
    mode = sys.argv[5]

    from pyscipopt import Model
    m = Model()
    m.readProblem(mps_path)

    def trysetp(fn):
        try:
            fn()
        except Exception:
            pass

    trysetp(lambda: m.setParam("limits/time", float(time_limit)))
    trysetp(lambda: m.setParam("limits/memory", float(mem_limit_mb)))
    trysetp(lambda: m.setParam("parallel/maxnthreads", threads))
    trysetp(lambda: m.setParam("lp/threads", threads))

    if mode == "concurrent":
        try:
            m.solveConcurrent()
        except Exception as e:
            print("SCIP Status        : concurrent solve unavailable (%s), "
                  "falling back to single-thread optimize" % e)
            m.optimize()
    else:
        m.optimize()

    try:
        print("SCIP Status        : %s" % m.getStatus())
    except Exception:
        pass
    try:
        print("Solving Time (sec) : %.2f" % m.getSolvingTime())
    except Exception:
        pass
    try:
        print("Nodes (total)      : %d" % m.getNNodes())
    except Exception:
        pass
    try:
        print("Primal Bound       : %r" % m.getPrimalbound())
    except Exception:
        pass
    try:
        print("Dual Bound         : %r" % m.getDualbound())
    except Exception:
        pass
    try:
        print("Gap                : %.4f %%" % (m.getGap() * 100.0))
    except Exception:
        pass

if __name__ == "__main__":
    main()
'''


def write_pyapi_runner(workdir):
    path = workdir / "scip_pyapi_runner.py"
    path.write_text(PYAPI_RUNNER_SOURCE)
    return path


def detect_mode(python_exe=None):
    """Returns 'cli' if the `scip` binary is on PATH, 'pyapi' if
    pyscipopt is importable under python_exe instead, or None if
    neither is available."""
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
        log(f"  SCIP: found `{BINARY_NAME}` binary on PATH -- using CLI mode")
    elif mode == "pyapi":
        log(f"  SCIP: no `{BINARY_NAME}` binary on PATH, but "
            f"`{MODULE_NAME}` is importable under {python_exe or sys.executable} "
            f"-- using Python-API mode")
    else:
        log(f"  SCIP: WARNING -- neither `{BINARY_NAME}` binary nor "
            f"`{MODULE_NAME}` python module found under "
            f"{python_exe or sys.executable}. Runs for this solver will be "
            f"skipped. If pyscipopt lives in a different venv, point "
            f"--scip-python at it.")
    return mode


def build_params_file(param_path, threads, time_limit, mem_limit_mb):
    param_path.write_text(
        "\n".join([
            f"limits/time = {time_limit}",
            f"limits/memory = {mem_limit_mb}",
            f"parallel/maxnthreads = {threads}",
            f"parallel/minnthreads = {threads}",
        ]) + "\n"
    )


def build_cli_script(mps_path, param_path, mode):
    solve_cmd = "concurrentopt" if mode == "concurrent" else "optimize"
    return "\n".join([
        f"set load {param_path}",
        f"read {mps_path}",
        solve_cmd,
        "display statistics",
        "quit",
    ]) + "\n"


def run(name, mps_path, threads, time_limit, mem_limit_mb, mode,
        instance_dir, log_dir, solver_mode, pyapi_runner_path,
        python_exe=None):
    log_path = log_dir / f"{name}.scip.log"
    if solver_mode == "cli":
        script_path = instance_dir / f"{name}.scip.cmd"
        param_path = instance_dir / f"{name}.scip.set"
        build_params_file(param_path, threads, time_limit, mem_limit_mb)
        script_path.write_text(build_cli_script(mps_path, param_path, mode))
        cmd = ["scip", "-b", str(script_path)]
        stdin_path = None
    else:  # pyapi (pyscipopt)
        cmd = [python_exe or sys.executable, str(pyapi_runner_path),
               str(mps_path), str(threads), str(time_limit),
               str(mem_limit_mb), mode]
        stdin_path = None

    wall, peak_mb, timed_out = run_with_monitor(
        cmd, stdin_path, log_path, hard_timeout_s=time_limit + 120
    )
    text = log_path.read_text(errors="replace")
    return parse_log(text, wall, peak_mb, timed_out)


def parse_log(text, wall, peak_mb, timed_out):
    def find(pat, cast=str, default=None):
        m = re.search(pat, text)
        if not m:
            return default
        try:
            return cast(m.group(1))
        except Exception:
            return m.group(1)

    status = find(r"SCIP Status\s*:\s*(.+)", str, "unknown/parse-failed")
    solve_time = find(r"Solving Time \(sec\)\s*:\s*([\d.]+)", float, wall)
    nodes = find(r"Nodes\s*\(total\)\s*:\s*(\d+)", int)
    primal = find(r"Primal Bound\s*:\s*([\-0-9.eE+]+)", float)
    dual = find(r"Dual Bound\s*:\s*([\-0-9.eE+]+)", float)
    gap = find(r"Gap\s*:\s*([\-0-9.eE]+|infinite)\s*%", str)

    return {
        "status": status.strip() if status else status,
        "wall_time_s": round(wall, 2),
        "solver_reported_time_s": solve_time,
        "peak_mem_mb": round(peak_mb, 1),
        "nodes": nodes,
        "primal_bound": primal,
        "dual_bound": dual,
        "reported_gap_pct": gap,
        "timed_out_hard": timed_out,
    }
