import subprocess, os, logging, time
from . import commands, maze_gen

LOGGER = logging.getLogger(__name__)

DOCKER_PREFIX = 'minotaur-'
DOCKER_COMMAND = 'docker'
HOST_NAME = '/mazes'
BATCH_FILE_FORMAT = 'batch_%d.txt'

SPAWN_CMD_CPU = f'{DOCKER_COMMAND} run --rm -m=%dg -t -d --cpus=1 --cpuset-cpus=%d --name %s --mount type=bind,source=%s,destination={HOST_NAME}%s %s' 
SPAWN_CMD_NOCPU = f'{DOCKER_COMMAND} run --rm -m=%dg -t -d --cpus=1 --name %s --mount type=bind,source=%s,destination={HOST_NAME}%s %s'
CP_MAZE_CMD = DOCKER_COMMAND + ' cp %s %s:/home/%s/%s'
CP_SEED_CMD = DOCKER_COMMAND + ' cp %s %s:/home/%s/%s'
CP_CMD = DOCKER_COMMAND + ' cp %s:/home/%s/workspace/%s %s'
KILL_CMD = DOCKER_COMMAND + ' kill %s'
REMOVE_CMD = DOCKER_COMMAND + ' rm %s'

def spawn_cmd_in_docker(container, cmd_str, timeout=-1):
    cmd_prefix = DOCKER_COMMAND + ' exec %s /bin/bash -c' %  container
    if timeout > 0:
        cmd_prefix = DOCKER_COMMAND + ' exec %s timeout %ds /bin/bash -c' %  (container, timeout)
    cmd_args = cmd_prefix.split()
    cmd_args += [cmd_str]
    LOGGER.info('Executing (in container %s): %s' % (container, ' '.join(cmd_args[3:])))
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

def spawn_docker(memory, name, tool, maze_dir, cpu = -1, host_is_readonly=False):
    if cpu >= 0:
        cmd = SPAWN_CMD_CPU % (memory, cpu, get_container(tool,name), os.path.abspath(maze_dir), ',readonly' if host_is_readonly else '', DOCKER_PREFIX + tool)
    else:
        cmd = SPAWN_CMD_NOCPU % (memory, get_container(tool,name), os.path.abspath(maze_dir), ',readonly' if host_is_readonly else '', DOCKER_PREFIX + tool) # TODO rewrite this, this is disgusting
    return commands.spawn_cmd(cmd)

def set_docker_seed(path, name, tool):
    cmd = CP_SEED_CMD % (path, get_container(tool,name),get_user(tool), os.path.split(path)[1])
    return commands.spawn_cmd(cmd)

def run_docker(duration, tool, name, variant='', flags='', batch_id=0):
    user = get_user(tool)
    script = '/home/%s/tools/run_%s.sh' % (user, tool)
    src_path = '%s/%s' % (HOST_NAME,BATCH_FILE_FORMAT % batch_id)
    cmd = ' '.join(map(str,[script, src_path, duration,variant,flags]))
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
    return commands.spawn_cmd(cmd)


def run_pa(tool,variant,flags, name, params,outdir, memory = 4,  timeout=1, gen='container', expected_result='error'):
    if gen == 'container':
        maze_gen.setup_generation_docker(params,outdir,name)
        maze_gen.generate_maze_in_docker(params,name).wait()
        kill_docker('gen', name)
    else:
        maze_gen.generate_maze(params,outdir)
    t_index = params['m'] - (0 if 'keepId' in params['t'] else 1)
    maze = maze_gen.get_maze_names(params)[t_index]
    with (open(os.path.join(outdir, 'src', BATCH_FILE_FORMAT % 0),'w')) as batchfile: 
        batchfile.write('%s/%s' % (HOST_NAME, maze))
    spawn_docker(memory,name,tool,os.path.join(outdir,'src')).wait()
    run_docker(timeout, tool, name, variant,flags).wait()
    collect_docker_results(tool,name,expected_result).wait()
    copy_docker_results(tool,name,os.path.join(outdir, maze))
    kill_docker(tool,name).wait()