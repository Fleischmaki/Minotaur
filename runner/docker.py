import subprocess
import time
import os, sys
from . import commands

SPAWN_CMD = 'docker run --rm -m=%dg -t -d --cpuset-cpus=%d --name %s %s'
CP_MAZE_CMD = 'docker cp %s %s:/home/%s/maze.c'
CP_SEED_CMD = 'docker cp %s %s:/home/%s/%s'
CP_CMD = 'docker cp %s:/home/%s/workspace/outputs %s'
KILL_CMD = 'docker kill %s'
REMOVE_CMD = 'docker rm %s'

def spawn_cmd_in_docker(container, cmd_str):
    print('[*] Executing (in container %s): %s' % (container, cmd_str))
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

def get_container(tool,variant,name):
    return tool + '-' + str(variant) + '-' + str(name)

def spawn_docker(memory, name, tool, cpu = 0, variant=''):
    cmd = SPAWN_CMD % (memory, cpu, get_container(tool,variant,name), 'maze-' + tool)
    return commands.spawn_cmd(cmd)

def set_docker_maze(path, name, tool, variant=''):
    cmd = CP_MAZE_CMD % (path, get_container(tool,variant,name),get_user(tool))
    return commands.spawn_cmd(cmd)

def set_docker_seed(path, name, tool, variant=''):
    cmd = CP_SEED_CMD % (path, get_container(tool,variant,name),get_user(tool), path.split('/')[-1])
    return commands.spawn_cmd(cmd)

def run_docker(duration, tool, name, variant=''):
    user = get_user(tool)
    script = '/home/%s/tools/run_%s.sh' % (user, tool)
    src_path = '/home/%s/maze.c' % (user)
    cmd = '%s %s %s' % (script, src_path, duration)
    spawn_cmd_in_docker(get_container(tool,variant,name), cmd)# sleep timeout + extra 5 secs.

def collect_docker_results(tool,name, variant=''):
    user = get_user(tool)
    cmd = 'python3 /home/%s/tools/get_tcs.py /home/%s/workspace/outputs' % (user,user)
    return spawn_cmd_in_docker(get_container(tool,variant,name), cmd)

def copy_docker_results(tool, name , out_path, variant = ''):
    user = get_user(tool)
    return copy_docker_output(tool, name, out_path, user, variant)

def copy_docker_output(tool, name, out_path, user, variant=''):
    return commands.run_cmd(CP_CMD % (get_container(tool,variant,name), user, out_path if not os.path.isdir(out_path) else os.path.join(out_path,'.')))

def kill_docker(tool,name,variant=''):
    cmd = KILL_CMD % (get_container(tool,variant,name))
    commands.run_cmd(cmd)
    cmd = REMOVE_CMD % (get_container(tool,variant,name))
    return commands.spawn_cmd(cmd)


def run_mc(tool, name, memory, fuzzle, params,outdir):
    spawn_docker(memory,name,tool).wait()
    commands.generate_maze_in_docker(fuzzle,params,outdir)
    t_index = params['m'] - (0 if 'keepId' in params['t'] else 1)
    maze_path = os.path.join(outdir,'src',commands.get_maze_names(params)[t_index])
    set_docker_maze(maze_path,name,tool).wait()
    run_docker(1, tool, name)
    time.sleep(60)
    collect_docker_results(tool,name).wait()
    copy_docker_results(tool,name,outdir)
    kill_docker(tool, name).wait()

if __name__ == "__main__":
    commands.generate_maze_in_docker(*sys.argv[1:])