"""
Instance source: download.

Pulls instances live using the third-party `MIPLIBing` package
(pip install MIPLIBing), filtered by decision-variable count -- a
proxy for problem complexity that's more meaningful than raw file
size. Requires internet access to miplib.zib.de.

    pip install MIPLIBing --break-system-packages

MIPLIBing is asked to write into <workdir>/instances (via
local_directory=), but its own reported `inst.path` values aren't
fully trusted here: if a file actually landed somewhere else (a
relative path, MIPLIBing's own cache dir, etc.) it is copied into
<workdir>/instances so *every* downloaded file ends up in one place.
After that, the folder is read back from disk (reusing local.py's
scan) and instances are sampled from what's actually there -- so
what you get is always exactly what's on disk, not just what the
library claims it wrote.
"""

import random
import shutil
from pathlib import Path

from ..logging_utils import log
from ..http_utils import install_redirect_handler
from .local import get_instances as _scan_folder


def get_instances(args, instance_dir):
    try:
        from MIPLIBing import MIPLIBing, Libraries
    except ImportError:
        raise SystemExit(
            "downloading instances requires the MIPLIBing package. "
            "Install it with: pip install MIPLIBing --break-system-packages"
        )

    # MIPLIBing uses pandas.read_html() internally, which calls plain
    # urllib.urlopen(). miplib.zib.de replies with an HTTP 308 that
    # older urllib/Python versions don't follow automatically, causing
    # an HTTPError deep inside pandas. install_opener() is process-global,
    # so installing our redirect-following handler here patches that
    # urlopen() call too -- without needing to touch MIPLIBing's code.
    install_redirect_handler()

    instance_dir = instance_dir.resolve()
    instance_dir.mkdir(parents=True, exist_ok=True)

    log(f"Fetching MIPLIB instances (min_var={args.min_var}, "
        f"max_var={args.max_var}, seed={args.seed}) ...")
    log(f"Downloaded files will be collected under: {instance_dir}")

    mip = MIPLIBing(
        library=Libraries.MIPLIB2017_Benchmark,
        local_directory=str(instance_dir),
        verbose=True,
    )

    instances = mip.get_instances(min_var=args.min_var, max_var=args.max_var)
    if not instances:
        raise SystemExit("No instances found matching the variable criteria.")

    valid_names = {_instance_name(inst) for inst in instances}

    # Anything MIPLIBing reports outside instance_dir gets copied in,
    # so nothing goes missing in some other cache directory.
    _consolidate_into(instances, instance_dir)

    # Read back the folder from disk -- this is the source of truth,
    # not whatever paths the library happened to hand back.
    on_disk = _scan_folder(args, instance_dir)
    matched = [p for p in on_disk if p.name.split(".")[0] in valid_names]

    pool = matched or on_disk
    if not pool:
        raise SystemExit(
            f"MIPLIBing reported {len(instances)} matching instance(s) but "
            f"none could be found on disk under {instance_dir}. Check "
            f"MIPLIBing's own output above for where it actually wrote "
            f"files, then either move them into {instance_dir} yourself "
            f"or point --workdir at their parent directory."
        )
    if not matched:
        log(f"  WARNING: couldn't match downloaded filenames to the "
            f"filtered instance list by name -- sampling from all "
            f"{len(pool)} .mps* file(s) found in {instance_dir} instead.")

    random.seed(args.seed)
    picked = random.sample(pool, min(args.num_instances, len(pool)))

    log(f"{len(picked)} instance file(s) selected from {instance_dir}:")
    for p in picked:
        log(f"  {p}")

    return picked


def _instance_name(inst):
    name = getattr(inst, "name", None)
    if name:
        return str(name)
    path = getattr(inst, "path", None)
    if path:
        return Path(path).name.split(".")[0]
    return str(inst).split(".")[0]


def _consolidate_into(instances, instance_dir):
    """Copy any reported instance file that isn't already under
    instance_dir into it, so every download ends up in one place."""
    for inst in instances:
        reported = getattr(inst, "path", None)
        if not reported:
            continue
        reported = Path(reported)
        if not reported.is_file():
            continue
        if instance_dir in reported.resolve().parents:
            continue
        dest = instance_dir / reported.name
        if not dest.exists():
            log(f"  found '{reported}' outside {instance_dir} -- "
                f"copying it in")
            shutil.copy2(reported, dest)
