import os
import json
import sys
import matplotlib.pyplot as plt
import numpy as np

def get_average(coverages, key):
    return np.average(list(map(lambda cov: cov[key], coverages)))

cols = ['b','g','r','c','m','y']
tools = ["cbmc","esbmc","seahorn"]
num_baselines = int(sys.argv[2])
total_runs = int(sys.argv[3])
all_coverages = [{tool: {'f': [], 'b': [], 'l': []} for tool in tools} for _ in range(num_baselines)]
for baseline in range(num_baselines):
    end_coverages = {tool: [] for tool in tools}
    for run in range(baseline,total_runs,num_baselines):
        path = os.path.join(sys.argv[1],f'run{run}_0')
        plt.ylim(0,100)
        plt.xlim(0,99)
        plt.ylabel("Coverage (%)")
        plt.xlabel("Number of batches (100 mazes per batch)")
        outdir = os.path.join(path,'cov')
        print(f"Results for dir {outdir}:")
        x = np.arange(100)
        for j, tool in enumerate(tools):
            i = 1
            fname = f"{tool}_{i}batches.cov.json"
            branch_coverage = []
            line_coverage = []
            function_coverage = []
            while os.path.isfile(os.path.join(outdir,fname)):
                with open(os.path.join(outdir,fname), "r") as f:
                    cov = json.load(f)
                    branch_coverage.append(cov["branch_percent"])
                    line_coverage.append(cov["line_percent"])
                    function_coverage.append(cov["function_percent"])
                i = i+1
                fname = f"{tool}_{i}batches.cov.json"
            end_coverages[tool].append(cov)
            all_coverages[baseline][tool]['b'].append(branch_coverage)
            all_coverages[baseline][tool]['l'].append(line_coverage)
            all_coverages[baseline][tool]['f'].append(function_coverage)
            print(f"Batch {fname}: b:{cov['branch_covered']}({cov['branch_percent']}%), l:{cov['line_covered']}({cov['line_percent']}%), f:{cov['function_covered']}({cov['function_percent']}%)")
            print("---------------------------")
            col = cols[j]
            plt.plot(x, branch_coverage, color=col, linestyle=":", label=f"{tool} b.c.")
            plt.plot(x, line_coverage, color=col,label=f"{tool} l.f.")
            plt.plot(x, function_coverage, color=col,linestyle="-", label=f"{tool} f.c.")
        plt.legend()
        plt.savefig(os.path.join(path, 'coverage.png'))
        plt.close()

        print("##############################")

    print(f"Final averages for baseline {baseline}:")
    for tool in tools:
        tool_end_coverage  = end_coverages[tool]
        print(f"{tool}: b:{get_average(tool_end_coverage ,'branch_covered')}({get_average(tool_end_coverage ,'branch_percent')}%), l:{get_average(tool_end_coverage ,'line_covered')}({get_average(tool_end_coverage ,'line_percent')}%), f:{get_average(tool_end_coverage ,'function_covered')}({get_average(tool_end_coverage ,'function_percent')}%)")

for baseline in range(num_baselines):
    for covtype in ('b','l','f'):
        for tool in tools:
            type_coverage = all_coverages[baseline][tool][covtype]
            all_coverages[baseline][tool][covtype] = [np.average([run[i] for run in type_coverage]) for i in range(len(type_coverage[0]))]
for tool in tools:
    plt.ylim(0,100)
    plt.xlim(0,99)
    plt.ylabel("Coverage (%)")
    plt.xlabel("Number of batches (100 mazes per batch)")
    x = np.arange(100)
    for baseline in range(num_baselines):
        col = cols[num_baselines]
        plt.plot(x, all_coverages[baseline][tool]['b'], color=col, linestyle=":", label=f"Baseline {baseline} b.c.")
        plt.plot(x, all_coverages[baseline][tool]['l'], color=col,label=f"Baseline {baseline} l.f.")
        plt.plot(x, all_coverages[baseline][tool]['f'], color=col,linestyle="-", label=f"Baseline {baseline} f.c.")
    plt.legend()
    plt.savefig(os.path.join(sys.argv[1], f'{tool}_coverage.png'))
    plt.close()