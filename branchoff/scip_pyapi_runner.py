
import sys

def main():
    mps_path = sys.argv[1]
    threads = int(sys.argv[2])
    time_limit = int(sys.argv[3])
    mem_limit_mb = int(sys.argv[4])
    mode = sys.argv[5]

    from pyscipopt import Model
    m = Model()
    m.readProblem(mps_path)

    def trysetp(fn):
        try:
            fn()
        except Exception:
            pass

    trysetp(lambda: m.setParam("limits/time", float(time_limit)))
    trysetp(lambda: m.setParam("limits/memory", float(mem_limit_mb)))
    trysetp(lambda: m.setParam("parallel/maxnthreads", threads))
    trysetp(lambda: m.setParam("lp/threads", threads))

    if mode == "concurrent":
        try:
            m.solveConcurrent()
        except Exception as e:
            print("SCIP Status        : concurrent solve unavailable (%s), "
                  "falling back to single-thread optimize" % e)
            m.optimize()
    else:
        m.optimize()

    try:
        print("SCIP Status        : %s" % m.getStatus())
    except Exception:
        pass
    try:
        print("Solving Time (sec) : %.2f" % m.getSolvingTime())
    except Exception:
        pass
    try:
        print("Nodes (total)      : %d" % m.getNNodes())
    except Exception:
        pass
    try:
        print("Primal Bound       : %r" % m.getPrimalbound())
    except Exception:
        pass
    try:
        print("Dual Bound         : %r" % m.getDualbound())
    except Exception:
        pass
    try:
        print("Gap                : %.4f %%" % (m.getGap() * 100.0))
    except Exception:
        pass

if __name__ == "__main__":
    main()
