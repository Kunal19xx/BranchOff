import csv
from datetime import datetime

from .logging_utils import log

FIELDNAMES = [
    "instance", "solver", "threads", "time_limit_s",
    "status", "wall_time_s", "solver_reported_time_s",
    "peak_mem_mb", "nodes", "primal_bound", "dual_bound",
    "reported_gap_pct", "gap_vs_best_known_pct", "timed_out_hard",
]


def gap_vs_best_known(obj, solu_entry):
    if obj is None or solu_entry is None:
        return None
    status, best = solu_entry
    if best is None or best == 0:
        return None
    return round(abs(obj - best) / max(1e-10, abs(best)) * 100, 4)


def write_csv(results, results_dir):
    ts = datetime.now().strftime("%Y%m%d_%H%M%S")
    csv_path = results_dir / f"results_{ts}.csv"
    with open(csv_path, "w", newline="") as f:
        w = csv.DictWriter(f, fieldnames=FIELDNAMES)
        w.writeheader()
        for r in results:
            w.writerow({k: r.get(k) for k in FIELDNAMES})
    return csv_path


def print_summary(results, csv_path, log_dir):
    log("=" * 78)
    log(f"Results written to: {csv_path}")
    log(f"Raw solver logs in: {log_dir}")
    log("=" * 78)
    log("SUMMARY")
    header = (f"{'instance':<28}{'solver':<8}{'status':<28}"
              f"{'wall(s)':>10}{'mem(MB)':>10}{'nodes':>10}")
    log(header)
    log("-" * len(header))
    for r in results:
        log(f"{r['instance']:<28}{r['solver']:<8}{str(r['status'])[:26]:<28}"
            f"{r['wall_time_s']:>10}{r['peak_mem_mb']:>10}{str(r['nodes']):>10}")
