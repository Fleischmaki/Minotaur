## Recreating experiment results
### Python dependencies
If you did not install the python requirements, you will need to install `pandas` and `gcovr` to evaluate experiment results
```bash
pip install gcovr pandas
```
### Experiment configurations
All configuration files for the experiments are already provided in the [experiment folder](experiments). 
The bug ids are the same as in Table 2 of the experiments section.

NOTE: in the following all commands assume that you are working in a folder containing the `Minotaur` folder from our submission. If you are working in a different folder replace `Minotaur` (or `./Minotaur`) with the path to the `Minotaur` folder.

There are several types of experiments:
### Run tests (RQ1)
Our submission includes the seeds we used for our tests (*Table 1*) in the `bitvector` (column BV) and `integer` (column IA/NIA) folders.

We provide the final test configurations we used in the [test folder](test).
`bv_*` means testing with seeds using bitvector logic, `integer_*` testing with seeds from integer logics.
`soundness`, `precision` and `mixed` indicate which fuzzing mode (all2sat, unsat2unsat or all2all is used). 
Before running tests, please adjust the parameters for `workers` and `memory` according to your system.
You start a test run using e.g. for bitvectors + pure soundness as follows:
```bash
python Minotaur --t bv_soundness outdir
```
NOTE: We do provide a config to use integer seeds to test precision, because most of the analyzers
complain about overflows, of which we cannot guarantee the absence using integer seeds.

### Recreate a bug (RQ1/Table 2)
We also provide configurations that try to quickly find a specific bug from *Table 2* on 5 different random integer seeds, by fixing the SMT-seed and analyzer (including the flags). E.g. for bug 1:
```bash
python Minotaur --e recreate1 outdir
```
Test results for each run are logged in a file called `summary.csv`. The files that caused the bugs are stored nested (first by tool, then batch-id, then by the name of the maze), the best way to find them is probably using `find`

```bash
find -type f -name *.c outdir/runX_0 
```
NOTE: the found bugs might look different from the ones reported, as the reports were also cleaned manually and sometimes a bug can be triggered in various ways using the seed file. For unfixed bugs there is also the possibility that a new bug is found, as we cannot check against the fixed version to confirm.

NOTE: might take a long time for mixed fuzzing bugs.

NOTE: due to a currently unfixed bug in CPA bug 9 will create a lot of error results. This is expected.

### Measure time to bug (RQ2/Table 3)
These correspond to *Table 3* in the paper. 
```bash
python Minotaur --e time_to_bug4 outdir
```
The results are stored in a specified directory `outdir`. To compute the average times, we used [this script](scripts/get_average_times.py):
```bash
./Minotaur/scripts/get_average_times outdir 3 fn/fp/er
```
Use `fn` if the issue is realted to soundness, for precision use `fp`, for crashes `er`.

NOTE: To get an accurate measure of time, only a single worker is used, so these can take a while to finish, however they are set upd so that they can be run in parallel without any conflict. If your machine has less than 16 (or 8x2) cores, please update the `use_core` parameter in the [config files](experiments). Don't run two experiments configured to use the same core at the same time, or the results might be incorrect. 

NOTE: For bug8 we only test Minotaur, as the baselines are non-applicable. To correctly read the results please run
```bash
./Minotaur/scripts/get_average_times outdir 1 fp
```

### Measure coverage (RQ3/Figure 5)
These give the results for *Figure 5* in the paper.
The coverage experiment is provided in [coverage.conf.json](experiments/coverage.conf.json). Please update the workers and memory according to your system specifications.
```bash
./Minotaur/scripts/build_MC_dockers.sh
python Minotaur --e coverage outdir  
# ^ This takes more than a day to run on a server 
python Minotaur/scripts/merge_coverage.py outdir/run*
python Minotaur/scripts/plot_coverage.py outdir 15 3
```

Coverage is collected per batch and can be aggregated via [a script](scripts/merge_coverage.py), which creates a coverage files combining the first n batches with n from 1 to the number of generated batches. The summarized coverage can be printed and plotted via [plot_coverage.py](script/plot_coverage.py) once coverage has been merged.
The average coverage is printed to console, and the graphs should appear in the outdir directory.

