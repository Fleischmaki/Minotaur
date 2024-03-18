from . import test
from ..runner import commands
import time, json, os, math

def load_config(path):
    with open(path) as f:
        txt = f.read()
    conf = json.loads(txt)

    print(conf)

    if 'verbosity' not in conf.keys():
        conf['verbosity'] = 'bug_only'
    if 'maze_gen' not in conf.keys():
        conf['maze_gen'] = 'local'
    if 'expected_result' not in conf.keys():
        conf['maze_gen'] = 'error'
    if 'abort_on_error' not in conf.keys():
        conf['abort_on_error'] = True
    if 'avg' not in conf.keys():
        conf['avg'] = 1

    assert len(conf['mazes']) > 0
    assert len(conf['duration']) > 0
    assert len(conf['transforms']) > 0

    assert conf['repeats'] > 0
    assert conf['workers'] > 0
    assert conf['memory'] > 0
    assert conf['maze_gen'] in ['local', 'container']
    assert conf['verbosity'] in ['all','summary','bug','bug_only']
    assert conf['expected_result'] in ['error','safe']

    return conf


def load(argv):
    conf = load_config(os.path.join(test.get_minotaur_root(),'experiments',argv[0] + '.conf.json'))
    outdir = argv[1]

    commands.run_cmd('mkdir -p %s' % outdir)
    resfile = open(os.path.join(outdir, 'times'), 'w')
    resfile.write("run_nr, time, mazes_tested\n")    

    runs = conf['repeats']
    conf['repeats'] = conf['mazes']

    for i in range(runs):
        curr_conf = dict(conf)
        for key in ['transforms','duration','repeats']:
            set_param_value(curr_conf, conf, key, i)
        total_targets = max(curr_conf['transforms'],1) * curr_conf['repeats'] 
        times = []
        targets = []
        for j in range(conf['avg']):
            start = time.time()
            remaining_targets = test.main(curr_conf, os.path.join(outdir, 'run%d_%d' % (i,j))) 
            end = time.time()
            times.append(end-start)
            targets.append(total_targets - remaining_targets)
        resfile.write("%d,%f,%d\n" % (i, sum(times)/len(times),sum(targets)/len(targets)))

def set_param_value(new_conf, old_conf, key, i):
    new_conf[key] = old_conf[key][i % len(old_conf[key])]
