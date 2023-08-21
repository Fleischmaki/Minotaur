import subprocess
import time
import os, sys
from . import commands, maze_gen

SPAWN_CMD = 'docker run --rm -m=%dg -t -d --cpuset-cpus=%d --name %s %s'
CP_MAZE_CMD = 'docker cp %s %s:/home/%s/maze.c'
CP_SEED_CMD = 'docker cp %s %s:/home/%s/%s'
CP_CMD = 'docker cp %s:/home/%s/workspace/%s %s'
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
    cmd = '%s %s %s %s' % (script, src_path, duration, variant)
    return spawn_cmd_in_docker(get_container(tool,variant,name), cmd)

def collect_docker_results(tool,name, variant=''):
    user = get_user(tool)
    cmd = 'python3 /home/%s/tools/get_tcs.py /home/%s/workspace/outputs' % (user,user)
    return spawn_cmd_in_docker(get_container(tool,variant,name), cmd)

def copy_docker_results(tool, name , out_path, variant = ''):
    user = get_user(tool)
    return copy_docker_output(tool, name, out_path, user, variant)

def copy_docker_output(tool, name, out_path, user, variant=''):
    cont = get_container(tool,variant,name)
    if not os.path.isdir(out_path):
        return commands.run_cmd(CP_CMD % (cont, user, 'outputs', out_path))
    if os.path.isdir(os.path.join(out_path,'src')):
        for dir in ['src','smt','png','txt','smt','bin']:
            commands.run_cmd(CP_CMD % (cont, user, os.path.join('outputs',dir,'.'), os.path.join(out_path, dir)))
    return commands.run_cmd(CP_CMD % (cont, user, 'outputs/.', out_path))

def kill_docker(tool,name,variant=''):
    cmd = KILL_CMD % (get_container(tool,variant,name))
    commands.run_cmd(cmd)
    cmd = REMOVE_CMD % (get_container(tool,variant,name))
    return commands.spawn_cmd(cmd)


def run_mc(tool,variant, name, memory, params,outdir, timeout=1):
    spawn_docker(memory,name,tool,variant=variant).wait()
    maze_gen.generate_maze(params,out_dir = outdir)
    t_index = params['m'] - (0 if 'keepId' in params['t'] else 1)
    maze_path = os.path.join(outdir,'src',maze_gen.get_maze_names(params)[t_index]) #'outputs' should not be necessary but somehow it is ¯\_(ツ)_/¯
    set_docker_maze(maze_path,name,tool,variant).wait()
    run_docker(timeout, tool, name, variant).wait()
    collect_docker_results(tool,name,variant).wait()
    copy_docker_results(tool,name,os.path.join(outdir, 'res'),variant)
    kill_docker(tool,name,variant).wait()