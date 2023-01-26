import random
import sys, os, subprocess
import json

def load_config(path):
    with open(path) as f:
        txt = f.read()
    conf = json.loads(txt)

    assert conf['repeats'] > 0
    assert conf['duration'] > 0
    return conf

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

def get_param_string(params):
    res = ''
    for param, value in params.items():
        res += '-%s %s ' % (param, value)
    return res

def run_cmd(cmd_str):
    print('[*] Executing: %s' % cmd_str)
    cmd_args = cmd_str.split()
    try:
        return subprocess.run(cmd_args, capture_output=True, text=True)
    except Exception as e:
        print(e)
        exit(1)

def run_tools(conf, params, out_dir):
    if params['g'] == 'CVE_gen':
        generator = '%s_gen' % params['s'].split('/')[-1][0:-5]
    else:
        generator = params['g']
    filepath = 'temp/src/%s_%sx%s_%s_1_%s_1_%spercent_%s_ve.c' % \
        (params['a'], params['w'], params['h'],params['r'], params['t'],params['c'], generator)  
    assert os.path.exists(filepath)
    for name, properties in conf['tools'].items():
        result = run_cmd('%s %s' % (properties['command'], filepath))
        with open(out_dir + '/results.csv', 'a') as f:
            print(result.stdout + result.stderr)
            for value in params.values():
                f.write(str(value) + ',')
            f.write(name +  ',')
            if properties['results']['positive'] in result.stdout + result.stderr:
                f.write('1')
            elif properties['results']['negative'] in result.stdout + result.stderr:
                f.write('-1')
            else:
                f.write('0')
            f.write('\n')

def main(conf_path, out_dir):
    os.system('mkdir -p %s' % out_dir)
    conf = load_config(conf_path)
    for i in range(conf['repeats']):
        params = get_random_params(conf)
        run_cmd('%s/scripts/generate.sh -o temp %s' % (conf['fuzzleRoot'], get_param_string(params)))
        run_tools(conf, params, out_dir)
    run_cmd('rm -r temp')

if __name__ == '__main__':
    conf_path = sys.argv[1]
    out_dir = sys.argv[2]
    main(conf_path, out_dir)