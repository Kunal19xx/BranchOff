"""
Pluggable instance sourcing.

Two sources are available, selected with --source:

  local     scan args.workdir/instances for already-downloaded *.mps*
            files (default -- use whatever you've already cached).
  download  pull instances live via the MIPLIBing package, filtered
            by decision-variable count.

Both return a list of local filesystem paths ready to hand to a solver.
Add a new source by dropping a module in this package with a
`get_instances(args, instance_dir) -> list[Path]` function and
registering it in SOURCES below.
"""

from .local import get_instances as _local_get_instances
from .download import get_instances as _download_get_instances

SOURCES = {
    "local": _local_get_instances,
    "download": _download_get_instances,
}


def get_instances(args, instance_dir, source='download'):
# def get_instances(args, instance_dir):
    try:
        fn = SOURCES[source]
    except KeyError:
        raise SystemExit(
            f"Unknown --source '{source}'. Available: {', '.join(SOURCES)}"
        )
    return fn(args, instance_dir)
