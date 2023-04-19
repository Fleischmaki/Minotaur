import random
import sys, os, subprocess
import json
import time

SPAWN_CMD = 'docker run --rm -m=%dg --cpuset-cpus=%d -it -d --name %s %s'
CP_MAZE_CMD = 'docker cp %s %s:/home/%s/maze.c'
CP_CMD = 'docker cp %s:/home/%s/outputs %s'
CP_FRCON_CMD = 'docker cp %s:%s %s'
MOVE_CMD = 'mv %s %s'
REMOVE_CMD = 'rm -r %s'
REMOVE_MAZE_CMD = 'rm %s/temp/src/%s '
KILL_CMD = 'docker kill %s'

def wait_for_procs(procs):
    for p in procs:
        p.wait()

def load_config(path):
    with open(path) as f:
        txt = f.read()
    conf = json.loads(txt)

    assert conf['repeats'] > 0
    assert conf['duration'] > 0
    assert conf['workers'] > 0
    assert conf['memory'] > 0
    assert conf['transforms'] >= 0

    if 'verbosity' not in conf.keys():
        conf.verbosity = 'all'

    return conf

def spawn_cmd(cmd_str):
    print('[*] Executing: %s' % cmd_str)
    cmd_args = cmd_str.split()
    try:
        return subprocess.Popen(cmd_args, stdout=subprocess.DEVNULL)
    except Exception as e:
        print(e)
        exit(1)

def run_cmd(cmd_str):
    print('[*] Executing: %s' % cmd_str)
    cmd_args = cmd_str.split()
    try:
        return subprocess.run(cmd_args)
    except Exception as e:
        print(e)
        exit(1)

def run_cmd_in_docker(container, cmd_str):
    print("[*] Executing (in container): %s" % cmd_str)
    cmd_prefix = "docker exec -d %s /bin/bash -c" %  container
    cmd_args = cmd_prefix.split()
    cmd_args += [cmd_str]
    try:
        subprocess.run(cmd_args)
    except Exception as e:
        print(e)
        exit(1)

def get_user(tool): # Could not create user in seahorn docker
    if tool == 'seahorn':
        return 'usea'
    return 'maze'

def pick_values(head,value,tail):
    if 'min' in value:
        body = str(random.randint(value['min'], value['max']))
    else: 
        choice = random.choice(value)
        if choice == 0:
            return ''
        elif choice == 1:
            body = ''
        else:
            body = str(choice)
    return head + body + tail

def set_default(parameters, name, value):
    if name not in parameters.keys():
        parameters[name] = value
        print('Using default value %s for parameter %s' % (value, name))

def get_random_params(conf):
    params = conf['parameters']
    res = dict()
    for key, value in params.items():
        if key == 't':
            body = ''
            for tkey, tvalue in value.items():
                body += pick_values(tkey, tvalue, '_')
            body = body[:-1] # remove last _
        elif key == 's':
            if value.endswith('.smt2'):
                body = value
            else:
                body = os.path.join(value,random.choice(os.listdir(value)))
        else:
            body = pick_values('', value, '')
            ## Special cases
                        
        res[key] = body
    
    # default values 
    set_default(res,'a','Backtracking')
    set_default(res,'w',5)
    set_default(res,'h',5)
    set_default(res,'b','ve')
    set_default(res,'n',1)
    set_default(res,'t','id')
    set_default(res,'r',int(time.time()))
    set_default(res,'c',0)
    set_default(res,'g','default_gen')
    set_default(res,'u',0)

    if 'u' in res.keys():
        res['w'] = 1
        res['h'] = 1
    return res


def get_targets(conf):
    targets = []

    repeats = conf['repeats']
    for i in range(repeats):
        params = get_random_params(conf)
        mazes = get_maze_names(params, int(conf['transforms']))
        for tool in conf['tool']:
            for j in range(len(mazes)):
                targets.append((mazes[j], tool,i*conf['transforms'] + j,params))
    return targets

def get_maze_names(params,transforms):
    if params['g'] == 'CVE_gen':
        generator = '%s_gen' % params['s'].split('/')[-1][0:-5]
    else:
        generator = params['g']
    min = 0 if 'keepId' in params['t'] else 1
    return ['%s_%sx%s_%s_0_%s_t%d_%spercent_%s_ve.c' %  (params['a'], params['w'], params['h'],params['r'], params['t'],i,params['c'], generator) for i in range(min,transforms)]


