import sys, os
import random
import importlib
import genutils
from collections import defaultdict

def get_maze(maze_file):
    f = open(maze_file + ".txt", "r+")
    txt = f.read().replace(' ', '').replace('[', '').replace(']', '')
    f.seek(0)
    f.write(txt)
    f.truncate()
    f.seek(0)
    matrix = []
    for i in range(height*2+1):
        row = []
        for j in range(width*2+2):
            c = f.read(1)
            if (c == '1' or c == '0'):
                row.append(c)
        matrix.append(row)
    f.close()
    return matrix

def get_solution(sol_file):
    with open(sol_file + "_solution.txt", 'r') as f_sln:
        sln = f_sln.readlines()
    for i in range(len(sln)):
        sln[i] = int(sln[i].strip("\n"))
    return sln

def get_exit(sln):
    return sln[len(sln) - 1]

def get_functions(width, height, maze_exit):
    xy_to_func = dict()
    functions = list(range(width*height))
    for i in range(width*height):
        xy_to_func[(i // width, i % width)] = functions[i]
    xy_to_func[(-1, 0)] = 'start'
    if maze_exit == width*height - 1:
        xy_to_func[(height, width-1)] = 'bug'
    return xy_to_func

# Label each node by depth first search
class DirGraph:
    def __init__(self):
        self.graph = defaultdict(list)

    def add_edge(self, node, neighbour):
        self.graph[node].append(neighbour)

    def count_edges(self):
        count = 0
        for idx in range(width*height):
            count = count + len(self.graph[idx])
        return count

    def count_backedges(self, labels):
        count = 0
        for idx in range(width*height):
            for neighbour in self.graph[idx]:
                if labels[idx] >= labels[neighbour]:
                    count = count + 1
        return count

    def remove_backedges(self, labels, n):
        while n > 0:
            idx = random.randrange(0, width*height)
            for neighbour in self.graph[idx]:
                if labels[idx] >= labels[neighbour]:
                    self.graph[idx].remove(neighbour)
                    n = n -1

    def df_search_helper(self, node, visited, labels):
        visited.add(node)
        labels[node] = len(visited)
        for neighbour in self.graph[node]:
            if neighbour not in visited:
                self.df_search_helper(neighbour, visited, labels)
        return labels

    def df_search(self, node):
        visited = set()
        labels = dict()
        return self.df_search_helper(node, visited, labels)

def generate_graph(width, height, maze_exit, maze_functions, matrix):
    graph = DirGraph()
    functions = list(range(width*height))
    for idx in range(width*height):
        x, y = functions[idx] // width, functions[idx] % width
        node = maze_functions[(x, y)]
        if node == maze_exit and node != width*height - 1:
            graph.add_edge(node, 'bug')
        i, j = 2*x + 1, 2*y + 1
        if matrix[i-1][j] == '0':
            graph.add_edge(node, maze_functions[(x-1, y)])
        if matrix[i][j-1] == '0':
            graph.add_edge(node, maze_functions[(x, y-1)])
        if matrix[i+1][j] == '0':
            graph.add_edge(node, maze_functions[(x+1, y)])
        if matrix[i][j+1] == '0':
            graph.add_edge(node, maze_functions[(x, y+1)])
    return graph

def remove_cycle(graph, cycle):
    graph_labels = graph.df_search(0)
    numb_backedges = graph.count_backedges(graph_labels)
    proportion_rm = float(1 - (cycle/100))
    numb_to_remove = int(numb_backedges*proportion_rm)
    graph.remove_backedges(graph_labels, numb_to_remove)

def get_bug(bugtype):
    if bugtype == "abort":
        return "abort();", ""
    elif bugtype == "assert":
        return "assert(0);", "#include <assert.h>\n"
    elif bugtype == "ve":
        return "__VERIFIER_error();", "extern void __VERIFIER_error(void);\n"

def render_program(c_file, maze, maze_funcs, width, height, generator, sln, bugtype, smt_file, transformations):
    f = open(c_file, 'w')
    generator = generator.Generator(width*height, maze.graph, sln, smt_file, transformations)     
    logic_def = generator.get_logic_def()
    logic_c = generator.get_logic_c()
    numb_bytes = generator.get_numb_bytes()
    total_bytes = generator.get_total_bytes()
    guard = generator.get_guard()
    bug, bug_headers = get_bug(bugtype)

    f.write("#include <stdio.h>\n" \
    "#include <stdlib.h>\n" \
    "#include <string.h>\n" \
    "#include <unistd.h>\n" \
    "#include <stdint.h>\n")
    f.write(bug_headers)
    f.write("extern char __VERIFIER_nondet_char(void);\n")
    f.write("""#define MAX_LIMIT {}\n\n""".format(total_bytes))
    function_format_declaration = """void func_{}(char *input, int index, int length);\n"""
    function_declarations = ""
    for k in range(width*height):
        function_declarations += function_format_declaration.format(k)
    f.write(function_declarations)
    f.write("""void func_start(char *input, int index, int length){}\n""")
    f.write("""void func_bug(char *input, int index, int length){{ {} }}\n""".format(bug))
    f.write(logic_def)
    f.write("""char* copy_input(char *input, int index, int bytes_to_use){
    char copy[bytes_to_use];
    for(int i = 0; i < bytes_to_use; i++){
        \tcopy[i] = __VERIFIER_nondet_char();
    }
    return (char*)copy;\n}\n""")
    f.write("""int is_within_limit(char *input, int index, int bytes_to_use, int length){
    if (index + (bytes_to_use - 1) >= MAX_LIMIT || index + (bytes_to_use - 1) >= length){
    \treturn 0;
    } else {
    \treturn 1;
    }\n}\n""")

    function_begin_format = """void func_{}(char *input, int index, int length){{
    int bytes_to_use = {};
    if (is_within_limit(input, index, bytes_to_use, length)){{
    \tchar *copy;
    \tcopy = copy_input(input, index, bytes_to_use);\n {}
    \tcopy = NULL;
    """
    function_format = """\t{} ({}) {{
    \t\tfunc_{}(input, index + bytes_to_use, length);
    \t}}
    """
    function_end = """\telse {
    \t\tprintf("User-provided conditions were not satisfied by the input");
    \t}
    }\n}\n"""
    function_deadend = """}\n}\n"""

    for idx in range(width*height):
        f.write(function_begin_format.format(idx, numb_bytes[idx], logic_c[idx]))
        valid_edges = len(maze.graph[idx])
        if valid_edges == 0:
            f.write(function_deadend)
            continue
        else:
            edge_counter = 0
            for neighbour in maze.graph[idx]:
                if edge_counter == 0:
                    f.write(function_format.format(
                        'if', guard[idx][edge_counter], neighbour))
                else:
                    f.write(function_format.format(
                        'else if', guard[idx][edge_counter], neighbour))
                edge_counter += 1
        f.write(function_end)

    f.write("""int main(){{
    char input[MAX_LIMIT];
    int index = 0;
    func_{}(input, index, MAX_LIMIT);\n}}\n""".format(maze_funcs[(0, 0)]))
    f.close()

def main(sol_file, width, height, cycle, seed, generator, bugtype, t_type, t_numb, output_dir, smt_file, CVE_name):
    random.seed(seed)
    transformations = genutils.parse_transformations(t_type)
    if transformations["storm"]:
        smt_files = [smt_file] + genutils.run_storm(smt_file, output_dir, seed, t_numb)
    else:
        smt_files = [smt_file]*(t_numb+1)
    print(smt_files)
    for t_index in range(t_numb+1):
        maze_file = sol_file + "_" + str(t_index)
        matrix = get_maze(maze_file)
        sln = get_solution(sol_file)
        maze_exit = get_exit(sln)
        maze_funcs = get_functions(width, height, maze_exit)
        graph = generate_graph(width, height, maze_exit, maze_funcs, matrix)
        remove_cycle(graph, cycle)
        c_file = maze_file + "_" + str(cycle) + "percent_" + CVE_name + "_" + bugtype + ".c"
        if t_index != 0:
            render_program(c_file, graph, maze_funcs, width, height, generator, sln, bugtype, smt_files[t_index], transformations)
        else:
            render_program(c_file, graph, maze_funcs, width, height, generator, sln, bugtype, smt_files[t_index],genutils.parse_transformations(""))

if __name__ == '__main__':
    sol_file = sys.argv[1]
    width, height = int(sys.argv[2]), int(sys.argv[3])
    cycle = int(sys.argv[4])
    seed = int(sys.argv[5])
    bugtype = sys.argv[6]
    t_type = sys.argv[7]
    t_numb = int(sys.argv[8])
    output_dir = sys.argv[9]
    generator_file = sys.argv[10]
    generator = importlib.import_module(generator_file)
    if "CVE" in generator_file:
        smt_file = sys.argv[11]
        CVE_name = os.path.basename(smt_file)
        CVE_name = os.path.splitext(CVE_name)[0] + "_gen"
    else:
        smt_file = ""
        CVE_name = generator_file
    main(sol_file, width, height, cycle, seed, generator, bugtype, t_type, t_numb, output_dir, smt_file, CVE_name)
