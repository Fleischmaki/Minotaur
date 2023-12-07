import os
from ..runner import *
from ..maze_gen import smt2_parser as sp
from math import ceil

def main(params, outdir,timeout,gen,err,tool,variant,flags):
    commands.run_cmd('mkdir -p %s' % outdir)
    commands.run_cmd("mkdir -p %s" % os.path.join(outdir,'seeds'))
    commands.run_cmd("mkdir -p %s" % os.path.join(outdir,'runs'))

    if not result_is_err(err,tool, variant, flags, params, outdir, timeout,gen):
        print('ERROR: Original not maze not a %s' % err)
        return

    if not 'u' in params.keys():
        params.update({'u':''})
        if not result_is_err(err,tool, variant, flags, params, outdir, timeout, gen):
            params.pop('u', None) 
        else:
            params.update({'w':1,'h':1})

    mutant = os.path.join(outdir,'smt', 'mutant_%d.smt2' % (params['m'] - 1))
    clauses = get_clauses(mutant)

    commands.run_cmd('rm -r %s' % os.path.join(outdir, 'src'))
    keep_first_half = True
    misses_bug = True 
    params = set_fake_params(params)
    while len(clauses) > 1 and (misses_bug or not keep_first_half):
        half = len(clauses) // 2
        new_clauses = clauses[:half] if keep_first_half else clauses[half+1:]

        seed = os.path.join(outdir, 'seeds', str(half) + ('-first' if keep_first_half else '-second'))
        set_seed(params,seed,new_clauses)
        misses_bug = result_is_err(err,tool, variant, flags, params, outdir,timeout,gen)

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
        if len(clauses) == 1:
            break
        commands.run_cmd('mkdir -p %s' % os.path.join(outdir,'seeds'))
        pos = i - empty_clauses
        seed = os.path.join(outdir, 'seeds', str(len(clauses)) + '-' + str(pos+1))
        clause = clauses.pop(pos)
    
        set_seed(params,seed,clauses)
        misses_bug = result_is_err(err,tool,variant,flags,params, outdir,timeout,gen)
        commands.run_cmd('rm -r %s' % os.path.join(outdir, 'src'))
        
        if misses_bug:
            empty_clauses += 1
        else: 
            clauses.insert(pos, clause) # Reinsert clause if no longer 'fn'
        
        
    set_seed(params,seed,clauses)
    if gen == 'container':
        maze_gen.generate_mazes([params],outdir)
    else:
        maze_gen.generate_maze(params, outdir)    

def result_is_err(err,tool,variant,flags,params, outdir, timeout,gen):
    expected_result = 'error' if err in ('fn','tp') else 'safe'
    docker.run_mc(tool,variant,flags, 'min', params, outdir,timeout=timeout, gen=gen, expected_result=expected_result)
    sat = is_err(outdir,err)
    return sat

def set_seed(params, seed, clauses):
    if not seed.endswith('.smt2'):
        seed += '.smt2'
    sp.write_to_file(clauses,seed)            
    params['s'] = seed


def get_clauses(mutant):
    formula = sp.read_file(mutant)[3]
    return list(sp.conjunction_to_clauses(formula))

def is_err(outdir,err):
    resdir = os.path.join(outdir,'res')
    for file in os.listdir(resdir):
            if '_' in file: # Still false negative
                commands.run_cmd('mv %s %s' % (os.path.join(resdir,file), os.path.join(outdir,'runs')))
                if err in file: 
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
    if ',' in argv[0]:
        run = argv[0][:-1] if argv[0].endswith(',') else argv[0]
        if len(run.split(',')) == 15:
            tool,variant,flags,id,u,a,w,h,c,t,g,_,r,timeout,err = run.split(',')
        else:
            tool,variant,flags,id,a,w,h,c,t,g,_,r,timeout,err = run.split(',')
            u = 0

        timeout = ceil(float(timeout)) + 60 # Add a minute for buffer
        seeddir = argv[1]
        outdir = argv[2]
        gen = argv[3]
        params = {'m':int(id),'a':a,'w':int(w),'h':int(h),'c':int(c),'t':t,'g':'CVE_gen','s':os.path.join(seeddir,g+'.smt2'),'r':int(r)}
        if u == '1':
            params['u'] = ''
    else:
        maze = argv[0]
        seeddir = argv[1]
        outdir = argv[2]
        timeout = argv[3]
        gen = argv[4]
        err = argv[5]
        tool = argv[6]
        variant = flags = ''
        if len(argv) >= 8:
            variant = argv[7]
            flags = ' '.join(argv[8:])
        params = get_params(maze,seeddir)

    main(params,outdir,timeout,gen, err, tool, variant, flags)