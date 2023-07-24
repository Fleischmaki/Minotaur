from ..runner import maze_gen as mg

def load(argv):
    out_dir = argv[0]
    params = argv[1:]
    return mg.generate_maze(mg.get_params_from_string(" ".join(params)), out_dir)