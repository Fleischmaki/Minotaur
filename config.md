## Configuration files
Automated testing and experiments are configured via config.json files. Some examples can be found in the [test](test) and [experiments](experiments) folders.
In particular config files accept the following values
- `workers`: Number of cores to use in parallel
- `memory`: Memory to use per worker
- `duration`: Time to run tools per maze
- `repeats`: Number of mazes to generate (-1 to run until cancelled), `transforms`: Number of transformations per maze
   - Total number of mazes generated = `repeats` * `transforms`
- `batch_size`: How many mazes will be tested before collecting results. Use higher numbers if spawning containers is expensive. 
- `batch_duration` Sets the time before a batch gets killed, specified as the average time a maze should have (i.e. the total time for a batch is batch_duration*batch_size) 
- `maze_gen=['local','container']`: Generate mazes locally one at a time or in parallel in docker
-  `verbosity=['all','bug','summary','bug_only']`: Container output to keep: `all` keeps all, `bug` only for buggy outputs (fn or fp), `summary` only logs results to `summary.csv`, but keeps no output and `bug_only` only logs bugs to `summary.csv`
-  `expected_results=['error','all']`: `error` expects soundness tests, `safe` precision tests.
-  `parameters`: Possible values for generation [parameters](parameters.md). Can either be a list of possible values or an object specifiying a `min  and `max` value
    - Transformations (parameter 't') expects an obejct containing for each transformation their possible values, specified same as other parameters.
- `tools`: Tools to be tested. It is necessary to add an object specifiying a variant (e.g. Taipan/Kojak/etc. for Ultimate). Flags can be set in two ways:
    -  `"toggle"`: A list of flags that are toggled on or off at random.
    -  `"choose"`: An object containing flags of the form `'prefix': [0,'opt1','opt2',...]`. This chooses one of the option and writes it + the prefix. If the option is 0, nothing will be written. E.g. `'--paths ': [0,'fifo','lifo']` will write one of `['','--paths fifo', '--paths lifo']`.
 -  `cov=[0,1]`: Collect coverage data. Currently only supported by ESBMC, CBMC, SeaHorn dockers
 -  `gen_time`: Timeout maze generation after this many seconds
### Experiment config
TODO
