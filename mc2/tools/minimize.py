import sys, os, time
from ..runner import *
       
def main(maze_path,tool,memory,smt_path,accuracy):
    commands.run_cmd('mkdir -p temp_min')
    maze = maze_path.split('/')[-1][:-2] # Cut .c
    params = maze_gen.get_params_from_maze(maze,smt_path)
    outdir = os.path.join(os.getcwd(),'temp_min')
    base_transform = params['t']
    constraints = 0
    change = 50 
    while abs(change) > accuracy and abs(change) > 0:
        constraints += change
        params['t'] = base_transform + '_dc' + str(constraints)
        docker.run_mc(tool,'min', memory,params,outdir)       
        change = -abs(change)
        for file in os.listdir(os.path.join(outdir,'outputs')):
            if 'fn' in file: # Still false negative
                print('Removed %s%% of constraints: ' % constraints)
                change *= -1 
                break 
        change = change // 2
        print(change, accuracy)

def load(argv):
    maze = argv[0]
    tool = argv[1]
    memory = int(argv[2])
    smt_path = argv[3]
    accuracy = int(argv[4])
    main(maze, tool, memory, smt_path, accuracy)