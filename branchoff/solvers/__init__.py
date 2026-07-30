"""
Each solver is fully self-contained in its own module (scip.py,
cplex.py): mode detection, Python-API runner template, CLI script
building, subprocess invocation, and log parsing all live together so
you can read/modify/extend one solver without touching the other.

Both modules expose the same small interface, used by runner.py:

    detect(...)          -> "cli" | "pyapi" | None
    write_pyapi_runner(workdir) -> Path
    run(...)             -> dict of result fields
"""
