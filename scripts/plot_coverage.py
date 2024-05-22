import os
import json
import sys
import matplotlib.pyplot as plt
import numpy as np

def get_average(coverages, key):
    return np.average(list(map(lambda cov: cov[key], coverages)))

cols = ['b','g','c','r','m','y']
linestyles = ['-',':','--','-.']
tools = ["cbmc","esbmc","seahorn"]
covtypes = {'l': 'line', 'b': 'branch', 'f': 'function'}
baselines = ["Fuzzle", "Fuzzle + SMT", "Minotaur 1x1", "Minotaur"]
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
            col = cols[j]
            x = np.arange(len(branch_coverage))
            plt.plot(x, branch_coverage, color=col, linestyle=":", label=f"{tool} b.c.")
            plt.plot(x, line_coverage, color=col,label=f"{tool} l.f.")
            plt.plot(x, function_coverage, color=col,linestyle="-", label=f"{tool} f.c.")
        plt.legend()
        plt.savefig(os.path.join(path, 'coverage.png'))
        plt.close()

        print("##############################")

    print(f"Final averages for baseline {baselines[baseline]}:")
    for tool in tools:
        tool_end_coverage  = end_coverages[tool]
        print(f"{tool}: {covtypes['b']}:{get_average(tool_end_coverage ,'branch_covered')}({get_average(tool_end_coverage ,'branch_percent'):.1f}%), {covtypes['l']}:{get_average(tool_end_coverage ,'line_covered')}({get_average(tool_end_coverage ,'line_percent'):.1f}%), {covtypes['f']}:{get_average(tool_end_coverage ,'function_covered')}({get_average(tool_end_coverage ,'function_percent'):.1f}%)")


for baseline in range(num_baselines):
    for covtype in ('b','l','f'):
        for tool in tools:
            type_coverage = all_coverages[baseline][tool][covtype]
            all_coverages[baseline][tool][covtype] = [np.average([run[i] for run in type_coverage]) for i in range(min([len(c) for c in type_coverage]))]

for tool in tools:
    for covtype in ('b','l','f'):
        plt.xlim(0,99)
        plt.ylabel("Coverage (%)", fontsize=18)
        plt.xlabel("Number of batches",  fontsize=18)
        for baseline in range(num_baselines):
            if baseline == 2:
                continue
            col = cols[baseline]
            lin = linestyles[baseline]
            x = np.arange(len(all_coverages[baseline][tool]['b']))
            plt.plot(x, all_coverages[baseline][tool][covtype], color=col, linestyle=lin, label=f"{baselines[baseline]}")
        plt.legend(loc="lower right" if tool=='seahorn' else "center right", fontsize=18)
        plt.savefig(os.path.join(sys.argv[1], f'{tool}_{covtypes[covtype]}_coverage.png'))
        plt.close()