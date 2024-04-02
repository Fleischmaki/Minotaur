from . import docker, commands
import os

GENERATE_CMD = '%s/scripts/generate.sh -o %s %s'

def get_params_from_maze(maze,smt_path = ''):
    params = dict()
    params['a'], size, params['r'], _, *params['t'], params['m'], params['c']= maze.split('percent')[0].split('_')
    *params['g'],_, params['b'] = maze.split('percent')[1][1:].split('_')

    params['w'], params['h'] = map(lambda x:  int(x), size.split('x'))
    params['m'] = int(params['m'][1:]) # cut 't'    
    params['r'] = int(params['r'])
    params['g'] = '_'.join(params['g'])
    params['t'] = '_'.join(params['t'])
    if size == '1x1':
        params['u'] = ''
    if smt_path != '':
        params['s'] = os.path.join(smt_path,params['g'] + '.smt2')
        params['g'] = 'CVE_gen'
    else:
        params['g'] += 'gen'
    return params


def get_maze_names(params):
    if params['g'] in ('CVE_gen', 'CVE-neg_gen'):
        generator = '%s_gen' % params['s'].split('/')[-1][0:-5]
    else:
        generator = params['g']
    min = 0 if 'keepId' in params['t'] else 1
    return ['%s_%sx%s_%s_0_%s_t%d_%spercent_%s_ve.c' 
            %  (params['a'], params['w'], params['h'],params['r'], params['t'],i,params['c'], generator)
              for i in range(min,params['m'] + 1)]

def generate_maze_in_docker(params, index = 0, timeout=-1):
    params['o'] = docker.HOST_NAME
    param_string = get_string_from_params(params)
    cmd = './Minotaur/scripts/generate.sh ' + param_string
    return docker.spawn_cmd_in_docker(docker.get_container('gen', index),  cmd, timeout=timeout)

def setup_generation_docker(params, outdir, index):
    commands.run_cmd('mkdir -p ' + outdir + ' ' + ' '.join([os.path.join(outdir, i) for i in ['src','smt','sln','png','txt','bin','smt/' + params['r']]]) )
    docker.spawn_docker(1, index, 'gen', outdir).wait()
    if params['s'] is not None:
        docker.set_docker_seed(params['s'], index, 'gen').wait()

def get_string_from_params(params):
    param_string = ''
    for param, value in params.items():
        if param == 's':
            value = '/home/maze/' + params['s'].split('/')[-1]
        param_string += '-%s %s ' % (param, value)
    return param_string

def get_params_from_string(param_string):
    params = dict()
    options = param_string.split(' ')
    i = 0
    while i < len(options):
        arg = options[i][1:] #cut the -
        if i == len(options)-1 or options[i+1].startswith('-'):
            if arg == 'u':
                params['w'] = 1
                params['h'] = 1
            value = ""
        else:
            value = options[i+1]
            i+=1
        params[arg] = value
        i+=1
    return params


def generate_mazes(paramss, outdir, workers=1, timeout=-1):
    works = [[] for _ in range(workers)]
    for i , params in enumerate(paramss):
        works[i % workers].append(params)
    works = list(filter(lambda w: len(w) > 0, works))

    pipes = []
    for i in range(len(works)):
        setup_generation_docker(works[i][0], outdir, i)
        pipes.append(generate_maze_in_docker(works[i][0],i,timeout)) # Can already generate first maze while others spawn in

    for i in range(1,max(map(len,works))):
        for j, work in enumerate(works):
            if i < len(work):
                pipes[j].wait()
                commands.run_cmd('mkdir -p ' + os.path.join(outdir, 'smt', str(work[i]['r'])))
                docker.set_docker_seed(work[i]['s'], j, 'gen').wait()
                pipes[j] = generate_maze_in_docker(work[i], j, timeout)
    commands.wait_for_procs(pipes)
    for i in range(len(works)):
        docker.kill_docker('gen',i)

def generate_maze(params, out_dir = '', minotaur = ''):
    if(minotaur == ''):
        import __main__
        minotaur = '/'.join(__main__.__file__.split('/')[:-1])
    param_string = ''
    for param, value in params.items():
        param_string += '-%s %s ' % (param, value)
    out_dir = os.path.join(minotaur, 'temp') if out_dir == '' else out_dir
    return commands.run_cmd(GENERATE_CMD % (minotaur, out_dir, param_string)) 

