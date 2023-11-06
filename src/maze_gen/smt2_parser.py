import re
import sys, random, os
from pysmt.smtlib.parser import SmtLibParser
from collections import defaultdict
from pysmt.shortcuts import *
from io import StringIO

def deflatten(args, op):
    x = args[0]
    for i in range(1,len(args)):
        y = args[i]
        x = op(x,y)
    return x

def error(flag, *nodes):
    if flag == 0:
        raise ValueError("ERROR: node type not recognized: ", nodes, map(lambda n: n.get_type()))
    elif flag == 1:
        raise ValueError("ERROR: nodes not supported", nodes)
    else:
        raise ValueError("ERROR: an unknown error occurred")

def binary_to_decimal(binary, unsigned = True):
    if len(binary) > 64:
        error(1, binary)
    val = str(BV(binary).constant_value() if unsigned else BV(binary).bv_signed_value())
    if len(binary) > 32:
        val += 'ULL' if unsigned else 'LL'
    return val 

def bits_to_type(n):
    if n <= 8:
        return "char"
    elif n <= 16:
        return "short"
    elif n <= 32:
        return "int"
    elif n <= 64:
        return "long"
    else:
        error(1, n)
        
def bits_to_utype(n):
    return "unsigned " + bits_to_type(n)

def signed(node,n_string):
    width = get_bv_width(node)
    cast = bits_to_type(width)  
    if width == 64:
        return '(%s) %s' % (cast, n_string)  
    return ('(%s) scast_helper(%s,%s)' % (cast,n_string,width))

def unsigned(node,n_string):
    return ('%s %s' % (get_unsigned_cast(node), n_string))

def get_unsigned_cast(node):
    width = get_bv_width(node)
    return '(' + bits_to_utype(width) + ') '

def get_bv_width(node):
    res = 0
    if node.is_bv_constant() or node.is_symbol or node.is_function_application() or node.is_ite() or node.is_select():
        res = node.bv_width()
    elif len(node.args()) == 1:
        (r,) = node.args()
        width = get_bv_width(r)
        if(node.is_bv_sext() or node.is_bv_zext()):
            res = width + node.bv_extend_step()
        else:
            res = r.bv_width()  
    elif len(node.args()) == 2:
        (l,r) = node.args() 
        if node.is_bv_concat():
            res = get_bv_width(l) + get_bv_width(r)
        if l.is_bv_constant() or l.is_symbol or l.is_function_application() or l.is_ite() or l.is_select():
            res =  l.bv_width()
        elif r.is_bv_constant() or r.is_symbol or r.is_function_application() or r.is_ite() or r.is_select():
            res = r.bv_width()
    else:
        error(1,node)
    
    if res == 0 or res > 64:
        error(1,node)
    return res

def type_to_c(type):
    if type.is_bool_type():
        return 'bool'
    elif type.is_bv_type():
        return bits_to_utype(type.width)
    elif type.is_function_type():
        return type_to_c(type.return_type)
    elif type.is_array_type():
        return 'long' # otherwise store might be unsound, we can always cast afterwards
    # elif type.is_string_type():
    #     return 'string'
    else:
        error(0, type)

def convert_helper(symbs,node, cons, op, cast_sign = '', cast_args = True):
    (l, r) = node.args()
    l_string = convert_to_string(symbs,l)
    r_string = convert_to_string(symbs,r)

    if cast_sign == '':
        cons.write(l_string)
        cons.write(op)
        cons.write(r_string)
    elif cast_args:
        l_cast = unsigned(l,l_string) if cast_sign == 'u' else signed(l,l_string)
        r_cast = unsigned(r,r_string) if cast_sign == 'u' else signed(r,r_string)
        cons.write(l_cast)
        cons.write(op)
        cons.write(r_cast)
    else:
        n_string = l_string + op + r_string
        cons.write(unsigned(node,n_string) if cast_sign == 'u' else signed(node,n_string))


def check_shift_size(node):
    (l,r) = node.args()
    if not r.is_bv_constant() or r.constant_value() > get_bv_width(node):
        error(1, node)

