import os
import json
import sys
outdir = os.path.join(sys.argv[1],'cov')
for tool in ["cbmc","esbmc","seahorn"]:
    i = 0
    fname = f"{tool}_{0}batches.cov.json"
    while os.path.isfile(fname):
        with open(os.path.join('cov3','run0_0','cov',fname), "r") as f:
            cov = json.load(f)
            print(f"Batch {fname}: b:{cov['branch_covered']}({cov['branch_percent']}%), l:{cov['line_covered']}({cov['line_percent']}%), f:{cov['function_covered']}({cov['function_percent']}%)")
        i = i+1
        fname = f"{tool}_{0}batches.cov.json"
    print("---------------------------")