## Recreating experiment results
All configuration files for the experiments are already provided in the experiment folder. 
The bug ids are the same as in Table 1 of the experiments section.
There are several types of experiments:

### Recreate bug
Configurations of the form recreate_AnalyzerBugid.conf.json (e.g. recreate_cpa1).
For 5 different seeds (1,2,3,4,5) Run tests until the bug is found on the corresponding version of the analyzer.
Will use multiple workers (default 5) to try and find the bug as quickly as possible.
Note that the found bugs might look different from the ones reported, as the reports were also cleaned manually and sometimes a bug can be triggered in various ways using the seed files. 

### Time to bug
Configurations of the form time_to_bug_AnalyzerBugid.conf.json (e.g. time_to_bug_cpa1).
These correspond to *Table 2* in the paper. To get an accurate measure of time, only a single worker is used, so these can take a while to finish. The results are stored in a specified directory `$outdir`. To compute the average times, we used [this script](scripts/get_average_times.py), which uses the pandas package to parse csv:
```
pip install pandas
python3 Minotaur --e time_to_bug_cpa1 cpa1_result_dir
python3 Minotaur/scripts/get_average_times cpa1_result_dir 3 fn
```
'fn' is the flag indicating that a soundness bug is found.
For precision use 'fp', for crashes 'er'.


### Coverage
These give the results for *Table 3* in the paper
The coverage experiment is provided in [coverage.conf.json](experiments/coverage.conf.json). Please update the workers and memory according to your system specifications.
Coverage is collected per batch and can be aggregated via [a script](scripts/merge_coverage.py), which creates a coverage files combining the first n batches with n from 1 to the number of generated batches. This script requires the gcovr package 
The summarized coverage can be printed and plotted via [plot_coverage.py](script/plot_coverage.py) (which again uses pandas), once coverage has been merged.
```
python3 Minotaur --e coverage result_dir  // This will take a long time to run 
pip install gcovr pandas
python3 Minotaur/scripts/merge_coverage.py result_dir/run*
python3 Minotaur/scripts/plot_coverage.py result_dir 16 4
```
The average coverage after 100 batches should be printed to console, and the graphs should appear in the result_dir directory.
