"""
Folder scan used to read back whatever instance files are actually on
disk under instance_dir (populated by instance_sources/download.py).
No network access at all.
"""

from ..logging_utils import log
from random import Random

def get_instances(args, instance_dir):
    files = sorted(instance_dir.rglob("*.mps*"))
    if not files:
        log(f"No instance files found under {instance_dir}.")
    rng = Random(args.seed)
    rng.shuffle(files)

    return files[: min(args.num_instances, len(files))]
