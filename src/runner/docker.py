import subprocess, os, logging
from . import commands, maze_gen

LOGGER = logging.getLogger(__name__)

SPAWN_CMD_CPU = 'docker run --rm -m=%dg -t -d --cpuset-cpus=%d --name %s %s'
SPAWN_CMD_NOCPU = 'docker run --rm -m=%dg -t -d --name %s %s'
CP_MAZE_CMD = 'docker cp %s %s:/home/%s/%s'
CP_SEED_CMD = 'docker cp %s %s:/home/%s/%s'
CP_CMD = 'docker cp %s:/home/%s/workspace/%s %s'
KILL_CMD = 'docker kill %s'
REMOVE_CMD = 'docker rm %s'
DOCKER_PREFIX = 'minotaur-'

def spawn_cmd_in_docker(container, cmd_str, timeout=-1):
    LOGGER.info('Executing (in container %s): %s' % (container, cmd_str))
    cmd_prefix = 'docker exec %s /bin/bash -c' %  container
    if timeout > 0:
        cmd_prefix = 'docker exec %s timeout %d /bin/bash -c' %  (container, timeout)
    cmd_args = cmd_prefix.split()
    cmd_args += [cmd_str]
    try:
        return subprocess.Popen(cmd_args)
    except Exception as e:
        LOGGER.error(e)
        exit(1)

def run_cmd_in_docker(container,cmd_str):
    return spawn_cmd_in_docker(container,cmd_str).wait()


def get_user(tool): # Could not create user in seahorn docker
    if tool == 'seahorn':
        return 'usea'
    return 'maze'

def get_container(tool,name):
    return tool + '-' + str(name)

def clean_name(name):
    return str(name).replace(' ', '').replace('=','')

def spawn_docker(memory, name, tool, cpu = -1):
    if cpu > 0:
        cmd = SPAWN_CMD_CPU % (memory, cpu, get_container(tool,name), DOCKER_PREFIX + tool)
    else:
        cmd = SPAWN_CMD_NOCPU % (memory, get_container(tool,name), DOCKER_PREFIX + tool)
    return commands.spawn_cmd(cmd)

def add_docker_maze(path, name, tool,maze_name):
    cmd = CP_MAZE_CMD % (path, get_container(tool,name),get_user(tool), os.path.split(path)[1] if maze_name == '' else maze_name)
    return commands.spawn_cmd(cmd)

def set_docker_seed(path, name, tool):
    cmd = CP_SEED_CMD % (path, get_container(tool,name),get_user(tool), os.path.split(path)[1])
    return commands.spawn_cmd(cmd)

def run_docker(duration, tool, name, variant='', flags='', maze_name='maze.c', result_name = 'res'):
    user = get_user(tool)
    script = '/home/%s/tools/run_%s.sh' % (user, tool)
    src_path = '/home/%s/%s' % (user, maze_name)
    out_name = result_name
    cmd = '%s %s %s %s %s %s' % (script, src_path, duration, out_name, variant,flags)
    return spawn_cmd_in_docker(get_container(tool,name), cmd)

def collect_docker_results(tool,name, expected_result='error'):
    user = get_user(tool)
    cmd = 'python3 /home/%s/tools/get_tcs.py /home/%s/workspace/outputs %s' % (user,user,expected_result)
    return spawn_cmd_in_docker(get_container(tool,name), cmd)

def copy_docker_results(tool, name , out_path):
    user = get_user(tool)
    return copy_docker_output(tool, name, out_path, user)

def copy_docker_output(tool, name, out_path, user):
    cont = get_container(tool,name)
    if not os.path.isdir(out_path):
        return commands.run_cmd(CP_CMD % (cont, user, 'outputs', out_path))
    if os.path.isdir(os.path.join(out_path,'src')):
        for dir in ['src','smt','png','txt','smt','bin']:
            commands.run_cmd(CP_CMD % (cont, user, os.path.join('outputs',dir,'.'), os.path.join(out_path, dir)))
    return commands.run_cmd(CP_CMD % (cont, user, 'outputs/.', out_path))

def kill_docker(tool,name):
    cmd = KILL_CMD % (get_container(tool,name))
    commands.run_cmd(cmd)
    cmd = REMOVE_CMD % (get_container(tool,name))
    return commands.spawn_cmd(cmd)


def run_mc(tool,variant,flags, name, params,outdir, memory = 4,  timeout=1, gen='container', expected_result='error'):
    spawn_docker(memory,name,tool).wait()
    if gen == 'container':
        maze_gen.generate_maze_in_docker(params,name).wait()
        copy_docker_results('gen', name, outdir)
        kill_docker('gen', name)
    else:
        maze_gen.generate_maze(params,outdir)
    t_index = params['m'] - (0 if 'keepId' in params['t'] else 1)
    maze = maze_gen.get_maze_names(params)[t_index]
    maze_path = os.path.join(outdir,'src',maze)
    add_docker_maze(maze_path,name,tool).wait()
    run_docker(timeout, tool, name, variant,flags,maze).wait()
    collect_docker_results(tool,name,expected_result).wait()
    copy_docker_results(tool,name,os.path.join(outdir, 'res'))
    kill_docker(tool,name).wait()