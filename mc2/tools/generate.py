from ..runner import docker, maze_gen as mg

def load(argv):
    out_dir = argv[0]
    params = argv[1:]
    mg.generate_maze_in_docker(mg.get_params_from_string(" ".join(params)), 'gen').wait()
    return docker.copy_docker_results('gen','gen',out_dir)