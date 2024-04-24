import os
import json
import sys
import matplotlib.pyplot as plt
import numpy as np
cols = ['b','g','r','c','m','y']
for path in sys.argv[1:]:
    outdir = os.path.join(path,'cov')
    print("##############################")
    print(f"Results for dir {outdir}:")
    for j, tool in enumerate(["cbmc","esbmc","seahorn"]):
        i = 1
        fname = f"{tool}_{i}batches.cov.json"
        branch_coverage = []
        line_coverage = []
        function_coverage = []
        while os.path.isfile(os.path.join(outdir,fname)):
            with open(os.path.join(outdir,fname), "r") as f:
                cov = json.load(f)
                print(f"Batch {fname}: b:{cov['branch_covered']}({cov['branch_percent']}%), l:{cov['line_covered']}({cov['line_percent']}%), f:{cov['function_covered']}({cov['function_percent']}%)")
                branch_coverage.append(cov["branch_percent"])
                line_coverage.append(cov["line_percent"])
                function_coverage.append(cov["function_percent"])
            i = i+1
            fname = f"{tool}_{i}batches.cov.json"
        print("---------------------------")
        x = np.arange(101)
        col = cols[j]
        plt.plot(x, branch_coverage, color=col, linestyle=":", label=f"{tool} b.c.")
        plt.plot(x, line_coverage, color=col,label=f"{tool} l.f.")
        plt.plot(x, function_coverage, color=col,linestyle="-", label=f"{tool} f.c.")
    plt.legend()
    plt.savefig(os.path.join(path, 'coverage.png'))
    plt.close()
    print("##############################")
