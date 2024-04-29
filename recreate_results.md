## Recreating experiment results
All configuration files for the experiments are already provided in the experiment folder. 
The bug ids are the same as in Table 1 of the experiments section.
There are several types of experiments:

### Recreate bug
Configurations of the form recreate_PaId.conf.json (e.g. recreate_cpa1).
For 5 different seeds (1,2,3,4,5) Run tests until the bug is found on the corresponding version of the analyzer.
Will use multiple workers (default 5) to try and find the bug as quickly as possible.
Note that the found bugs might look different from the ones reported, as the reports where also cleaned manually and sometimes a bug can be triggered in various ways using the seed files. 

### Time to bug
Configurations of the form time_to_bug_PaId.conf.json (e.g. recreate_cpa1).
These correspond to *Table 2* in the paper. To get an accurate measure for time, only a single worker is used, so these can take a while to finish.

The results are stored in a specified directory `$outdir`. To compute the average times, we used [this script](scripts/get_average_times.py).

To obtain the times for an experiment, run `pyhton3 Minotaur/script/get_average_times.py $outdir 4` (4 is the number of different configs we use).

### Coverage
These give the results for *Table 3* in the paper
The coverage experiment is provided in [cov_smt_vs_fuzzed.conf.json](experiments/cov_smt_vs_fuzzed.conf.json). Please update the workers and memory according to your system specifications.
Coverage is collected per batch and can be aggregated via [a script](scripts/merge_coverage.py), which creates a coverage files combining the first n batches with n from 1 to the number of generated batches. 
The summarized coverage can be printed and plotted via [plot_coverage.py](script/plot_coverage.py), once coverage has been merged.
```
python3 Minotaur --e smt_vs_fuzzed_cov result_dir # This will take a long time to run 
python3 Minotaur/scripts/merge_coverage.py result_dir/run*
python3 Minotaur/scripts/plot_coverage.py result_dir 16 4
```
The average coverage after 100 batches should be printed to console, and the graphs should appear in the result_dir directory.
