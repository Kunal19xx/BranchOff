
import sys, time

def main():
    mps_path = sys.argv[1]
    threads = int(sys.argv[2])
    time_limit = int(sys.argv[3])
    mem_limit_mb = int(sys.argv[4])

    import cplex
    c = cplex.Cplex(mps_path)

    def trysetp(fn):
        try:
            fn()
        except Exception:
            pass

    trysetp(lambda: c.parameters.threads.set(threads))
    trysetp(lambda: c.parameters.timelimit.set(time_limit))
    trysetp(lambda: c.parameters.workmem.set(max(512, mem_limit_mb // 4)))
    trysetp(lambda: c.parameters.mip.limits.treememory.set(mem_limit_mb))
    trysetp(lambda: c.parameters.mip.strategy.file.set(2))
    trysetp(lambda: c.parameters.mip.display.set(2))

    start = time.time()
    try:
        c.solve()
    except Exception as e:
        print("MIP - solve() raised an exception: %s" % e)
        return
    elapsed = time.time() - start

    try:
        status = c.solution.get_status_string()
    except Exception:
        status = "unknown"
    print("MIP - %s" % status)

    try:
        obj = c.solution.get_objective_value()
        print("Objective =  %r" % obj)
    except Exception:
        pass

    nodes = None
    for getter in (
        lambda: c.solution.progress.get_num_nodes_processed(),
        lambda: c.solution.MIP.get_num_nodes(),
    ):
        try:
            nodes = getter()
            break
        except Exception:
            continue
    line = "Solution time =   %.2f sec." % elapsed
    if nodes is not None:
        line += "  Nodes = %d" % nodes
    print(line)

    try:
        gap = c.solution.MIP.get_mip_relative_gap() * 100.0
        print("gap = %.4f%%," % gap)
    except Exception:
        pass

if __name__ == "__main__":
    main()
