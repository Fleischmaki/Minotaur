from ..runner import docker, maze_gen as mg
import logging

LOGGER = logging.getLogger(__name__)

def load(argv):
    gen = argv[0]
    out_dir = argv[1]
    param_string = argv[2:]
    params = mg.get_params_from_string(" ".join(param_string))
    if gen == 'container':
        mg.setup_generation_docker(params, out_dir, 0)
        mg.generate_maze_in_docker(params, 0).wait()
        return docker.kill_docker('gen',0).wait()
    if gen == 'local':
        return mg.generate_maze(params, out_dir)
    LOGGER.error("Invalid generation option, please use one of [container,local]")