def div_helper(symbs,node,cons):
    (l,r) = node.args()
    width = get_bv_width(node)

    lString = convert_to_string(symbs, l)
    rString = convert_to_string(symbs, r)
    
    if node.is_bv_urem() or node.is_bv_srem():
        if node.is_bv_srem():
            cons.write(signed(node))
        cons.write("rem_helper(%s,%s,%s)" % (lString,rString,width))
    elif node.is_bv_udiv():
        cons.write("div_helper(%s,%s,%s)" % (lString,rString,width))
    else:
        cons.write("sdiv_helper(%s,%s,%s)" % (lString,rString,width))
        
def convert_to_string(symbs, node):
    buff = StringIO()
    convert(symbs, node, buff)
    lString = buff.getvalue()
    buff.close()
    return lString

def convert(symbs,node, cons):
    #if cons.tell() > 2**20:
    #    raise ValueError("Parse result too large") # Avoid file sizes > 1 MB
    cons.write('(')
    if node.is_iff() or node.is_equals() or node.is_bv_comp():
        (l, r) = node.args()
        if "Array" in str(l.get_type()):
            if "Array" in str(r.get_type()):
                cons.write("array_comp(")
                convert(symbs,l,cons)
                cons.write(",")
                convert(symbs,r,cons)
                cons.write("))")
                return
            error(1, node)
        convert_helper(symbs,node, cons, " == ")

    elif node.is_bv_sle():
        convert_helper(symbs,node, cons, " <= ", 's')
    elif node.is_bv_ule():
        convert_helper(symbs,node, cons, " <= ", 'u')
    elif node.is_bv_slt():
        convert_helper(symbs,node, cons, " < ", 's')
    elif node.is_bv_ult():
        convert_helper(symbs,node, cons, " < ", 'u')
    elif node.is_bv_lshr():
        check_shift_size(node)
        convert_helper(symbs,node, cons, " >> ", 'u') # C >> is logical for unsigned, arithmetic for signed
    elif node.is_bv_ashr():
        check_shift_size(node)
        convert_helper(symbs,node, cons, " >> ", 's')
    elif node.is_bv_add():
        convert_helper(symbs,node, cons, " + ", 'u', False) # Recast result on all operations that can exceed value ranges
    elif node.is_bv_sub():
        convert_helper(symbs,node, cons, " - ")
    elif node.is_bv_mul():
        convert_helper(symbs,node, cons, " * ", 'u', False)# Recast result on all operations that can exceed value ranges
    elif node.is_bv_udiv() or node.is_bv_sdiv() or node.is_bv_urem() or node.is_bv_srem():
        div_helper(symbs,node, cons)
    elif node.is_bv_xor():
        convert_helper(symbs,node, cons, " ^ ")
    elif node.is_bv_or():
        convert_helper(symbs,node, cons, " | ")
    elif node.is_bv_and():
        convert_helper(symbs,node, cons, " & ")
    elif node.is_bv_lshl():
        check_shift_size(node)
        convert_helper(symbs,node, cons, " << ", 'u', False)
    elif node.is_bv_not():
        (b,) = node.args()
        cast = get_unsigned_cast(node)
        cons.write(cast)
        cons.write("(~")
        convert(symbs,b, cons)
        cons.write(")")
    elif node.is_bv_sext():
        extend_step = node.bv_extend_step()
        (l,) = node.args()
        width = get_bv_width(l)
        newtype=bits_to_type(extend_step+width)
        res = convert_to_string(symbs,l)
        cons.write('((%s & %s) > 0 ? ((%s)%s - %s) : (%s)%s)' % (binary_to_decimal("1" + "0"*(width-1)),res,newtype,res,binary_to_decimal("1"+"0"*width),newtype,res))
    elif node.is_bv_zext():
        (l,) = node.args()
        get_unsigned_cast(node)
        convert(symbs,l, cons)
    elif node.is_bv_concat():
        (l,r) = node.args()
        cast = get_unsigned_cast(node)
        cons.write('(')
        cons.write(cast)
        convert(symbs,l, cons)
        cons.write(')')
        cons.write(' << %d | ' % get_bv_width(r))
        cons.write('(')
        cons.write(cast)
        convert(symbs,r,cons)
        cons.write(')')
    elif node.is_bv_extract():
        ext_start = node.bv_extract_start()
        ext_end = node.bv_extract_end()
        dif = ext_end - ext_start + 1
        (l,) = node.args()
        m = get_bv_width(l)
        mask = binary_to_decimal("1" * (dif))
        newtype = bits_to_utype(dif) 
        cons.write("(" + newtype +") (")
        convert(symbs,l, cons)
        cons.write(" >> " + str(ext_start))
        if ext_end != m:
            cons.write(" & " + mask)
        cons.write(")")
    elif node.is_and():
        node = deflatten(node.args(),And)
        convert_helper(symbs,node, cons, " && ")
    elif node.is_or():
        node = deflatten(node.args(),Or)
        convert_helper(symbs,node, cons, " || ")
    elif node.is_not():
        (b,) = node.args()
        cons.write("!")
        convert(symbs,b, cons)
    elif node.is_implies():
        (l,r) = node.args()
        cons.write("!")
        convert(symbs,l,cons)
        cons.write(" | ")
        convert(symbs,r,cons)
    elif node.is_ite():
        (g,p,n) = node.args()
        convert(symbs,g,cons)
        cons.write(' ? ')
        convert(symbs,p, cons)
        cons.write(' : ')
        convert(symbs,n, cons)
    elif node.is_bv_neg():
        (s,) = node.args()
        cast = get_unsigned_cast(node)
        base = binary_to_decimal("1" + "0" * (get_bv_width(s)))
        cons.write(cast + base + ' - ' + cast)
        convert(symbs,s,cons)
    elif node.is_bv_rol():
        rotate_helper(symbs, node, cons, "<<")
    elif node.is_bv_ror():
        rotate_helper(symbs, node, cons, ">>")
    elif node.is_bv_constant():
        value =  "(" + bits_to_utype(node.bv_width()) + ") " + str(node.constant_value())
        if node.bv_width() > 32:
            value += "ULL"
        cons.write(value)
    elif node.is_bool_constant():
        value =  "1" if node.is_bool_constant(True) else "0"
        cons.write(value)
    elif node.is_symbol():
        if str(node) == 'c':
            node = '__original_smt_name_was_c__'
        node = clean_string(node)
        cons.write(node)
        symbs.add(node)
    elif node.is_select():
        (a, p) = node.args()
        cast = get_unsigned_cast(node)
        cons.write(cast)
        convert(symbs, a, cons)
        cons.write("[")
        convert(symbs,p,cons)
        cons.write("]")
    elif node.is_store():
        (a, p, v) = node.args()
        cons.write("array_store(")
        convert(symbs, a, cons)
        cons.write(",")
        convert(symbs,p,cons)
        cons.write(",")
        convert(symbs,v,cons)
        cons.write(")")
    elif node.is_function_application():
        for n in node.args():
            if not n.is_bv_constant():
                error(1, node)
        index = "".join(["_" + str(n.constant_value()) for n in node.args()])
        fn = clean_string(node.function_name())
        cons.write(fn + index)
        symbs.add(fn + index)
    else:
        error(0, node)
        return("")
    cons.write(')')
    return ""

