"""
Runs a solver subprocess, captures its stdout+stderr to a log file, and
tracks peak RSS via /proc/<pid>/status (Linux only). Used identically
by both the SCIP and CPLEX runners, so it lives here rather than in
either solver module.
"""

import subprocess
import time


def run_with_monitor(cmd, stdin_path, log_path, hard_timeout_s):
    """Run cmd, capture stdout+stderr to log_path, track peak RSS via
    /proc/<pid>/status VmHWM. Returns (wall_seconds, peak_mem_mb, timed_out)."""
    start = time.time()
    peak_kb = 0
    timed_out = False

    with open(log_path, "w") as logf:
        stdin_f = open(stdin_path, "r") if stdin_path else subprocess.DEVNULL
        try:
            proc = subprocess.Popen(
                cmd, stdin=stdin_f, stdout=logf, stderr=subprocess.STDOUT
            )
        finally:
            if stdin_path:
                stdin_f.close()

        try:
            while True:
                ret = proc.poll()
                try:
                    with open(f"/proc/{proc.pid}/status") as f:
                        for line in f:
                            if line.startswith("VmHWM:"):
                                kb = int(line.split()[1])
                                peak_kb = max(peak_kb, kb)
                                break
                except FileNotFoundError:
                    pass  # process already gone
                if ret is not None:
                    break
                if time.time() - start > hard_timeout_s:
                    timed_out = True
                    proc.kill()
                    proc.wait()
                    break
                time.sleep(0.5)
        except KeyboardInterrupt:
            proc.kill()
            raise

    wall = time.time() - start
    return wall, peak_kb / 1024.0, timed_out
