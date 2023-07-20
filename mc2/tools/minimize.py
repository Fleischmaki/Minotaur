import sys, os, time
from ..runner import *
from ..maze_gen import smt2_parser as sp

def main(maze_path,tool,variant, memory,mutant,outdir):
    params = get_params(maze_path)
    commands.run_cmd('mkdir -p %s' % outdir)
    commands.run_cmd("mkdir -p %s" % os.path.join(outdir,'seeds'))
    commands.run_cmd("mkdir -p %s" % os.path.join(outdir,'runs'))
 
    clauses = get_clauses(mutant)
    misses_bug = True
    keep_first_half = True

    while misses_bug or not keep_first_half:
        half = len(clauses) // 2
        new_clauses = clauses[:half] if keep_first_half else clauses[half+1:]

        seed = os.path.join(outdir, 'seeds', str(half) + ('-first' if keep_first_half else '-second'))
        misses_bug = check_result(tool, variant, memory, params, outdir, seed,new_clauses)

        commands.run_cmd('rm -r %s' % os.path.join(outdir, 'src'))
        if misses_bug:
            clauses = new_clauses
            print("Discarded %s half of constraints" % 'first' if keep_first_half else 'second')
            keep_first_half = True
        else:
            keep_first_half = not(keep_first_half)
    
    # Check individual files
    empty_clauses = 0
    for i in range(len(clauses)):
        commands.run_cmd('mkdir -p %s' % os.path.join(outdir,'seeds'))
        pos = i - empty_clauses
        seed = os.path.join(outdir, 'seeds', str(len(clauses)) + '-' + str(pos+1))
        clause = clauses.pop(pos)
        
        misses_bug = check_result(tool,variant,memory, params, outdir, seed,clauses)
        commands.run_cmd('rm -r %s' % os.path.join(outdir, 'src'))
        
        if misses_bug:
            empty_clauses += 1
        else: 
            clauses.insert(pos, clause) # Reinsert clause if no longer 'fn'
        
        
    set_seed(params,seed,clauses)
    maze_gen.generate_maze(params,out_dir = outdir)
        

def check_result(tool,variant,memory, params, outdir, seed, clauses):
    set_seed(params, seed, clauses)
    docker.run_mc(tool,variant, 'min', memory, params, outdir)
    sat = is_fn(outdir)
    return sat

def set_seed(params, seed, clauses):
    if not seed.endswith('.smt2'):
        seed += '.smt2'
    sp.write_to_file(clauses,seed)            
    params['s'] = seed



def get_clauses(mutant):
    formula = sp.read_file(mutant)[3]
    return list(sp.conjunction_to_clauses(formula))

def is_fn(outdir):
    for file in os.listdir(os.path.join(outdir,'outputs')):
            if '_' in file: # Still false negative
                commands.run_cmd('mv %s %s' % (os.path.join(outdir,'outputs',file), os.path.join(outdir,'runs')))
                if 'fn' in file: 
                    return True
    return False

def get_params(maze_path):
    maze = maze_path.split('/')[-1][:-2] # Cut .c
    params = maze_gen.get_params_from_maze(maze,'_') # Give a non-empty SMT path to trigger smt conversion  
    params['t'] = params['t'].replace('storm', '')
    params['t'] = params['t'].replace('__', '_')
    if params['t'].endswith('_'):
        params['t'] = params['t'][:-1]
    if params['t'] == '':
        params['t'] = 'keepId'
        params['m'] = 0
    return params

def load(argv):
    maze = argv[0]
    tool = argv[1]
    if len(argv) == 5:
        variant = argv[2]
        mutant = argv[3]
        outdir = argv[4]
    else:
        variant = ''
        mutant = argv[2]
        outdir = argv[3]
    memory = 4
    main(maze, tool, variant, memory, mutant,outdir)