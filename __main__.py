import random
import sys, os
import json
import time
from runner import *

REMOVE_CMD = 'rm -r %s'

def load_config(path):
    with open(path) as f:
        txt = f.read()
    conf = json.loads(txt)

    if 'verbosity' not in conf.keys():
        conf['verbosity'] = 'all'
    if 'maze_gen' not in conf.keys():
        conf['maze_gen'] = 'local'


    assert conf['repeats'] > 0
    assert conf['duration'] > 0
    assert conf['workers'] > 0
    assert conf['memory'] > 0
    assert conf['transforms'] >= 0
    assert conf['maze_gen'] in ['local', 'container']
    assert conf['verbosity'] in ['all','summary','bug','bug_only']

    return conf

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
    set_default(res,'t','keepId')
    set_default(res,'r',int(time.time()))
    set_default(res,'c',0)
    set_default(res,'g','default_gen')
    set_default(res,'u',0)
    set_default(res,'m',int(conf['transforms']))

    if 'u' in res.keys():
        res['w'] = 1
        res['h'] = 1
    elif res['w'] < 5 and res['h'] < 5:
        res['h'] = 5 # mazelib gets stuck when generating 4x4 or smaller mazes
    return res


def get_targets(conf):
    targets = []

    repeats = conf['repeats']
    for i in range(repeats):
        params = get_random_params(conf)
        mazes = maze_gen.get_maze_names(params)
        for tool in conf['tool']:
            for j in range(len(mazes)):
                targets.append((mazes[j], tool,i*params['m'] + j,params))
    return targets # Or just set greater values for transforms 

def fetch_works(conf,targets):
    works = []
    mazes = []
    for i in range(conf['workers']):
        if len(targets) <= 0:
            break
        _, tool, id, params = t = targets.pop(0)
        works.append(t)
        if id % (int(conf['transforms'])) == 0 and tool == conf['tool'][0]:
            if conf['maze_gen'] == 'container':
                mazes.append(params)
            else:
                maze_gen.generate_maze(get_fuzzle_root(), params, get_temp_dir(conf))
    if conf['maze_gen'] == 'container':
        maze_gen.generate_mazes(mazes, get_temp_dir(conf))
    return works

def get_temp_dir(conf):
    return os.path.join(get_fuzzle_root(), 'temp')

def get_maze_dir(conf, maze=''):
    return os.path.join(get_temp_dir(conf),'src', maze)

def spawn_containers(conf, works):
    procs = []
    for i in range(len(works)):
        maze, tool, id, _ = works[i]
        docker.spawn_docker(conf['memory'], id, tool,i).wait()

    procs = []
    for i in range(len(works)):
        maze, tool, id, _ = works[i]
        # Copy maze in the container
        procs.append(docker.set_docker_maze(get_maze_dir(conf,maze), id,tool))
    commands.wait_for_procs(procs)
    print("Done waiting")

def run_tools(conf,works):
    duration = conf['duration']
    for i in range(len(works)):
        _, tool, id, _ = works[i]
        docker.run_docker(duration, tool, id)
    time.sleep(duration*60 + 15) 

def store_outputs(conf, out_dir, works):
    for i in range(len(works)):
        maze, tool, id, params = works[i]
        docker.collect_docker_results(tool, id)
    time.sleep(10)

    for i in range(len(works)):
        maze, tool, id, params = works[i]
        out_path = os.path.join(out_dir, tool, maze)
        os.system('mkdir -p %s' % out_path)
        docker.copy_docker_results(tool, id, out_path)

        # Write file details into summary
        runtime = 'notFound'
        tag = 'notFound'
        for filename in os.listdir(os.path.join(out_path,'outputs')):
            if '_' in filename:
                runtime, tag = filename.split('_')
        if (conf['verbosity'] == 'bug' or conf['verbosity'] == 'bug_only') and tag not in ('fp', 'fn', 'er', 'uk', 'notFound'):
            commands.run_cmd(REMOVE_CMD % out_path)
            if conf['verbosity'] == 'bug_only':
                break
        offset = 0 if 'keepId' in params['t'] else 1
        with open(out_dir + '/summary.csv', 'a') as f:
            f.write(tool + ',' + str(id % conf['transforms'] + offset) + ',')
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
            commands.run_cmd(REMOVE_CMD % out_path)

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
        procs.append(docker.kill_docker(tool,id))
    commands.wait_for_procs(procs)
    time.sleep(10)

def cleanup(conf, targets):
    commands.run_cmd(REMOVE_CMD % get_temp_dir(conf))
    if len(targets) == 0:
        return # We are done
    _, tool, id, params = targets[0]
    if not (id % int(conf['transforms']) == 0 and tool == conf['tool'][0]) : # Maze will be generated anyways
        if conf['maze_gen'] == 'container':
            maze_gen.generate_mazes([params], get_temp_dir(conf))
        else:
            maze_gen.generate_maze(get_fuzzle_root(), params, get_temp_dir(conf))

def get_fuzzle_root():
    return os.path.dirname(os.path.realpath(__file__))

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
    conf_path = os.path.join(get_fuzzle_root(),'test',sys.argv[1] + '.conf.json')
    out_dir = sys.argv[2]
    main(conf_path, out_dir)