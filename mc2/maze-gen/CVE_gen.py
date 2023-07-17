import smt2_parser
import random
import transforms

class Generator:
    def __init__(self, size, edges, sln, smt_file, transformations):
        self.size = size
        self.edges = edges
        self.sln = sln
        try:
            self.array_size = smt2_parser.get_minimum_array_size(smt_file)
        except ValueError as e:
            print(e)
            self.array_size = -1 # This should make model checkers throw an error 
        self.constraints, self.vars_all = smt2_parser.parse(smt_file, check_neg = False)
        transforms.remove_constraints(self.constraints, transformations['dc'])
        self.groups, self.vars = smt2_parser.independent_formulas(self.constraints, self.vars_all)
        if transformations['sh']:
            self.groups, self.vars = transforms.coshuffle(self.groups, self.vars)
        self.insert = list()
        for _ in range(self.size):
            self.insert.append(0)
        while sum(self.insert) < len(self.groups):
            for func in self.sln:
                self.insert[func] += 1
                if sum(self.insert) >= len(self.groups):
                    break
        if transformations['sh']:
            random.shuffle(self.insert)
            
    def get_logic_def(self):
        logic_def = "char read_input(char *input, int index){ return input[index]; }\n"
        if self.array_size > 0:
            logic_def += "#define ARRAY_SIZE %d\n" % self.array_size
            logic_def += """int* array_store(int* a,int p,int v){
    a[p] = v;
    return a;\n}\n"""
            logic_def += ("""int array_comp(int* a1, int* a2){
    for(int i = 0; i < ARRAY_SIZE; i++){
    \tif(a1[i] != a2[i]) return 0;
    }
    return 1;\n}\n""")

        return logic_def

    def get_logic_c(self):
        logic_c = list()
        group_idx = 0
        for idx in range(self.size):
            if self.insert[idx] == 0:
                logic_c.append("\t\tchar c = read_input(copy, 0);")
            else:
                copy_idx, tab_cnt = 0, 0
                constraints, vars = set(), set()
                for cnt in range(self.insert[idx]):
                    constraints = constraints.union(self.groups[group_idx + cnt])
                    vars = vars.union(self.vars[group_idx + cnt])
                buggy_constraints = ""
                for var in vars:
                    if '[' in var: #Arrays
                        buggy_constraints += "\t\tunsigned {} {};\n".format(self.vars_all[var],var)
                    else:
                        buggy_constraints += "\t\tunsigned{} {} = read_input(copy, {});\n".format(self.vars_all[var], var, copy_idx)
                        copy_idx += 1
                    
                buggy_constraints += "\t\tchar c = read_input(copy, {});\n".format(len(vars))
                buggy_constraints += "\t\tint flag = 0;\n"
                for constraint in constraints:
                    buggy_constraints += "\t"*tab_cnt + "\t\tif{}{{\n".format(constraint)
                    tab_cnt += 1
                buggy_constraints += "\t"*tab_cnt + "\t\tflag = 1;\n"
                for k in range(len(constraints)-1, -1, -1):
                    buggy_constraints += "\t"*k + "\t\t}\n"
                logic_c.append(buggy_constraints)
                group_idx += self.insert[idx]
        return logic_c

    def get_numb_bytes(self):
        numb_bytes = list()
        group_idx = 0
        for idx in range(self.size):
            if self.insert[idx] == 0:
                numb_bytes.append(1)
            else:
                used_bytes = 0
                for cnt in range(self.insert[idx]):
                    used_bytes += len(self.vars[group_idx + cnt])
                numb_bytes.append(used_bytes + 1)
                group_idx += self.insert[idx]
        return numb_bytes

    def get_guard(self):
        guard = list()
        group_idx = 0
        for idx in range(self.size):
            conds_default = [["0"], ["1"],
            ["c < 0", "c >= 0"],
            ["c < -43", "c < 42", "c >= 42"],
            ["c < -64", "c < 0", "c < 64", "c >= 64"]]
            numb_edges = len(self.edges[idx])
            if self.insert[idx] == 0:
                guard.append(conds_default[numb_edges])
            else:
                next, bug_edge, m = 0, 0, 0
                conds = []
                for i in range(len(self.sln)):
                    if self.sln[i] == idx:
                        if i == len(self.sln) - 1:
                            next = 'bug'
                        else:
                            next = self.sln[i+1]
                for n in range(numb_edges):
                    if self.edges[idx][n] == next:
                        bug_edge = n
                for n in range(numb_edges):
                    if n == bug_edge:
                        conds.append("flag == 1")
                    else:
                        conds.append(conds_default[numb_edges-1][m] + " && flag == 0")
                        m += 1
                group_idx += 1
                guard.append(conds)
        return guard

    def get_total_bytes(self):
        return sum(self.get_numb_bytes())