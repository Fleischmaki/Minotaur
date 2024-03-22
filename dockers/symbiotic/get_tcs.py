import os, sys

def save_tc(dest_dir, tc_path, start_time, end_time, sig, expected_result='error'):
    elapsed_time = end_time - start_time
    if sig == '':
        sig = 'tc'
    elif sig == 'positive':
        sig = 'tp' if expected_result == 'error' else 'fp'
    elif sig == 'negative':
        sig = 'fn' if expected_result == 'error' else 'tn'

    name = '%011.5f_%s' % (elapsed_time, sig)
    file_path = os.path.join(dest_dir, name)
    os.system('cp %s %s' % (tc_path, file_path))


WORKDIR = '/home/maze/workspace'
OUTDIR = '/home/maze/workspace/outputs'

def main(dest_dir,expected_result):           
    # Create destination directory
    os.system('mkdir -p %s' % dest_dir)
    for file in filter(lambda f: '_' in f, os.listdir(OUTDIR)):
        respath = '%s/%s' %(OUTDIR,file)
        try:
            start_file = os.path.join(WORKDIR, '.start%s' % file)
            start_time = os.path.getmtime(start_file)
            end_file = os.path.join(WORKDIR, '.end%s' % file)
            end_time = os.path.getmtime(end_file)       
            resfile = open(respath, "r").read()
            file_dir = os.path.join(dest_dir,"maze_%s" % file) 
            os.system('mkdir -p %s' % file_dir)
        except Exception as e:
            print("NOTE: Failed to parse file %s: %s", file, str(e))
            continue

        resfile = open(respath, "r").read()
        # True positives
        if ('RESULT: false(unreach-call)' in resfile):
            save_tc(file_dir, respath, start_time, end_time, 'positive', expected_result)

        # False negatives #TODO
        elif ('RESULT: true' in resfile):
            save_tc(file_dir, respath, start_time, end_time, 'negative', expected_result)

        # Crashes/Errors
        elif ('RESULT: unknown' in resfile):
            save_tc(file_dir, respath, start_time, end_time, 'uk')

        elif ('RESULT: ERROR' in resfile):
            save_tc(file_dir, respath, start_time, end_time, 'er')

        # Timeout
        else: 
            save_tc(file_dir, respath, start_time, end_time, 'to')

if __name__ == '__main__':
    dest_dir = sys.argv[1]    
    expected_result = sys.argv[2]
    main(dest_dir, expected_result)
