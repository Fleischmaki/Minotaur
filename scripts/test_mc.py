import random
import sys, os, subprocess
import json
import time

NUM_WORKERS = 12
SPAWN_CMD = 'docker run --rm -m=%dg --cpuset-cpus=%d -it -d --name %s %s'
CP_MAZE_CMD = 'docker cp %s %s:/home/%s/maze.c'
CP_CMD = 'docker cp %s:/home/%s/outputs %s'
CP_FRCON_CMD = 'docker cp %s:%s %s'
MOVE_CMD = 'mv %s %s'
REMOVE_CMD = 'rm -r %s'
KILL_CMD = 'docker kill %s'

def load_config(path):
    with open(path) as f:
        txt = f.read()
    conf = json.loads(txt)

    assert conf['repeats'] > 0
    assert conf['duration'] > 0
    assert conf['workers'] > 0
    assert conf['memory'] > 0

    if 'verbosity' not in conf.keys():
        conf.verbosity = 'all'

    return conf

def run_cmd(cmd_str):
    print('[*] Executing: %s' % cmd_str)
    cmd_args = cmd_str.split()
    try:
        return subprocess.run(cmd_args, capture_output=True, text=True)
    except Exception as e:
        print(e)
        exit(1)

def run_cmd_in_docker(container, cmd_str):
    print("[*] Executing (in container): %s" % cmd_str)
    cmd_prefix = "docker exec -d %s /bin/bash -c" %  container
    cmd_args = cmd_prefix.split()
    cmd_args += [cmd_str]
    try:
        subprocess.call(cmd_args)
    except Exception as e:
        print(e)
        exit(1)

def get_user(tool): # Could not create user in seahorn docker
    if tool == 'seahorn':
        return 'usea'
    return 'maze'

def get_random_params(conf):
    params = conf['parameters']
    res = dict()
    for key, value in params.items():
        if 'min' in value:
            body = str(random.randint(value['min'], value['max']))
        else:
            body = random.choice(value)

        ## Special cases
        if key == 't':
            body = 'sh_rw' + body
        if 'CVE' in body: 
            file = body.split('_')[0]
            body = 'CVE_gen'
            res['s'] = '%s/CVEs/%s.smt2' % (conf['fuzzleRoot'], file)

        res[key] = body
    # default values for other parameters 
    res['n'] = 1
    res['b'] = 've'
    res['m'] = 1
    return res


def get_targets(conf):
    targets = []

    repeats = conf['repeats']
    for i in range(repeats):
        params = get_random_params(conf)
        mazes = generateMaze(conf, params)
        for tool in conf['tool']:
            targets.append((mazes['original'], tool,2*i,params))
            targets.append((mazes['transformed'], tool,2*i+1,params))
    return targets

def generateMaze(conf, params):
    param_string = ''
    for param, value in params.items():
        param_string += '-%s %s ' % (param, value)
    run_cmd('%s/scripts/generate.sh -o temp %s' % (conf['fuzzleRoot'], param_string))
    if params['g'] == 'CVE_gen':
        generator = '%s_gen' % params['s'].split('/')[-1][0:-5]
    else:
        generator = params['g']
    return {
        'original' : '%s_%sx%s_%s_1_%s_0_%spercent_%s_ve.c' %  (params['a'], params['w'], params['h'],params['r'], params['t'],params['c'], generator),  
        'transformed' : '%s_%sx%s_%s_1_%s_1_%spercent_%s_ve.c' %  (params['a'], params['w'], params['h'],params['r'], params['t'],params['c'], generator),
    }

def fetch_works(conf,targets):
    works = []
    for i in range(conf['workers']):
        if len(targets) <= 0:
            break
        works.append(targets.pop(0))
    return works

def spawn_containers(conf, works):
    for i in range(len(works)):
        maze, tool, id, _ = works[i]

        user = get_user(tool)

        image = 'maze-%s' % tool
        container = '%s-%s' % (tool,id)
        # Spawn a container
        cmd = SPAWN_CMD % (conf['memory'], i, container, image)
        run_cmd(cmd)

        # Copy maze in the container
        cmd = CP_MAZE_CMD % ('temp/src/%s' % maze, container, user)
        run_cmd(cmd)

def run_tools(conf,works):
    for i in range(len(works)):
        _, tool, id, _ = works[i]
        container = '%s-%s' % (tool,id)

        user = get_user(tool)
        script = '/home/%s/tools/run_%s.sh' % (user, tool)
        src_path = '/home/%s/maze.c' % (user)
        duration = conf['duration']
        cmd = '%s %s %s' % (script, src_path, duration)

        run_cmd_in_docker(container, cmd)

    time.sleep(duration*60 + 60) # sleep timeout + extra 1 min.

def store_outputs(conf, out_dir, works):
    # First, collect testcases in /home/maze/outputs
    for i in range(len(works)):
        _, tool, id, _ = works[i]
        if tool == 'seahorn':
            user = 'usea'
        else:
            user = 'maze'
        container = '%s-%s' % (tool,id)

        cmd = 'python3 /home/%s/tools/get_tcs.py /home/%s/outputs' % (user,user)
        run_cmd_in_docker(container, cmd)

    time.sleep(60)

    # Write summary header
    with open(out_dir + '/summary.csv', 'w') as f:
        f.write('tool,')
        for key in conf['parameters'].keys():
            f.write(str(key)+',')
        f.write('runtime,status\n')

    # Next, store outputs to host filesystem
    for i in range(len(works)):
        maze, tool, id, params = works[i]
        container = '%s-%s' % (tool,id)
        out_path = os.path.join(out_dir, tool, maze)
        os.system('mkdir -p %s' % out_path)

        user = get_user(tool)
        cmd = CP_CMD % (container, user, out_path)
        run_cmd(cmd)

        # Write file details into summary
        runtime = 'notFound'
        tag = 'notFound'
        for filename in os.listdir(os.path.join(out_path,'outputs')):
            if '_' in filename:
                runtime, tag = filename.split('_')
        if conf['verbosity'] == 'bug' and tag not in ('fp', 'fn', 'er'):
            run_cmd(REMOVE_CMD % out_path)
            break
        with open(out_dir + '/summary.csv', 'a') as f:
            f.write(tool + ',')
            for key, value in params.items():
                if key == 'g':
                    f.write(str(params['g']))
                if key not in ('m','n','b','s'):
                    f.write(str(value) + ',')
            f.write('%s,%s,' % (runtime, tag))
            f.write('\n')
        if conf['verbosity'] == 'summary': 
            run_cmd(REMOVE_CMD % out_path)
             
    time.sleep(60)


def kill_containers(works):
    for i in range(len(works)):
        _, tool, id, _ = works[i]
        container = '%s-%s' % (tool,id)
        cmd = KILL_CMD % container
        run_cmd(cmd)

def cleanup():
    run_cmd(REMOVE_CMD % 'temp')

def main(conf_path, out_dir):
    os.system('mkdir -p %s' % out_dir)

    conf = load_config(conf_path)
    targets = get_targets(conf)

    while len(targets) > 0:
        works = fetch_works(conf, targets)
        spawn_containers(conf, works)
        run_tools(conf, works)
        store_outputs(conf, out_dir, works)
        kill_containers(works)
    cleanup()


if __name__ == '__main__':
    conf_path = sys.argv[1]
    out_dir = sys.argv[2]
    main(conf_path, out_dir)