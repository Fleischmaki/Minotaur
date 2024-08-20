# Minotaur
Minotaur is a generative black-box fuzzer for software model checkers, based on [Fuzzle](https://github.com/SoftSec-KAIST/Fuzzle) and (optionally) using [STORM](https://github.com/mariachris/storm).

## About
Minotaur uses sat/unsat SMT-Files to generate programs that are unsafe/safe by construction, which can be used to test program anaylzers for soundness/precision issues. 

## Requirements
- Python 3.10 or 3.11
- [Docker](https://docs.docker.com/engine/install/) (or similar)

## Installation
We tested installation on Ubuntu 22.03 and Debian 12. If you're using a different system, you might need to install
the dependencies in a different manner.
```bash
sudo apt update && sudo apt install docker.io
./Minotaur/scripts/build_MC_dockers.sh <num_cores>
# For recreating experiments #
./Minotaur/scripts/build_experiment_dockers.sh <num_cores>
```
where <num_cores> is the number of cores available for parallel builds (recommended to keep at least two cores free).

Note that the provided dockers build the analyzers under test from source. Building might take up to a few hours and several GBs of memory.
The builds need to download data from remote mirrors, so it can occassionally occur that the build fails because a connection is terminated.
In this case rerunning the script usually fixes the problem.

### Install python3 dependencies
#### NOTE: if you only want to run tests or experiments, you can skip this step. 

If you want to generate mazes locally or perform minimization, you will need to install the packages from [requirements.txt](requirements.txt)
We recommend using a [virtualenv](https://virtualenv.pypa.io/en/latest/):
```bash
# python3.10 or python3.11
sudo apt update && sudo apt install python3-virtualenv
virtualenv --python=/usr/bin/python3.XX venv
source venv/bin/activate
pip install -r Minotaur/requirements.txt
```
If you want to use STORM locally, update the STORM home in the [config file](src/maze_gen/storm/config.py).

## Recreating ASE 2024 paper results
For more informations on the provided experiment configurations see [this guide](recreate_results.md) on how to recreate the experiment results. 

## Using Minotaur
### Test Analyzers
Runs are configured via conf.json files located in the [test](test) folder.
To perform a test using the config file test/conf_name.conf.json run 
```bash
python Minotaur --t <conf_name> <outdir>
```
For more info on config files check [config.md](./config.md) and the example config files provided.
Results are written to `summary.csv`; lines ending in `fn` (`fp`) indicate that a soundness (precision) 
issue has been found for the listed parameters.

### Run experiments
Before recreating experiments, build the necessary experiment Dockers. Then run the experiment for a given config similarly to test config: 
```bash
./Minotaur/scripts/build_experiment_dockers.sh
python Minotaur --e <experiment_name> <outdir>
```
Experiment configurations are stored in the [experiments](experiments) folder. 

### Generate a specific maze
```
python Minotaur --g {local,container} <outdir> <params...>
```
Will generate the maze + any transformations specified.
`container` indicates that mazes should be generated within a container, which is but works without installing 
the python dependencies. `local` is faster but requires the dependencies. 
For parameter options see [params.md](./params.md).

### Minimize a maze
```
python Minotaur --m <report> <seed-dir> <outdir> {local,container}
```
`<report>` is the line from the `summary.csv` (wrapped in single quotes) corresponding to the test case you want to minimize, e.g.
```
esbmc-bug1,23695,--interval-analysis,,2,1,storm_mc100_dag3,CVE_gen,app12bench_930.smt2,3666,00000.11000,fn
```
for a test that caused a soundness bug in the interval-analysis of tool esbmc-bug1.

The csv contains most of the information required to recreate and minimize the test, you only need to set `<seed-dir>` to tell the minimizer where it should look for the original seed constraint file used in the generation (Minotaur will also search in subdirectories of `<seed-dir>`).

The remaining options are the same as for generation.

### Filter accepted seed files
```bash
python Minotaur --c <seed_dir> <outfile> {sat,unsat}
```
will recursively search for compatible smtfiles for sat/unsat seed generation (=> unsafe/safe programs).
Compatible files will be written to outfile. Files can then be collected, e.g. with `mkdir safe_seeds && for f in $(cat outfile); do cp seed_dir/"$f" safe_seeds; done`.

### Logging
For all tools the logging level can be set via --LEVEL with LEVEL being one of E(rror), W(arning), I(nfo) or D(ebug). E.g. `python3 --t --D conf outdir` runs tests with log-level `DEBUG`.
Note that container outputs are only tracked if the logging level is set to Debug

## Bugs found by Minotaur
In chronological order; ID is the corresponding ID used in Table 2 of the paper.
### Soundness Bugs
ID.  | Tool | Status | Cause
| --  | -- | -- | -- |
4 | CPA - InvariantsCPA | [fixed](https://gitlab.com/sosy-lab/software/cpachecker/-/issues/1114) | Overflow
28 | Ultimate Framework Integer | [fixed](https://github.com/ultimate-pa/ultimate/issues/642#issuecomment-1661186726) | Overflow
5 |CPA - InvariantsCPA | [fixed](https://gitlab.com/sosy-lab/software/cpachecker/-/issues/1130) | Bitwise Operations
\-|CPA - Intervallanalysis | [confirmed](https://gitlab.com/sosy-lab/software/cpachecker/-/issues/1132#note_1544904422) | Overflow (known)
26 | Symbiotic | [confirmed](https://github.com/staticafi/symbiotic/issues/246) | Arrays
27 |Symbiotic | [open](https://github.com/staticafi/symbiotic/issues/247) | Unknown
29 |Ultimate Automizer/Gemcutter integer | [fixed](https://github.com/ultimate-pa/ultimate/issues/646) | Bitwise Operators
10 |ESBMC --interval-analysis | [fixed](https://github.com/esbmc/esbmc/issues/1363) | Type Casts
11 |ESBMC --interval-analysis | [fixed](https://github.com/esbmc/esbmc/issues/1392) | Type Casts
6 |CPA -InvariantsCPA | [fixed](https://gitlab.com/sosy-lab/software/cpachecker/-/issues/1194) | Modulo Operator
23 |Seahorn - bpf | [closed](https://github.com/seahorn/seahorn/issues/545) | Bound inference
12 |ESBMC --interval-analysis | [fixed](https://github.com/esbmc/esbmc/issues/1565) | Boolean Intervals
13 |ESBMC --cvc4 | [fixed](https://github.com/esbmc/esbmc/issues/1770) | Incremental-SMT Translation
7 |CPA -InvariantsCPA | [confirmed](https://gitlab.com/sosy-lab/software/cpachecker/-/issues/1208) | Division
14 |ESBMC --mathsat| [confirmed](https://github.com/esbmc/esbmc/issues/1771) | Unknown
19 | MOPSA congr | [fixed](https://gitlab.com/mopsa/mopsa-analyzer/-/issues/179) | Modulo
\- | Ultimate Integer| [closed](https://github.com/ultimate-pa/ultimate/issues/664) | Division-by-Zero (Undefined)
20 | MOPSA excluded-powerset | [confirmed](https://gitlab.com/mopsa/mopsa-analyzer/-/issues/182) | Unknown 
21 | MOPSA cell-rel-itv | [closed](https://gitlab.com/mopsa/mopsa-analyzer/-/issues/183) | Outdated Dependency | 
31 | Ultimate Framework Integer| [fixed](https://github.com/ultimate-pa/ultimate/issues/665) | Overflowing Left Shift | 
\- | MOSPA cell-string-length-pointer-sentinel-pack-rel-itv-congr-rewrite | [confirmed](https://gitlab.com/mopsa/mopsa-analyzer/-/issues/184) | Negative Right Shift (Undefined)|
22 | MOPSA congr | [confirmed](https://gitlab.com/mopsa/mopsa-analyzer/-/issues/185) | Modulo |

### Precision Issues
ID. |Tool | Status | Cause
| -- | -- | -- | -- |
16 | MOPSA default | [confirmed](https://gitlab.com/mopsa/mopsa-analyzer/-/issues/150) | Type Casts
17 | MOPSA default | [confirmed](https://gitlab.com/mopsa/mopsa-analyzer/-/issues/157) | Imprecise Overabstraction
24 | SeaHorn | [open](https://github.com/seahorn/seahorn/issues/546) | Interprocedural Analysis (probably)
25 | SeaHorn | [open](https://github.com/seahorn/seahorn/issues/550) | Unknown
8 | CPA -smg2 | [fixed](https://gitlab.com/sosy-lab/software/cpachecker/-/issues/1211) | Symbolic Constants
6 | MOPSA | [confirmed](https://gitlab.com/mopsa/mopsa-analyzer/-/issues/177) | Type Casts
1 | 2ls --k-induction | [confirmed](https://github.com/diffblue/2ls/issues/177) | Unknown
2 | CBMC | [open](https://github.com/diffblue/cbmc/issues/8295) | Pointers
9| CPA -smg2| [confirmed](https://gitlab.com/sosy-lab/software/cpachecker/-/issues/1211#note_1904978360) | Symbolic array accesses 
3 | CBMC --refine | [open](https://github.com/diffblue/cbmc/issues/8296) | Unknown
15 | ESBMC --inteval-analysis | [confirmed](https://github.com/esbmc/esbmc/issues/1844) | Unary Minus + Casts
### Crashes
ID | Tool | Status | Cause
| -- |-- | -- | -- |
30 | Ultimate Kojak Bitvector | [fixed](https://github.com/ultimate-pa/ultimate/issues/647#event-10423593364) | SMT translation
\- | CPA -smg2 | [open](https://gitlab.com/sosy-lab/software/cpachecker/-/issues/1211#note_1907113929) | Unknown
