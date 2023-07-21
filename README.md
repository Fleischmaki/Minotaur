# Minotaur
Minotaur is a metamorphic testing tools for software model checkers, based on [storm](https://github.com/mariachris/storm) and [Fuzzle](https://github.com/SoftSec-KAIST/Fuzzle)

## Installation
```
git clone https://github.com/Fleischmaki/Minotaur.git
pip install -r Minotaur/requirements.txt
./Minotaur/scripts/build_MC_dockers.sh
```

## Using Minotaur
### Run tests
Runs are configured via conf.json files located in Minotaur/test.
To perform a test using the config file conf_name.conf.json run `python3 Minotaur --t conf_name outdir`
For more info on config files check [config.md](./config.md)

### Generate a single maze
`python3 Minotaur --g outdir params...` or ./Minotaur/scripts/generate.sh -o outdir params...
See [params.md](./params.md)

### Minimize a maze
`python3 Minotaur --m maze.c tool (variant) mutant.smt2 outdir`

## Bugs found by Minotaur
 Tool | Issue | Status 
 -- | -- | --
 CPA - InvariantsCPA | [1114](https://gitlab.com/sosy-lab/software/cpachecker/-/issues/1114) |fixed