def rotate_helper(symbs, node, cons, op):
    (l,) = node.args()
    m = get_bv_width(node)
    i = node.bv_rotation_step()
    convert(symbs,l,cons)
    cons.write('((')
    convert(symbs,l,cons)
    cons.write(' %s %s) & ((1 %s %s+1) - 1)) | (' % (op, i, op, i)) # TODO exponential blowup possible
    convert(symbs,l,cons)
    cons.write(' %s (%s-%s) )' % (op, i, m))

def is_neg_sat(c, clauses):
    form_neg = Not(c)
    for n in clauses:
        if n is not c:
            form_neg = form_neg.And(n)
    sat = is_sat(form_neg, solver_name = "z3")
    return sat

def conjunction_to_clauses(formula):
    if formula.is_and():
        clauses = set()
        for node in formula.args():
            clauses = clauses.union(conjunction_to_clauses(node))
    else:
        clauses = set([formula])
    return clauses

def clean_string(s):
    s = str(s)
    return re.sub('[^A-Za-z0-9_]+','',s)

def rename_arrays(formula):
    constraints = set()
    subs = dict()

    for sub in formula.args():
        new_formula, new_constraints = rename_arrays(sub)
        subs.update({sub: new_formula})
        constraints = constraints.union(new_constraints)

    if formula.is_store():
        old = formula.arg(0)
        if old.is_symbol():
            new = FreshSymbol(typename=old.get_type())
            constraints.add(Equals(old,new))
            subs.update({old : new})

    formula = formula.substitute(subs)
    return formula, constraints

