from . import docker, commands
import os

GENERATE_CMD = '%s/scripts/generate.sh -o %s %s'

def get_params_from_maze(maze,smt_path = ''):
    params = dict()
    params['a'], size, params['r'], _, params['t'], params['m'], params['c'], *params['g'],_, params['b'] = maze.split('_')

    params['w'], params['h'] = map(lambda x:  int(x), size.split('x'))
    params['c'] = int(params['c'][:-7]) # cut 'percent'
    params['m'] = int(params['m'][1:]) # cut 't'    
    params['r'] = int(params['r'])
    params['g'] = '_'.join(params['g'])
    if size == '1x1':
        params['u'] = ''
    if smt_path != '':
        params['s'] = os.path.join(smt_path,params['g'] + '.smt2')
        params['g'] = 'CVE_gen'
    else:
        params['g'] += 'gen'
    return params

def get_maze_names(params):
    if params['g'] == 'CVE_gen':
        generator = '%s_gen' % params['s'].split('/')[-1][0:-5]
    else:
        generator = params['g']
    min = 0 if 'keepId' in params['t'] else 1
    return ['%s_%sx%s_%s_0_%s_t%d_%spercent_%s_ve.c' 
            %  (params['a'], params['w'], params['h'],params['r'], params['t'],i,params['c'], generator)
              for i in range(min,params['m'] + 1)]

def generate_maze_in_docker(params, index = 0):
    docker.spawn_docker(1, index, 'gen', cpu=index).wait()

    if params['s'] is not None:
        docker.set_docker_seed(params['s'], index, 'gen').wait()

    param_string = '-o ' + 'outputs '
    for param, value in params.items():
        if param == 's':
            value = '/home/maze/' + params['s'].split('/')[-1]
        param_string += '-%s %s ' % (param, value)
    
    cmd = './Fuzzle/scripts/generate.sh ' + param_string

    return docker.spawn_cmd_in_docker(docker.get_container('gen','', index),  cmd)

def generate_mazes(paramss, outdir):
    pipes = []
    for i in range(len(paramss)):
        pipes.append(generate_maze_in_docker(paramss[i],i))
    commands.wait_for_procs(pipes)
    pipes = []
    for i in range(len(paramss)):
        docker.copy_docker_output('gen', i, outdir, 'maze')
        pipes.append(docker.kill_docker('gen', i))
    commands.wait_for_procs(pipes)

def generate_maze(fuzzle, params, out_dir = ''):
    param_string = ''
    for param, value in params.items():
        param_string += '-%s %s ' % (param, value)
    out_dir = os.path.join(fuzzle, 'temp') if out_dir == '' else out_dir
    param_string += ' -o %s' % out_dir
    return commands.run_cmd(GENERATE_CMD % (fuzzle, out_dir, param_string)) # TODO: Figure out how to multithread this
