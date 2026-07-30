import re
from pathlib import Path

from .logging_utils import log


def print_system_banner(threads, mem_limit_mb):
    log("=" * 78)
    log("SYSTEM INFO")
    try:
        with open("/proc/cpuinfo") as f:
            model = None
            ncores = 0
            for line in f:
                if line.startswith("model name") and model is None:
                    model = line.split(":", 1)[1].strip()
                if line.startswith("processor"):
                    ncores += 1
        log(f"  CPU: {model}  ({ncores} logical cores detected)")
    except Exception:
        pass
    try:
        with open("/proc/meminfo") as f:
            for line in f:
                if line.startswith("MemTotal:"):
                    kb = int(line.split()[1])
                    log(f"  RAM total: {kb / 1024 / 1024:.1f} GiB")
                    break
    except Exception:
        pass
    try:
        rel = Path("/etc/os-release").read_text()
        m = re.search(r'PRETTY_NAME="([^"]+)"', rel)
        if m:
            log(f"  OS: {m.group(1)}")
    except Exception:
        pass
    log(f"  Requested solver threads: {threads}")
    log(f"  Per-run RAM ceiling given to each solver: {mem_limit_mb} MB")
    log("=" * 78)
