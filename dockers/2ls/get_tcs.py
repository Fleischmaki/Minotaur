import os, sys

def save_tc(dest_dir, tc_path, start_time, end_time, sig, expected_result='error', copy_content=True):
    elapsed_time = end_time - start_time
    if sig == '':
        sig = 'tc'
    elif sig == 'positive':
        sig = 'tp' if expected_result == 'error' else 'fp'
    elif sig == 'negative':
        sig = 'fn' if expected_result == 'error' else 'tn'

    name = '%011.5f_%s' % (elapsed_time, sig)
    file_path = os.path.join(dest_dir, name)
    if copy_content:
        os.system('mv %s %s' % (tc_path, file_path))
    else:
        os.system('touch %s' % (file_path))
        os.system('rm %s' % (tc_path))

WORKDIR = '/home/maze/workspace'
OUTDIR = '/home/maze/workspace/outputs'

def main(dest_dir,expected_result, verbosity):           
    # Create destination directory
    os.system('mkdir -p %s' % dest_dir)
    for file in filter(lambda f: 'res' in f, os.listdir(OUTDIR)):
        name = file[3:]
        respath = '%s/%s' %(OUTDIR,file)
        try:
            start_file = os.path.join(WORKDIR, '.start%s' % name)
            start_time = os.path.getmtime(start_file)
            end_file = os.path.join(WORKDIR, '.end%s' % name)
            end_time = os.path.getmtime(end_file)       
            resfile = open(respath, "r").read()
            file_dir = os.path.join(dest_dir,name) 
            os.system('mkdir -p %s' % file_dir)
        except Exception as e:
            print("NOTE: Failed to parse file %s: %s" % (file, str(e)))
            continue

        if ('VERIFICATION FAILED' in resfile):
            save_tc(file_dir, respath, start_time, end_time, 'positive', expected_result)

        elif ('VERIFICATION SUCCESSFUL' in resfile):
            save_tc(file_dir, respath, start_time, end_time, 'negative', expected_result)

        elif ('VERIFICATION INCONCLUSIVE' in resfile):
            save_tc(file_dir, respath, start_time, end_time, 'uk', copy_content = verbosity == 'all')
        elif ('ERROR' or '--- begin invariant violation report ---' in resfile):
                save_tc(file_dir, respath, start_time, end_time, 'er', copy_content = verbosity in ('error','all'))
        else:
            save_tc(file_dir, respath, start_time, end_time, 'to', copy_content = verbosity == 'all')
    
if __name__ == '__main__':
    dest_dir = sys.argv[1]
    expected_result = sys.argv[2]
    verbosity = sys.argv[3]
    main(dest_dir, expected_result, verbosity)
