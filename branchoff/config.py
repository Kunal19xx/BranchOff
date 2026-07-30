"""
All constants and default values live here so nothing else in the
package hardcodes a URL, header, or default number.
"""

MIPLIB_BASE = "https://miplib.zib.de"
BENCHMARK_TEST_URL = f"{MIPLIB_BASE}/downloads/benchmark-v2.test"
SOLU_URL = f"{MIPLIB_BASE}/downloads/miplib2017-v36.solu"
INSTANCE_URL_TMPL = MIPLIB_BASE + "/WebData/instances/{name}.mps.gz"

# miplib.zib.de blocks/mishandles default urllib UAs -- pretend to be a browser.
USER_AGENT = (
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
    "(KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
)

DEFAULTS = dict(
    threads=32,
    mem_limit_mb=13000,
    time_limit=900,
    num_instances=6,
    size_min_kb=300,
    size_max_kb=4000,
    min_var=1000,
    max_var=50000,
    seed=42,
    solvers="all",
    scip_mode="concurrent",
)
