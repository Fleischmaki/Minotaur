## Generation Parameters
Maze generation currently support the following parameters:
- `-a`: Algorithm for maze generation; one of Backtracking, Kruskal, Prim, Sidewinder or Wilsons. Default Backtracking.
- `-w`, `-h`: Width and height of the maze. Mazes should be at least 20 tiles (i.e. 4x5) to ensure proper function
- `-u`: Only create a single function containing all the constraints as nested ifs ("1x1 Maze"). Turned off by default. Overwrites width and height.
- `-b`: Function used for the bug, one of ve (__VERIFIER_error), abort or assert. Default ve
- `-c`: % of backward paths maintained in the maze. Default 0
- `-r`: Seed used for randomizer. Default 0
- `-g`: Generator used for generating guards. Reccomended "CVE_gen". Default default_gen.
- `-s`: Seed .smt2 file used for CVE_gen. Use if and only if CVE_gen is selected.
- `-n`: Number of mazes to chain (append entry of one maze to exit of another). Default 1.
- `-t`: Transformations used (see below). Default keepId
- `-m`: Number of transformations to perform. Default 0.
Note: Unless `-u` is set with and height always need to be provided.

## Transformations
Transformations are passed via the `-t` parameter. Transformations can be combbined via `_`, eg. `-t dc50_sh` will shuffle and drop 50% of constraints.
Transformations that modify the guards should only be used with CVE_gen 
The following transformations are supported at the moment:
- `keepId`: keep original program, as well as transformations
- `rwX`: remove X% of walls from the maze
- `sh`: shuffle gurad constraints
- `dcX`: remvoe X% of guard constraints
- `storm`: run STORM on seed SMT file to produce new gurads. Strongly recommended.
- `wd: generate well-defined programs. Also recommended

## Checking SMT-File compatibility
Running `python3 Minotaur/mc2/maze-gen/smt2_parser.py $outfile $smt_dir` will recursively check if CVE_gen can handle smt2 files contained in $smt_dir or subdirectories. Compatible files are written to $outfile.