def write_to_file(formula, file):
    if type(formula) == list:
        formula = And(*formula)
    return write_smtlib(formula, file)

def parse(file_path, check_neg):
    print("Converting %s: " % file_path)
    decl_arr, variables, parsed_cons, formula = read_file(file_path)
    clauses = conjunction_to_clauses(formula) 

    array_size, array_constraints = constrain_array_size(formula)

    c = 0
    for clause in clauses:
        c += 1
        print("%d/%d" % (c,len(clauses)))
        clause, constraints = rename_arrays(clause)
        if len(constraints) > 0:
            print("Added %d new arrays" % len(constraints))
        ldecl_arr = decl_arr
        ldecl_arr.extend(map(lambda c: c.args()[1],constraints))
        clause = And(*constraints, clause) # Make sure to render constraints first

        symbs = set()
        buffer = StringIO()
        try:
            convert(symbs,clause, buffer)
        except Exception as e:
           print("Could not convert clause: ", e)
           continue
        cons_in_c =  buffer.getvalue()
        if "model_version" not in cons_in_c:
            if check_neg == True:
                neg_sat = is_neg_sat(clause, clauses)
                parsed_cons[cons_in_c] = neg_sat
            else:
                parsed_cons[cons_in_c] = ""
            for symb in symbs:
                decls = list(map(lambda x: clean_string(x), ldecl_arr))
                if symb in decls:
                    decl = symb
                elif 'c' in decls and symb == '__original_smt_name_was_c__':
                    decls.remove('c')
                    decls.append(symb)
                    decl = symb
                else:
                    decl = symb.split("_")[0]
                i = decls.index(decl)
                vartype = ldecl_arr[i].get_type()
                type_in_c = type_to_c(vartype)
                if vartype.is_array_type():
                    symb += "[%d]" % array_size 
                variables[symb] = type_in_c
    return parsed_cons, variables

def read_file(file_path):
    parser = SmtLibParser()
    script = parser.get_script_fname(file_path)
    decl_arr = list()
    variables = dict()
    decls = script.filter_by_command_name("declare-fun")
    for d in decls:
        for arg in d.args:
            if (str)(arg) != "model_version":
                decl_arr.append(arg)
    parsed_cons = dict()
    formula = script.get_strict_formula()
    return decl_arr,variables,parsed_cons,formula

def check_indices(symbol,maxArity,maxId, cons_in_c):
    if maxArity == 0:
        return set([symbol]) if symbol in cons_in_c else set()
    for id in range(maxId):
        var = symbol + '_' + str(id)
        res = set([var]) if var in cons_in_c else set()
        res = res.union(check_indices(var, maxArity-1,maxId,cons_in_c))
    return res    

def extract_vars(cond, variables):    
    vars = dict()
    for var, type in variables.items():
        if var + " " in cond or var + ")" in cond or var.split('[')[0] in cond:
            vars[var] = type
    return vars

class Graph:
    def __init__(self):
        self.graph = defaultdict(list)

    def add_edge(self, node, neighbour):
        self.graph[node].append(neighbour)

    def get_edges(self, node):
        return self.graph[node]

    def separate_helper(self, node, visited):
        group = {node}
        current = {node}
        while len(current) != 0:
            new = set()
            for node in current:
                for neighbour in self.graph[node]:
                    if neighbour not in visited:
                        new.add(neighbour)
            visited.update(new)
            group.update(new)
            current = new
        return group


    def separate(self):
        visited = set()
        groups = list()
        for node in self.graph:
            if node not in visited:
                group = self.separate_helper(node, visited)
                groups.append(group)
        return groups

def independent_formulas(conds, variables):
    formula = Graph()
    for cond in conds:
        formula.add_edge(cond,cond)
        vars = extract_vars(cond, variables)
        for other in conds:
            if len(vars.keys() & extract_vars(other, variables).keys()) > 0:
                formula.add_edge(cond, other)
    groups = formula.separate()
    vars_by_groups = list()
    for group in groups:
        used_vars = dict()
        for cond in group:
            used_vars.update(extract_vars(cond, variables))
        vars_by_groups.append(sorted(used_vars))
    return groups, vars_by_groups

