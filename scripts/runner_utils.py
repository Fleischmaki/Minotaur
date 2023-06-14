import subprocess
import time
import os, sys

SPAWN_CMD = 'docker run --rm -m=%dg -t -d --cpuset-cpus=%d --name %s %s'
CP_MAZE_CMD = 'docker cp %s %s:/home/%s/maze.c'
CP_SEED_CMD = 'docker cp %s %s:/home/%s/%s'
CP_CMD = 'docker cp %s:/home/%s/workspace/outputs %s'
KILL_CMD = 'docker kill %s'
GENERATE_CMD = '%s/scripts/generate.sh -o %s %s'
MV_CMD = 'mv %s %s'
RM_CMD = 'rm -r %s'

def wait_for_procs(procs):
    for p in procs:
        p.wait()

def spawn_cmd(cmd_str):
    print('[*] Executing: %s' % cmd_str)
    cmd_args = cmd_str.split()
    try:
        return subprocess.Popen(cmd_args, stderr=subprocess.PIPE, stdout=subprocess.PIPE, text=True)
    except Exception as e:
        print(e)
        exit(1)

def run_cmd(cmd_str):
    print('[*] Executing: %s' % cmd_str)
    cmd_args = cmd_str.split()
    return subprocess.run(cmd_args)

def spawn_cmd_in_docker(container, cmd_str):
    print('[*] Executing (in container): %s' % cmd_str)
    cmd_prefix = 'docker exec %s /bin/bash -c' %  container
    cmd_args = cmd_prefix.split()
    cmd_args += [cmd_str]
    try:
        return subprocess.Popen(cmd_args)
    except Exception as e:
        print(e)
        exit(1)

def run_cmd_in_docker(container,cmd_str):
    return spawn_cmd_in_docker(container,cmd_str).wait()


def get_user(tool): # Could not create user in seahorn docker
    if tool == 'seahorn':
        return 'usea'
    return 'maze'

def get_container(tool,name):
    return tool + '-' + str(name)

def spawn_docker(memory, name, tool, cpu = 0):
    cmd = SPAWN_CMD % (memory, cpu, get_container(tool,name), 'maze-' + tool)
    return spawn_cmd(cmd)

def set_docker_maze(path, name, tool):
    cmd = CP_MAZE_CMD % (path, get_container(tool,name),get_user(tool))
    return spawn_cmd(cmd)

def set_docker_seed(path, name, tool):
    cmd = CP_SEED_CMD % (path, get_container(tool,name),get_user(tool), path.split('/')[-1])
    return spawn_cmd(cmd)

def run_docker(duration, tool, name):
    user = get_user(tool)
    script = '/home/%s/tools/run_%s.sh' % (user, tool)
    src_path = '/home/%s/maze.c' % (user)
    cmd = '%s %s %s' % (script, src_path, duration)
    spawn_cmd_in_docker(get_container(tool,name), cmd)# sleep timeout + extra 5 secs.

def collect_docker_results(tool,name):
    user = get_user(tool)
    cmd = 'python3 /home/%s/tools/get_tcs.py /home/%s/workspace/outputs' % (user,user)
    return spawn_cmd_in_docker(get_container(tool,name), cmd)

def copy_docker_results(tool, name , out_path):
    user = get_user(tool)
    return copy_docker_output(tool, name, out_path, user)

def copy_docker_output(tool, name, out_path, user):
    return run_cmd(CP_CMD % (get_container(tool,name), user, out_path if not os.path.isdir(out_path) else os.path.join(out_path,'.')))
    #for file in os.listdir(os.path.join(out_path,'outputs')):
    #    run_cmd(MV_CMD % (os.path.join(out_path,'outputs', file),out_path))
    #return run_cmd(RM_CMD % os.path.join(out_path,'outputs'))

def kill_docker(tool,name):
    cmd = KILL_CMD % (get_container(tool,name))
    return spawn_cmd(cmd)

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
    spawn_docker(1, index, 'gen', cpu=index).wait()

    if params['s'] is not None:
        set_docker_seed(params['s'], index, 'gen').wait()
        params['s'] = '/home/maze/' + params['s'].split('/')[-1]

    param_string = '-o ' + 'outputs '
    for param, value in params.items():
        param_string += '-%s %s ' % (param, value)
    cmd = './Fuzzle/scripts/generate.sh ' + param_string

    return spawn_cmd_in_docker(get_container('gen', index),  cmd)

def generate_mazes(paramss, outdir):
    pipes = []
    for i in range(len(paramss)):
        pipes.append(generate_maze_in_docker(paramss[i],i))
    wait_for_procs(pipes)
    for i in range(len(paramss)):
        copy_docker_output('gen', i, outdir, 'maze')
        kill_docker('gen', i)

def generate_maze(fuzzle, params, out_dir = ''):
    param_string = params
    for param, value in params.items():
        param_string += '-%s %s ' % (param, value)
    out_dir = os.path.join(fuzzle, 'temp') if out_dir == '' else out_dir
    param_string += ' -o %s' % out_dir
    return run_cmd(GENERATE_CMD % (fuzzle, out_dir, param_string)) # TODO: Figure out how to multithread this


def run_mc(tool, name, memory, fuzzle, params,outdir):
    spawn_docker(memory,name,tool).wait()
    generate_maze_in_docker(fuzzle,params,outdir)
    t_index = params['m'] - (0 if 'keepId' in params['t'] else 1)
    #print(params, get_maze_names(params), t_index)
    maze_path = os.path.join(outdir,'src',get_maze_names(params)[t_index])
    set_docker_maze(maze_path,name,tool).wait()
    run_docker(1, tool, name)
    time.sleep(60)
    collect_docker_results(tool,name).wait()
    copy_docker_results(tool,name,outdir)
    kill_docker(tool, name).wait()

if __name__ == "__main__":
    generate_maze_in_docker(*sys.argv[1:])