def generateMaze(conf, params):
    param_string = ''
    for param, value in params.items():
        param_string += '-%s %s ' % (param, value)
    out_dir = os.path.join(conf['fuzzleRoot'], 'temp')
    return run_cmd('%s/scripts/generate.sh -o %s -m %s %s' % (conf['fuzzleRoot'], out_dir, conf['transforms'], param_string)) # TODO: Figure out how to multithread this
                                                                                                                              # Or just set greater values for transforms 
def fetch_works(conf,targets):
    works = []
    for i in range(conf['workers']):
        if len(targets) <= 0:
            break
        _, tool, id, params = t = targets.pop(0)
        if id % (int(conf['transforms'])) == 0 and tool == conf['tool'][0]:
            generateMaze(conf,params) # lazily generate mazes
        works.append(t)
    return works

def spawn_containers(conf, works):
    procs = []
    for i in range(len(works)):
        maze, tool, id, _ = works[i]

        user = get_user(tool)

        image = 'maze-%s' % tool
        container = '%s-%s' % (tool,id)
        # Spawn a container
        cmd = SPAWN_CMD % (conf['memory'], i, container, image)
        procs.append(spawn_cmd(cmd))
    wait_for_procs(procs)

    procs = []
    for i in range(len(works)):
        maze, tool, id, _ = works[i]
        user = get_user(tool)
        container = '%s-%s' % (tool,id)
        # Copy maze in the container
        cmd = CP_MAZE_CMD % ( os.path.join(conf['fuzzleRoot'], 'temp','src',maze), container, user)
        procs.append(spawn_cmd(cmd))
    wait_for_procs(procs)

def run_tools(conf,works):
    duration = conf['duration']
    for i in range(len(works)):
        _, tool, id, _ = works[i]
        container = '%s-%s' % (tool,id)

        user = get_user(tool)
        script = '/home/%s/tools/run_%s.sh' % (user, tool)
        src_path = '/home/%s/maze.c' % (user)
        cmd = '%s %s %s' % (script, src_path, duration)

        run_cmd_in_docker(container, cmd)

    time.sleep(duration*60 + 5) # sleep timeout + extra 5 secs.

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

    time.sleep(5)


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
        if (conf['verbosity'] == 'bug' or conf['verbosity'] == 'bug_only') and tag not in ('fp', 'fn', 'er'):
            run_cmd(REMOVE_CMD % out_path)
            if conf['verbosity'] == 'bug_only':
                break
        with open(out_dir + '/summary.csv', 'a') as f:
            f.write(tool + ',' + str(id % conf['transforms']) + ',')
            for key, value in params.items():
                if key == 'g':
                    f.write(str(params['s'].split('/')[-1])[:-5] + ',')
                elif key == 'u':
                    f.write('1,')
                elif key in conf['parameters'].keys():
                    f.write(str(value) + ',')
            f.write('%s,%s,' % (runtime, tag))
            f.write('\n')
        if conf['verbosity'] == 'summary': 
            run_cmd(REMOVE_CMD % out_path)

    time.sleep(5)

def write_summary_header(conf, out_dir):
    with open(out_dir + '/summary.csv', 'w') as f:
        f.write('tool,id,')
        for key in conf['parameters'].keys():
            f.write(str(key)+',')
        f.write('runtime,status\n')


def kill_containers(works):
    procs = []
    for i in range(len(works)):
        _, tool, id, _ = works[i]
        container = '%s-%s' % (tool,id)
        cmd = KILL_CMD % container
        procs.append(spawn_cmd(cmd))
    wait_for_procs(procs)

def cleanup(conf, targets):
    run_cmd(REMOVE_CMD % os.path.join(conf['fuzzleRoot'],'temp'))
    if len(targets) == 0:
        run_cmd(REMOVE_CMD % os.path.join(conf['fuzzleRoot'], 'temp.txt')) 
        return # We are done
    _, tool, id, params = targets[0]
    if not (id % int(conf['transforms']) == 0 and tool == conf['tool'][0]) : # Maze will be generated anyways
        generateMaze(conf,params)

def main(conf_path, out_dir):
    os.system('mkdir -p %s' % out_dir)

    conf = load_config(conf_path)
    targets = get_targets(conf)
    write_summary_header(conf, out_dir)
        
    while len(targets) > 0:
        works = fetch_works(conf, targets)
        spawn_containers(conf, works)
        run_tools(conf, works)
        store_outputs(conf, out_dir, works)
        kill_containers(works)
        cleanup(conf, targets) 
    
    cleanup(conf, targets) 

if __name__ == '__main__':
    conf_path = sys.argv[1]
    out_dir = sys.argv[2]
    main(conf_path, out_dir)