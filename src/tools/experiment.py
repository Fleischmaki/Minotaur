from . import test
from ..runner import commands
import json, os, time

def load_config(path: str) -> dict:
    with open(path) as f:
        txt = f.read()
    
    conf = json.loads(txt)

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
    if 'gen_time' not in conf.keys():
        conf['gen_time'] = 120

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
    resfile.write("run_nr, time\n")    

    runs = conf['repeats']
    conf['repeats'] = conf['mazes']

    variable_keys = map(lambda kv: kv[0],(filter(lambda kv: type(kv[1]) is list, conf.items())))
    

    for i in range(runs):
        curr_conf = dict(conf)
        for key in variable_keys:
            set_param_value(curr_conf, conf, key, i)
        times = []
        for j in range(conf['avg']):
            start = time.time()
            test.main(curr_conf, os.path.join(outdir, 'run%d_%d' % (i,j))) 
            end = time.time()
            times.append(end-start)
        resfile.write("%d,%f\n" % (i, sum(times)/len(times)))

def set_param_value(new_conf, old_conf, key, i):
    new_conf[key] = old_conf[key][i % len(old_conf[key])]
    if key == 'transforms':
        new_conf['parameters']['t']['keepId'] = [1] 
