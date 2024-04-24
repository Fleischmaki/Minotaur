from numpy import average
import pandas
import sys
import os
run_directory = sys.argv[1]
df = pandas.read_csv(os.path.join(run_directory,'times'), header='infer')
num_tests = int(sys.argv[2])
total_runs = len(df.iloc[:,1])
runs_per_test = num_tests/total_runs

for test in range(num_tests):
    avg = (average(df.iloc[test::num_tests,1]))
    tool_times = []
    found = 0
    for run in range(test,total_runs,num_tests):
        summary = pandas.read_csv(os.path.join(run_directory, f'run{run}_{0}','summary.csv'), header='infer')
        tool_times.append(sum(summary['runtime'][::]))
        if any(map(lambda res: res in ('fn', 'fp'), summary['status'][::])):
            found += 1

    avg_tool_time = average(tool_times)
    print(f"Test {test}:\tTotal time {avg:.2f},\t Tool time {avg_tool_time:.2f},\tPA% = {avg_tool_time / avg:.3f}\t found {found}/5")
