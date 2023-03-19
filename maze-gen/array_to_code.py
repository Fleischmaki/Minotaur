import sys, os
import random
import importlib
import genutils
from collections import defaultdict

UNIT_MATRIX = [['1','0','1'],['1','0','1'],['1','0','1']]

def get_maze(maze_file, width, height):
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

def get_solution(sol_file, offset):
    with open(sol_file + "_solution.txt", 'r') as f_sln:
        sln = f_sln.readlines()
    for i in range(len(sln)):
        sln[i] = int(sln[i].strip("\n"))
    return list(map(lambda x: x + offset, sln))

def get_exit(sln):
    return sln[len(sln) - 1]

def get_functions(width, height, maze_exit, offset):
    xy_to_func = dict()
    for i in range(width*height):
        xy_to_func[(i // width, i % width)] = i + offset
    xy_to_func[(-1, 0)] = 'start'
    if maze_exit == width*height - 1 + offset:
        xy_to_func[(height, width-1)] = 'bug'
    return xy_to_func

# Label each node by depth first search
class DirGraph:
    def __init__(self):
        self.graph = defaultdict(list)

    def add_edge(self, node, neighbour):
        self.graph[node].append(neighbour)

    def remove_edge(self, node, neighbour):
        self.graph[node].remove(neighbour)

    def count_edges(self):
        count = 0
        for idx in self.graph.keys():
            count = count + len(self.graph[idx])
        return count

    def count_backedges(self, labels):
        count = 0
        for idx in self.graph.keys():
            for neighbour in self.graph[idx]:
                if labels[idx] >= labels[neighbour]:
                    count = count + 1
        return count

    def remove_backedges(self, labels, n):
        while n > 0:
            idx = random.choice(list(self.graph.keys()))
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

    def disjoint_union(self, graph):
        self.graph = {**self.graph, **graph.graph}

class MazeGraph(DirGraph):
    def __init__(self,width, height, maze_exit, maze_functions, matrix):
        super().__init__()

        self.start_neigh = maze_functions[0,0]
        self.bug_neigh = maze_functions[height-1,width-1]

        self.graph['start'] = [self.start_neigh]
        self.graph['bug'] = []


        for idx in range(width*height):
            x, y = idx // width, idx % width
            node = maze_functions[(x, y)]
            if node == maze_exit and not (x == height - 1 and y == width - 1):
                self.add_edge(node, 'bug')
                self.bug_neigh = node                
            i, j = 2*x + 1, 2*y + 1
            if matrix[i-1][j] == '0':
                self.add_edge(node, maze_functions[(x-1, y)])
            if matrix[i][j-1] == '0':
                self.add_edge(node, maze_functions[(x, y-1)])
            if matrix[i+1][j] == '0':
                self.add_edge(node, maze_functions[(x+1, y)])
            if matrix[i][j+1] == '0':
                self.add_edge(node, maze_functions[(x, y+1)])

    def remove_cycle(self, cycle):
        graph_labels = self.df_search('start')
        numb_backedges = self.count_backedges(graph_labels)
        proportion_rm = float(1 - (cycle/100))
        numb_to_remove = int(numb_backedges*proportion_rm)
        self.remove_backedges(graph_labels, numb_to_remove)

    def append(self, maze):
        self.disjoint_union(maze)
        self.graph['start'] = [self.start_neigh] # Overwrite this as not disjoint
        self.remove_edge(self.bug_neigh,'bug')
        self.remove_edge(maze.start_neigh,'start')
        self.add_edge(self.bug_neigh, maze.start_neigh)
        self.add_edge(maze.start_neigh, self.bug_neigh)
        self.bug_neigh = maze.bug_neigh

def get_bug(bugtype):
    if bugtype == "abort":
        return "abort();", ""
    elif bugtype == "assert":
        return "assert(0);", "#include <assert.h>\n"
    elif bugtype == "ve":
        return "__VERIFIER_error();", "extern void __VERIFIER_error(void);\n"

def render_program(c_file, graph, size, generator, sln, bugtype, smt_file, transformations):
    f = open(c_file, 'w')
    generator = generator.Generator(size, graph, sln, smt_file, transformations)     
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
    f.write("""#define ARRAY_SIZE {}\n\n""".format(255))
    function_format_declaration = """void func_{}(char *input, int index, int length);\n"""
    function_declarations = ""
    for k in range(size):
        function_declarations += function_format_declaration.format(k)
    f.write(function_declarations)
    f.write("""void func_start(char *input, int index, int length){{ func_0(input,index,length); }}\n""")
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

    for idx in range(size):
        f.write(function_begin_format.format(idx, numb_bytes[idx], logic_c[idx]))
        valid_edges = len(graph[idx])
        if valid_edges == 0:
            f.write(function_deadend)
            continue
        else:
            edge_counter = 0
            for neighbour in graph[idx]:
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
    func_start(input, index, MAX_LIMIT);\n}}\n""")
    f.close()

def generate_maze(t_index, size, maze, unit):
    maze_file = maze["sol_file"] + "_t" + str(t_index)
    if unit:
        matrix = UNIT_MATRIX
        sln = [0 + size]
    else:
        matrix = get_maze(maze_file, maze["width"], maze["height"])
        sln = get_solution(maze["sol_file"],size)

    maze_exit = get_exit(sln)
    maze_funcs = get_functions(maze["width"], maze["height"], maze_exit,size)
    graph = MazeGraph(maze["width"], maze["height"], maze_exit, maze_funcs, matrix)
    return sln,graph

def generate_maze_chain(mazes, cycle, t_index, unit):
    size = 0
    graph = None
    solution = []
    for maze in mazes:
        sln, new_graph = generate_maze(t_index, size, maze, unit)
        solution += sln
        size += maze["width"] * maze["height"]
        if graph is None:
            graph = new_graph
        else:
            graph.append(new_graph)
    graph.remove_cycle(cycle)
    return size,graph,solution

def main(mazes, seed, generator, bugtype, t_type, t_numb, output_dir, cycle, unit, smt_file, CVE_name):
    random.seed(seed)
    transformations = genutils.parse_transformations(t_type)
    if transformations["storm"]:
        smt_files = [smt_file] + genutils.run_storm(smt_file, os.path.join(output_dir,'smt'), seed, t_numb)
    else:
        smt_files = [smt_file]*(t_numb+1)
    for t_index in range(t_numb+1):
        size, graph, solution = generate_maze_chain(mazes, cycle, t_index, unit)
        c_file = mazes[0]["sol_file"] + "_t" + str(t_index) + "_" + str(cycle) + "percent_" + CVE_name + "_" + bugtype + ".c"
        if t_index != 0:
            render_program(c_file, graph.graph, size, generator, solution, bugtype, smt_files[t_index], transformations)
        elif transformations["keepId"]:
            render_program(c_file, graph.graph, size, generator, solution, bugtype, smt_files[t_index],genutils.parse_transformations(""))

if __name__ == '__main__':
    seed = int(sys.argv[1])
    bugtype = sys.argv[2]
    t_type = sys.argv[3]
    t_numb = int(sys.argv[4])
    output_dir = sys.argv[5]
    cycle = int(sys.argv[6])
    unit = int(sys.argv[7])
    generator_file = sys.argv[8]
    generator = importlib.import_module(generator_file)
    if "CVE" in generator_file:
        smt_file = sys.argv[9]
        CVE_name = os.path.basename(smt_file)
        CVE_name = os.path.splitext(CVE_name)[0] + "_gen"
        i = 9
    else:
        smt_file = ""
        CVE_name = generator_file
        i = 8
    mazes = []
    while (i+3 < len(sys.argv)):
        maze = dict()
        maze["sol_file"] = sys.argv[i+1]
        maze["width"], maze["height"] = int(sys.argv[i+2]), int(sys.argv[i+3])
        mazes.append(maze)
        i += 3
    main(mazes, seed, generator, bugtype, t_type, t_numb, output_dir, cycle, unit, smt_file, CVE_name)
