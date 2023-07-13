import sys, os, time
import Fuzzle.runner.docker as docker


        
def main(maze_path,tool,memory,fuzzle,smt_path,accuracy):
    docker.run_cmd('mkdir -p temp_min')
    maze = maze_path.split('/')[-1][:-2] # Cut .c
    params = docker.get_params_from_maze(maze,smt_path)
    outdir = os.path.join(os.getcwd(),'temp_min')
    base_transform = params['t']
    constraints = 0
    change = 50 
    while abs(change) > accuracy and abs(change) > 0:
        constraints += change
        params['t'] = base_transform + '_dc' + str(constraints)
        docker.run_mc(tool,'min', memory, fuzzle, params,outdir)       
        change = -abs(change)
        for file in os.listdir(os.path.join(outdir,'outputs')):
            if 'fn' in file: # Still false negative
                print('Removed %s%% of constraints: ' % constraints)
                change *= -1 
                docker.run_cmd('rm ' + os.path.join(outdir, 'outputs', file))
                break 
        change = change // 2
        print(change, accuracy)

if __name__ == '__main__':
    maze = sys.argv[1]
    tool = sys.argv[2]
    memory = int(sys.argv[3])
    fuzzle = sys.argv[4]
    smt_path = sys.argv[5]
    accuracy = int(sys.argv[6])
    main(maze, tool, memory, fuzzle, smt_path, accuracy)