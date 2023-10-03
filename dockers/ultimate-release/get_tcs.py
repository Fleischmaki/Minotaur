import os, sys

def save_tc(dest_dir, tc_path, start_time, end_time, sig):
    elapsed_time = end_time - start_time
    name = '%011.5f_%s' % (elapsed_time, sig)
    file_path = os.path.join(dest_dir, name)
    os.system('cp %s %s' % (tc_path, file_path))


WORKDIR = '/home/maze/workspace'
OUTDIR = '/home/maze/workspace/outputs'

def main(dest_dir):           
    # Create destination directory
    os.system('mkdir -p %s' % dest_dir)

    start_file = os.path.join(WORKDIR, '.start')
    start_time = os.path.getmtime(start_file)
    end_file = os.path.join(WORKDIR, '.end')
    end_time = os.path.getmtime(end_file)       

    respath = '%s/res' %(OUTDIR)
    resfile = open(respath,'r').read()
    if ('FALSE' in resfile):
        save_tc(dest_dir, respath, start_time, end_time, 'tp')

    elif ('TRUE' in resfile):
        save_tc(dest_dir, respath, start_time, end_time, 'fn')

    elif ('UNKNOWN' in resfile):
        save_tc(dest_dir, respath, start_time, end_time, 'uk')
    # Timeout
    elif ('Killed' in resfile):  # Killed by 15
        save_tc(dest_dir, respath, start_time, end_time, 'to')
    else:
        save_tc(dest_dir, respath, start_time, end_time, 'er')

if __name__ == '__main__':
    dest_dir = sys.argv[1]
    main(dest_dir)
