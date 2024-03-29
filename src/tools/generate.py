from ..runner import docker, maze_gen as mg
import logging

LOGGER = logging.getLogger(__name__)

def load(argv):
    gen = argv[0]
    out_dir = argv[1]
    params = argv[2:]
    param_string = mg.get_params_from_string(" ".join(params))
    if gen == 'container':
        mg.generate_maze_in_docker(param_string, 'gen')
    elif gen == 'local': 
        mg.generate_maze(param_string, out_dir)
    else:
        LOGGER.error("Invalid generation option, please use one of [container,local]")