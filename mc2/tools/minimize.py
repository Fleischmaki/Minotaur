import os
from ..runner import *
from ..maze_gen import smt2_parser as sp

def main(maze_path,tool,variant,seeddir, outdir,timeout):
    params = get_params(maze_path,seeddir)
    commands.run_cmd('mkdir -p %s' % outdir)
    commands.run_cmd("mkdir -p %s" % os.path.join(outdir,'seeds'))
    commands.run_cmd("mkdir -p %s" % os.path.join(outdir,'runs'))

    if not check_if_tp(tool, variant, params, outdir, timeout):
        print('ERROR: Original not maze not a fn')
        return
    mutant = os.path.join(outdir,'smt', 'mutant_%d.smt2' % (params['m'] - 1))
    clauses = get_clauses(mutant)

    keep_first_half = True
    misses_bug = True 
    params = set_fake_params(params)
    while misses_bug or not keep_first_half:
        half = len(clauses) // 2
        new_clauses = clauses[:half] if keep_first_half else clauses[half+1:]

        seed = os.path.join(outdir, 'seeds', str(half) + ('-first' if keep_first_half else '-second'))
        set_seed(params,seed,new_clauses)
        misses_bug = check_if_tp(tool, variant, params, outdir,timeout)

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
    
        set_seed(params,seed,clauses)
        misses_bug = check_if_tp(tool,variant,params, outdir,timeout)
        commands.run_cmd('rm -r %s' % os.path.join(outdir, 'src'))
        
        if misses_bug:
            empty_clauses += 1
        else: 
            clauses.insert(pos, clause) # Reinsert clause if no longer 'fn'
        
        
    set_seed(params,seed,clauses)
    maze_gen.generate_mazes([params],outdir)
        

def check_if_tp(tool,variant,params, outdir, timeout):
    docker.run_mc(tool,variant, 'min', params, outdir,timeout=timeout)
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
    resdir = os.path.join(outdir,'res')
    for file in os.listdir(resdir):
            if '_' in file: # Still false negative
                commands.run_cmd('mv %s %s' % (os.path.join(resdir,file), os.path.join(outdir,'runs')))
                if 'fn' in file: 
                    return True
    return False

def get_params(maze_path, smt_path = ''):
    maze = maze_path.split('/')[-1][:-2] # Cut .c
    params = maze_gen.get_params_from_maze(maze,smt_path=smt_path)  
    return params

def set_fake_params(params):
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
    if len(argv) == 6:
        variant = argv[2]
        seeddir = argv[3]
        outdir = argv[4]
        timeout = argv[5]
    else:
        variant = ''
        seeddir = argv[2]
        outdir = argv[3]
        timeout = argv[4]
    main(maze, tool, variant,seeddir,outdir,timeout)