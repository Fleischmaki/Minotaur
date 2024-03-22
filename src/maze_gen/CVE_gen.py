from smt2 import parser, converter
import transforms
import random


class Generator:
    def __init__(self, size, edges, sln, smt_file, transformations):
        self.size = size
        self.edges = edges
        self.sln = sln
        self.transformations = transformations
        self.logic = parser.read_file(smt_file).logic

        try:
            self.constraints, self.vars_all, self.array_size = parser.parse(smt_file, check_neg = False, generate_well_defined=transformations['wd'], generate_sat=transformations['sat'],limit=transformations['dag'])
        except ValueError as e:
            print('Error while parsing smt file %s' % str(e))
            self.constraints = {} if transformations['sat'] else '(1==0)'
            self.vars_all = {}
            self.array_size = 0


        transforms.remove_constraints(self.constraints, transformations['dc'])
        transforms.make_const(self.vars_all, transformations['mc'])

        self.groups, self.vars = parser.independent_formulas(self.constraints, self.vars_all)

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
        logic_def = ""
        if 'BV' in self.logic:
            logic_def += ("\n\n//Helper functions for division and casts\n")
            logic_def += ("""long scast_helper(unsigned long i, unsigned char width){
    if((i & (1ULL << (width-1))) > 0){
        return (long) (i - (1ULL<< width));
    }
    return i;
}\n""")
            if self.transformations['wd']:
                logic_def += ("""unsigned long sdiv_helper(long l, long r, int width){
    if(r == 0){
        if(l >= 0)
            return -1ULL >> (64-width); // Make sure we shift with 0s
        return 1;
    } else if ((r == -1) && (l == ((-0x7FFFFFFFFFFFFFFFLL-1) >> (64-width))))
        return 0x8000000000000000ULL;
    return l / r;
}
unsigned long div_helper(unsigned long l, unsigned long r, int width){
    if(r == 0)
        return -1ULL >> (64-width);
    return l / r;
}
unsigned long srem_helper(long l, long r, int width){
    if(r == 0)
        return l;
    return l % r;
}
unsigned long rem_helper(unsigned long l, unsigned long r, int width){
    if(r == 0)
        return l;
    return l % r;
}\n""")
        if 'A' in self.logic:
            logic_def += "\n\n//Array support\n"
            logic_def += "#define ARRAY_SIZE %d\n" % self.array_size
            logic_def += """long* value_store(long* a,long pos,long v){
    a[pos] = v;
    return a;\n}\n"""
            logic_def += """long* array_store(long* a,long pos,long* v, int size){
    for (int i=0;i<size;i++){
        a[pos*size+i] = v[i];
    }
    return a;\n}\n"""
            logic_def += ("""int array_comp(long* a1, long* a2, int size){
    for(int i = 0; i < size; i++){
    \tif(a1[i] != a2[i]) return 0;
    }
    return 1;\n}\n""")
            logic_def += ("""void init(long* array,int size){
    for(int i = 0; i < size; i++){
    \tarray[i] = __VERIFIER_nondet_long();
    }\n}""")
        return logic_def

    def get_logic_c(self):
        logic_c = list()
        group_idx = 0
        for idx in range(self.size):
            if self.insert[idx] == 0 and len(self.edges[idx]) > 1:
                logic_c.append("\t\tsigned char c = __VERIFIER_nondet_char();")
            else:
                tab_cnt = 0
                constraints, vars = list(), set()
                for cnt in range(self.insert[idx]):
                    constraints.extend(self.groups[group_idx + cnt])
                    vars = vars.union(self.vars[group_idx + cnt])
                buggy_constraints = ""  
                for var in vars:
                    buggy_constraints += self.get_initialisation(var)
                    

                if len(self.edges[idx]) > 1:
                    buggy_constraints += "\tchar c = __VERIFIER_nondet_char();\n"
                buggy_constraints += "\tint flag = 0;\n"
                for constraint in constraints:
                    buggy_constraints += "\t"*tab_cnt + "\tif{}{{\n".format(constraint)
                    tab_cnt += 1
                buggy_constraints += "\t"*tab_cnt + "\tflag = 1;\n"
                for k in range(len(constraints)-1, -1, -1):
                    buggy_constraints += "\t"*k + "\t}\n"
                logic_c.append(buggy_constraints)
                group_idx += self.insert[idx]
        return logic_c

    def get_initialisation(self, var):
        if '[' in var: #Arrays
            dim = var.count('[')
            return "\t{} {};\n\tinit({}{},{});\n".format(self.vars_all[var],var,'*'*(dim-1),var.split('[')[0],converter.get_array_size_from_dim(dim))
        elif self.vars_all[var] == 'bool':
            return "\t_Bool {} = __VERIFIER_nondet_bool();\n".format(var)
        elif self.vars_all[var] == 'const bool':
            return "\t const _Bool {} = __VERIFIER_nondet_bool();\n".format(var)
        else:
            orig_type = self.vars_all[var]
            short_type = orig_type.split(" ")[-1]
            if 'unsigned' in orig_type:
                short_type = 'u' + short_type
            return "\t{} {} = __VERIFIER_nondet_{}();\n".format(self.vars_all[var], var, short_type)

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