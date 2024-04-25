from numpy import NaN, average
import pandas
import sys
import os
run_directory = sys.argv[1]
df = pandas.read_csv(os.path.join(run_directory,'times'), header='infer')
num_tests = int(sys.argv[2])
total_runs = len(df.iloc[:,1])

for test_id in range(num_tests):
    tool_times = []
    found = [False] * total_runs
    for run in range(test_id, total_runs, num_tests):
        summary = pandas.read_csv(os.path.join(run_directory, f'run{run}_{0}','summary.csv'), header='infer')
        if any(map(lambda res: res in ('fn', 'fp'), summary['status'][::])):
            found[run] = True
            tool_times.append(sum(summary['runtime'][::]))
    avg = average(df.iloc[found,1])
    
    avg_tool_time = NaN if len(tool_times) == 0 else average(tool_times)

    print(f"Test {test_id}:\tTotal time {avg:.2f},\t Tool time {avg_tool_time:.0f},\tPA% = {100*avg_tool_time / avg:.1f}\t found {sum(found)}/5")