def get_negated(conds, group, vars, numb):
    negated_groups = list()
    new_vars = list()
    n = 0
    for cond in group:
        if conds[cond] == True:
            n = n + 1
    if n >= numb:
        negated = set()
        for i in range(numb):
            negated_group = set()
            for cond in group:
                if conds[cond] == True and len(negated) <= i and cond not in negated:
                        negated_group.add("(!" + cond + ")")
                        negated.add(cond)
                else:
                    negated_group.add(cond)
            negated_groups.append(negated_group)
    else:
        for i in range(numb):
            new_group = set()
            new_var = "c" + str(i)
            # negate one of the original and add same conds for new var
            for cond in group:
                if conds[cond] == True:
                    cond_neg = "(!" + cond + ")"
                    break
            new_group.add(cond_neg)
            for cond in group:
                cond_vars = extract_vars(cond, vars)
                for v in cond_vars:
                    cond_new = cond.replace(v, new_var)
                new_group.add(cond_new)
            negated_groups.append(new_group)
            new_vars.append(new_var)
    return negated_groups, new_vars

def get_subgroup(groups, vars_by_groups, seed):
    # get a subset of a randomly selected independent group
    random.seed(seed)
    rand = random.randint(0, len(groups)-1)
    vars = dict()
    subgroup = groups[rand]
    for cond in subgroup:
        vars.update(extract_vars(cond, vars_by_groups[rand]))
    return subgroup, vars

def get_array_calls(formula):
    calls = []
    if formula.is_store() or formula.is_select():
        calls = [formula]

    for subformula in formula.args():
        if not (subformula.is_constant() or subformula.is_literal()):
            calls = calls + get_array_calls(subformula)
    return calls
    
def get_minimum_array_size_from_file(smt_file):
    formula = read_file(smt_file)[3]
    return constrain_array_size(formula)[0]

def constrain_array_size(formula):
    array_ops = get_array_calls(formula)
    if len(array_ops) == 0:
        return 0, set()
    sat = False
    array_size = 2
    if not is_sat(formula):
        formula = Not(formula)
    assertions = set()
    while not sat:
        if array_size > 2**12:  
            raise ValueError("Minimum array size too large")
        assertions = {i < array_size for i in map(lambda x: x.args()[1], array_ops)}
        new_formula = And(*assertions, formula)
        sat = is_sat(new_formula)
        array_size *= 2 
    return array_size // 2, assertions


def main(file_path, resfile):    
    return check_files(file_path, resfile)

def check_files(file_path, resfile):
    if os.path.isdir(file_path):
        print("Going into dir %s\n" % file_path)
        for file in sorted(os.listdir(file_path)):
            check_files(os.path.join(file_path,file), resfile)
        return
    if not file_path.endswith('.smt2'):
        return
    print("Checking file " + file_path)
    try:
        env = reset_env()
        env.enable_infix_notation = True
        #Check number of atoms
        #print("[*] Check atoms:")
        #formula = read_file(file_path)[3]
        #if len(formula.get_atoms()) < 5:
        #    raise ValueError("Not enough atoms") 
        #print("[*] Done")

        # Check that everything is understood by the parser
        # and file doesn't get too large
        print("[*] Check parser:")
        _, _, _, formula = read_file(file_path)
        clauses = conjunction_to_clauses(formula)
        for clause in clauses:
            symbols = set()
            buffer = StringIO()
            convert(symbols,clause, buffer) 
            print(".",end ="")
        print("")
        print("[*] Done.")

        # Check that satisfiability is easily found
        # (else STORM will take a long time to run)
        print("[*] Check sat:")
        so = smtObject(file_path,'temp')
        so.check_satisfiability(60)
        if so.orig_satisfiability == 'timeout':
            raise ValueError('Takes too long to process')
        print("[*] Done.")

        # Check that it is satisfiable on bounded arrays
        print("[*] Check array size:")
        get_minimum_array_size_from_file(file_path)
        print("[*] Done.")

    except Exception as e:
        print("Error in " + file_path + ': ' + str(e))
        return
        
    f = open(resfile, 'a')
    f.write(file_path + '\n')
    f.close()

if __name__ == '__main__':
    from storm.smt.smt_object import smtObject
    resfile = sys.argv[1]
    for i in range(2, len(sys.argv)):
        main(sys.argv[i], resfile)
