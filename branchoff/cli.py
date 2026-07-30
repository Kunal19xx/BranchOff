import argparse
from pathlib import Path

from .config import DEFAULTS
from .runner import run_benchmark


PROJECT_DIR = Path(__file__).resolve().parent

EPILOG = """
USAGE
-----
  python3 -m branchoff                              # sane defaults, downloads instances
  python3 -m branchoff --num-instances 10 --time-limit 1200
  python3 -m branchoff --solvers scip                # SCIP only
  python3 -m branchoff --solvers scip,cuopt          # SCIP + cuOpt, skip CPLEX
  python3 -m branchoff --dry-run                     # just pick instances

Instances are always downloaded fresh from MIPLIB into
<workdir>/instances -- see that folder if you want to inspect or
reuse the raw .mps.gz files directly.

Results land in ~/branchoff/results/results_<timestamp>.csv plus
full raw solver logs per run for manual inspection.
"""


def build_parser():
     ap = argparse.ArgumentParser(
          description="Stress test SCIP vs CPLEX on real MIPLIB 2017 "
                         "benchmark instances.",
          formatter_class=argparse.RawDescriptionHelpFormatter,
          epilog=EPILOG,
     )
     ap.add_argument("--threads", type=int, default=DEFAULTS["threads"],
                         help="threads given to each solver (default: %(default)s)")
     ap.add_argument("--mem-limit-mb", type=int, default=DEFAULTS["mem_limit_mb"],
                         help="hard RAM ceiling per solver run, in MB "
                              "(default: %(default)s)")
     ap.add_argument("--time-limit", type=int, default=DEFAULTS["time_limit"],
                         help="per-instance, per-solver time limit in seconds "
                              "(default: %(default)s)")
     ap.add_argument("--num-instances", type=int, default=DEFAULTS["num_instances"],
                         help="how many MIPLIB instances to download and run "
                              "(default: %(default)s)")
     ap.add_argument("--size-min-kb", type=int, default=DEFAULTS["size_min_kb"],
                         help="min compressed .mps.gz size to consider, KB "
                              "(default: %(default)s)")
     ap.add_argument("--size-max-kb", type=int, default=DEFAULTS["size_max_kb"],
                         help="max compressed .mps.gz size to consider, KB "
                              "(default: %(default)s)")
     ap.add_argument("--solvers", default=DEFAULTS["solvers"],
                         help="'all' (default) or a comma-separated subset of "
                              "scip,cplex,cuopt -- e.g. --solvers scip,cuopt")
     ap.add_argument("--scip-mode", choices=["concurrent", "optimize"],
                         default=DEFAULTS["scip_mode"],
                         help="'concurrent' actually uses --threads cores "
                              "(SCIP's concurrentopt); 'optimize' is the "
                              "classic ~single-threaded SCIP search "
                              "(default: %(default)s)")
     ap.add_argument("--seed", type=int, default=DEFAULTS["seed"])
     ap.add_argument("--workdir", type=Path,
                         default=PROJECT_DIR,
                         help="instances/logs/results all live under here "
                              "(default: %(default)s)")
     ap.add_argument("--dry-run", action="store_true",
                         help="only select+download instances, don't solve")
     ap.add_argument("--min-var", type=int, default=DEFAULTS["min_var"],
                         help="minimum decision variables")
     ap.add_argument("--max-var", type=int, default=DEFAULTS["max_var"],
                         help="maximum decision variables")
     ap.add_argument("--source", type=str, default='local',
                         help=['local', 'download'])
     return ap


def main(argv=None):
    args = build_parser().parse_args(argv)
    run_benchmark(args)
