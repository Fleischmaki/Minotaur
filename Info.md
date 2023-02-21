# Running tests
Before running tests run 
```
scripts/build_MC_dockers.sh
```
 to build the docker containers for the Model checkers

After that run 
```
python3 scripts/test_mc.py <Path to Config> <Output folder>
```
# Config
A sample config can be found in */test/mctest_config/test.conf.json*
The config is in json and should contain 
```
{
    "repeats" : \d+,                        //Number of mazes to generate
    "transforms": \d+,                      //Number of transformed mazes per generated maze
    "duration" : \d+,                       //Timeout per maze, in minutes
    "fuzzleRoot": /path/to/Fuzzle",         //Path to Fuzzle roo
    "tool": ["tools","to","be","tested"]    //Currently seahorn, cpa, ua
    "workers": \d+                          //Number of parallel workers
    "memory": \d+                           //Memory per workers (in GB)
    "verbosity": [all|summary|bugs]         //"all" preserves all outputs,
                                            //"summary" only csv summary,
                                            //"bugs" log bugs only
    "parameters": [                         //List of parameters for maze generation
        par1: [val1,val2,val3],             //Either fixed values or 
        par2: {min: i, max: j},             //min/max (if numeric)
    ]
}
```
## Current parameters
- a: Algorithm for maze generation ["Backtracking","Kruskal","Prims","Wilsons","Sidewinder"]
- w: Maze Width (min 5)
- h: Maze Height (min 5)
- c: Percentage of backedges to keep 
- t: Transformations {t1: [0,1], t2: {min:0,max:10}, t3: [10,15,20],...}
- g: Type of constraint generation: ["default_gen","equality\*_gen", "CVE\*_gen"]              
- r: Random seed
- n: Number of mazes to chain 

## Current transformations
- rwX: Remove X% of walls
- keepId: Also output original maze (without transformations)
- sh: Shuffle constraints*
- dcX: Drop X% of constraints*
- storm: Generate transformed SMT Files via Storm*
\* Constraint based transformations only work with CVE_gen