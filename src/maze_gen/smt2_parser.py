import re
import sys, random, os
from collections import defaultdict, OrderedDict, namedtuple
import io

from pysmt.smtlib.parser import SmtLibParser
from pysmt.shortcuts import *
from pysmt.typing import INT
from pysmt.oracles import get_logic
from pysmt.smtlib.commands import SET_LOGIC
from pysmt.fnode import FNode
from pysmt.typing import PySMTType as node_type

from pysmt.solvers.z3 import Z3Solver

import math
import typing as t


T = t.TypeVar('T')
SmtFileData = namedtuple('SmtFileData',['decl_arr','variables','formula', 'logic', 'clauses'])
MAXIMUM_ARRAY_SIZE = 2**9

def deflatten(args: t.List[T], op: t.Callable[[T,T],T]) -> T:
    x = args[0]
    for i in range(1,len(args)):
        y = args[i]
        x = op(x,y)
    return x

def error(flag: int, *info):
    if flag == 0:
        raise ValueError("ERROR: node type not recognized: ", info)
    elif flag == 1:
        raise ValueError("ERROR: nodes not supported", info)
    else:
        raise ValueError("ERROR: an unknown error occurred")

def binary_to_decimal(binary: str, unsigned : bool = True) -> str:
    if len(binary) > 64:
        error(1, "BV width > 64: ",binary)
    val = str(BV(binary).constant_value() if unsigned else BV(binary).bv_signed_value())
    if len(binary) > 32:
        val += 'ULL' if unsigned else 'LL'
    return val 

def bits_to_type(num_bits: int):
    if num_bits <= 8:
        return "char"
    elif num_bits <= 16:
        return "short"
    elif num_bits <= 32:
        return "int"
    elif num_bits <= 64:
        return "long"
    else:
        error(1, "BV width > 64:", num_bits)
        
def bits_to_stype(numb_bits: int) -> str:
    return "signed " + bits_to_type(numb_bits)
def bits_to_utype(num_bits: int) -> str:
    return "unsigned " + bits_to_type(num_bits)

def signed(node: FNode,converted_node: str) -> str:
    width = get_bv_width(node)
    scast = bits_to_stype(width)  
    if width in (1,8,16,32,64):
        return '((%s) %s)' % (scast, converted_node)  
    return ('scast_helper(%s,%s)' % (converted_node,width))

def unsigned(node: FNode,converted_node: str) -> str:
    return '(%s %s)' % (get_unsigned_cast(node), converted_node)  

def get_unsigned_cast(node: FNode) -> str:
    width = get_bv_width(node)
    if width in (8,16,32,64):
        return '(' + bits_to_utype(width) + ') '
    return '(%s)%s&' % (bits_to_utype(width),binary_to_decimal('1'*width))

def get_bv_width(node: FNode) -> int:
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
        error(1,"Could not compute BV width: ", node)
    
    if res <= 0 or res > 64:
        error(1,"Invalid bv width: ", res, node)
    return res

def type_to_c(ntype: node_type) -> str:
    if ntype.is_int_type():
        return 'long'
    if ntype.is_bool_type():
        return 'bool'
    elif ntype.is_bv_type():
        return bits_to_utype(ntype.width)
    elif ntype.is_function_type():
        return type_to_c(ntype.return_type)
    elif ntype.is_array_type():
        if ntype.elem_type.is_array_type():
            return '%s[ARRAY_SIZE]' % type_to_c(ntype.elem_type) # otherwise store might be unsound, we can always cast afterwards
        return 'long[ARRAY_SIZE]'
    # elif type.is_string_type():
    #     return 'string'
    else:
        error(0, ntype)

def convert_helper(symbs: t.Set[str],node: FNode, cons: io.TextIOBase, op: str, cast_sign: str = '', cast_args: bool = True):

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
        n_string = '(' + l_string + op + r_string + ')'
        cons.write(unsigned(node,n_string) if cast_sign == 'u' else signed(node,n_string))


def check_shift_size(node: FNode) -> None:
    global GENERATE_WELL_DEFINED
    if GENERATE_WELL_DEFINED:
        (l,r) = node.args()        
        if not r.is_bv_constant() or r.constant_value() > get_bv_width(node):
            error(1, "Invalid shift: ", node)

def div_helper(symbs: t.Set[str],node: FNode, cons: io.TextIOBase):
    (l,r) = node.args()
    width = get_bv_width(node)

    lString = convert_to_string(symbs, l)
    rString = convert_to_string(symbs, r)

    if node.is_bv_srem() or node.is_bv_sdiv():
        lString = signed(l,lString)
        rString = signed(r,rString)

    if GENERATE_WELL_DEFINED:
        if node.is_bv_srem():
            helper = 'srem_helper'
        elif node.is_bv_urem():
            helper = 'rem_helper'
        elif node.is_bv_udiv():
            helper = 'div_helper'
        else:
            helper = 'sdiv_helper'
        cons.write(unsigned(node,"%s(%s,%s,%s)" % (helper,lString,rString,width)))

    else:
        if node.is_bv_urem() or node.is_bv_srem():
            op = '%'
        else:
            op = '/'
        cons.write(unsigned(node, '(%s %s %s)' % (lString, op, rString)))
 
def convert_to_string(symbs: t.Set[str], node: FNode):
    buff = io.StringIO()
    convert(symbs, node, buff)
    lString = buff.getvalue()
    buff.close()
    return lString

def get_array_dim(node: FNode):
    dim = 0
    curr_type = node.get_type() 
    while curr_type.is_array_type():
        curr_type = curr_type.elem_type
        dim += 1
    return dim

def get_array_size_from_dim(dim: int):
    if dim <= 0:
        return '1'
    return ('ARRAY_SIZE*'*dim)[:-1]


def get_array_size(node: FNode):
    return get_array_size_from_dim(get_array_dim(node))    

def convert(symbs: t.Set[str],node: FNode,cons: io.TextIOBase):
    if cons.tell() > 2**20:
        raise ValueError("Parse result too large") # Avoid file sizes > 1 MB
    cons.write('(')
    if node.is_iff() or node.is_equals() or node.is_bv_comp():
        (l, r) = node.args()
        if "Array" in str(l.get_type()):
            if "Array" in str(r.get_type()):
                cons.write("array_comp(")
                convert(symbs,l,cons)
                cons.write(",")
                convert(symbs,r,cons)
                cons.write(",%s))" % get_array_size(l))
                return
            error(1, "Cannot compare array with non-array", node)
        convert_helper(symbs,node, cons, " == ")
    elif node.is_int_constant():
        value = str(node.constant_value())
        if int(value) > 2**32:
            value += 'LL'
        cons.write(value)
    elif node.is_plus():
        node = deflatten(node.args(),Plus)
        convert_helper(symbs,node,cons,'+')
    elif node.is_minus():
        convert_helper(symbs,node,cons,'-')
    elif node.is_times():
        node = deflatten(node.args(),Times)
        convert_helper(symbs,node,cons,'*')
    elif node.is_div():
        convert_helper(symbs,node,cons,'/')
    elif node.is_le():
        convert_helper(symbs,node,cons,'<=')
    elif node.is_lt():
        convert_helper(symbs,node,cons,'<')
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
        convert_helper(symbs,node, cons, " - ", 'u', False)
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
        (l,r) = node.args()
        l_string = convert_to_string(symbs,l)
        r_string = convert_to_string(symbs,r)
        cons.write(unsigned(node,'(%s << %s)' % (unsigned(l,l_string),r_string)))
    elif node.is_bv_not():
        (b,) = node.args()
        cons.write(unsigned(node,"(~%s)" % convert_to_string(symbs,b)))
    elif node.is_bv_sext():
        (l,) = node.args()
        res = convert_to_string(symbs,l)
        cons.write(signed(node,res))
    elif node.is_bv_zext():
        (l,) = node.args()
        cons.write('(')
        cons.write(get_unsigned_cast(node))
        convert(symbs,l, cons)
        cons.write(')')
    elif node.is_bv_concat():
        (l,r) = node.args()
        cons.write(unsigned(node,convert_to_string(symbs,l)))
        cons.write(' << %d | ' % get_bv_width(r))
        cons.write(unsigned(node,convert_to_string(symbs,r)))        
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
        cons.write('(' + cast + base + ') - ' + '(' + cast)
        convert(symbs,s,cons)
        cons.write(')')
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
        dim = get_array_dim(node)
        cons.write("*"*(dim-1))
        if str(node) == 'c':
            node = '__original_smt_name_was_c__'
        node = clean_string(node)
        cons.write(node)
        symbs.add(node)
    elif node.is_select():
        (a, p) = node.args()
        if 'BV' in str(node.get_type()): 
            cast = get_unsigned_cast(node)
            cons.write(cast)
        dim = get_array_dim(a)
        convert(symbs, a, cons)
        if dim == 1:
            cons.write("[")
            convert(symbs,p,cons)
            cons.write("]")
        else:
            size = get_array_size_from_dim(dim-1)
            cons.write("+(%s*" % size)
            convert(symbs,p,cons)
            cons.write(")")
    elif node.is_store():
        (a, p, v) = node.args()
        a_dim = get_array_dim(a)
        v_dim = get_array_dim(v)
        if v_dim != (a_dim -1):
            error(1, "Invalid array dimensions for store", node)
        if v_dim == 0:
            cons.write("value_store(")
        else:
            cons.write("array_store(")
        convert(symbs, a, cons)
        cons.write(",")
        convert(symbs,p,cons)
        cons.write(",")
        convert(symbs,v,cons)
        if v_dim > 0:
            cons.write(",")
            cons.write(get_array_size_from_dim(v_dim))
        cons.write(")")
    elif node.is_function_application():
        for n in node.args():
            if not (n.is_bv_constant() or node.is_int_constant()):
                error(1, "Non-constant function call: ", node)
        index = "".join(["_" + str(n.constant_value()) for n in node.args()])
        fn = clean_string(node.function_name())
        cons.write(fn + index)
        symbs.add(fn + index)
    else:
        error(0, node.get_type())
        return("")
    cons.write(')')
    return ""

def rotate_helper(symbs: t.Set[str], node: FNode, cons: io.TextIOBase, op: str):
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

def conjunction_to_clauses(formula: FNode):
    if formula.is_and():
        clauses = set()
        for node in formula.args():
            clauses = clauses.union(conjunction_to_clauses(node))
    else:
        clauses = set([formula])
    return clauses

def get_unsat_cores(clauses, logic):
    print('NOTE: Finding unsat core')
    print(clauses)
    solver = Z3Solver(get_env(),logic,unsat_cores_mode='all')
    solver.add_assertions(clauses)
    print(solver.solve())
    core = set(solver.get_unsat_core())
    print("Done")
    return core

def clean_string(s: str):
    s = str(s)
    return re.sub('[^A-Za-z0-9_]+','_',s)

def rename_arrays(formula: FNode):
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
    if isinstance(formula,t.Iterable):
        formula = And(*formula)
    return write_smtlib(formula, file)

def get_logic_from_script(script):
    if script.contains_command(SET_LOGIC):
        logic = str(script.filter_by_command_name(SET_LOGIC).__next__().args[0])
    else:
        formula = script.get_strict_formula()
        logic = str(get_logic(formula))
        print('NOTE: Logic not found in script. Using logic from formula: ' % (logic))
    return logic

def get_division_constraints(formula: FNode):
    divisions = get_nodes(formula, (lambda f : f.is_div() or f.is_bv_udiv() or f.is_bv_sdiv() or f.is_bv_urem() or f.is_bv_srem()))
    return [Not(Equals(BV(0,get_bv_width(div)),div)) for div in map(lambda division : division.args[1], divisions)]

def get_nodes(formula: FNode, cond: t.Callable[[FNode], bool]):
    return get_nodes_helper(formula,cond,set())

def get_nodes_helper(node: FNode,cond: t.Callable[[FNode], bool],visited_nodes: set) -> t.Set[FNode]:
    visited_nodes.add(node.node_id())
    matching = set()
    if cond(node):
        matching.add(node)
    for sub in node.args():
        if sub.node_id() not in visited_nodes:
            matching.update(get_nodes_helper(sub, cond, visited_nodes))
    return matching
    

def parse(file_path: str, check_neg: bool, continue_on_error=True, generate_well_defined=True):
    set_well_defined(generate_well_defined)
    print("Converting %s: " % file_path)

    decl_arr, variables, formula, logic, formula_clauses = read_file(file_path)  

    clauses, array_size = run_checks(formula, logic, formula_clauses)

    parsed_cons = OrderedDict()
    for c, clause in enumerate(clauses,start=1):
        ldecl_arr = decl_arr

        if logic.split('_')[-1].startswith('A'):
            print("NOTE: Renaming array stores", end = " ")
            clause, constraints = rename_arrays(clause)
            print("Added %d new arrays" % len(constraints))
            clause = And(*constraints, clause) # Make sure to render constraints first
            ldecl_arr.extend(map(lambda c: c.args()[1],constraints))

        symbs = set()

        try:
            print("NOTE: converting clause %d/%d." % (c,len(clauses)), end = " ")
            result = convert_to_string(symbs,clause)
        except Exception as e:
            print("Could not convert clause: ", e)
            if continue_on_error:
                continue
            else:
                raise Exception(e)
        print("Done.")

        add_parsed_cons(check_neg, clauses, parsed_cons, clause, result)
        add_used_variables(variables, ldecl_arr, symbs)

    return parsed_cons, variables, array_size

def add_parsed_cons(check_neg:bool, clauses:list, parsed_cons:OrderedDict, clause:FNode, cons_in_c: str):
    if "model_version" not in cons_in_c:
        if check_neg == True:
            neg_sat = is_neg_sat(clause, clauses)
            parsed_cons[cons_in_c] = neg_sat
        else:
            parsed_cons[cons_in_c] = ""

def add_used_variables(variables: set, ldecl_arr: t.List[FNode], symbs: t.Set[str]):
    for symb in symbs:
        decls = list(map(lambda x: clean_string(x), ldecl_arr))
        if symb in decls:
            decl = symb
        elif 'c' in decls and symb == '__original_smt_name_was_c__':
            decl = 'c'
        else:
            decl = symb.split("_")[0]
        i = decls.index(decl)
        vartype = ldecl_arr[i].get_type()
        type_in_c = type_to_c(vartype)
        if vartype.is_array_type():
            first_bracket = type_in_c.find('[')
            symb += type_in_c[first_bracket:]
            type_in_c = type_in_c[:first_bracket]
        variables[symb] = type_in_c

def set_well_defined(generate_well_defined: bool):
    global GENERATE_WELL_DEFINED
    GENERATE_WELL_DEFINED = generate_well_defined

def run_checks(formula: FNode, logic: str, clauses: t.Set[FNode]):
    if not is_sat(formula,'z3'):
        return clauses, MAXIMUM_ARRAY_SIZE
    
    clauses =  []
    constraints = set()

    if 'BV' not in logic and GENERATE_WELL_DEFINED:
        print("WARNING: Can only guarantee well-definedness on bitvectors")
    
    if logic.split('_')[-1].startswith('A'):
        array_size, array_constraints = constrain_array_size(formula)
        if GENERATE_WELL_DEFINED:
            clauses.extend(array_constraints)# Make sure to render constraints first
        constraints.update(array_constraints)
    else:
        array_size = -1
    
    if 'IA' in logic:
        print("NOTE: Generating integer constraints")
        constraints.update(get_integer_constraints(formula))
    
    if not GENERATE_WELL_DEFINED:
        print("NOTE: Generating divsion constraints")
        constraints.update(get_division_constraints(formula))
    
    if len(constraints) > 0:
        print("NOTE: Checking satisfiability with global constraints")
        if not is_sat(And(formula, *constraints), solver_name='z3'):
            raise ValueError("Cannot guarantee a valid solution")
        print("Done.")
    
    clauses.extend(clauses)
    if len(clauses) > 256:
        print("WARNING: Original number of clauses (%d) too large, dropping some" % len(clauses))
        clauses = clauses[:255]
    return clauses,array_size

def read_file(file_path: str):
    parser = SmtLibParser()
    script = parser.get_script_fname(file_path)
    decl_arr = list()
    variables = dict()
    decls = script.filter_by_command_name("declare-fun")
    for d in decls:
        for arg in d.args:
            if (str)(arg) != "model_version":
                decl_arr.append(arg)
    formula = script.get_strict_formula()
    logic = get_logic_from_script(script)  
    clauses = conjunction_to_clauses(formula) 

    return SmtFileData(decl_arr,variables,formula, logic, clauses)

def check_indices(symbol: str,maxArity: int,maxId :int, cons_in_c: str):
    if maxArity == 0:
        return set([symbol]) if symbol in cons_in_c else set()
    for id in range(maxId):
        var = symbol + '_' + str(id)
        res = set([var]) if var in cons_in_c else set()
        res = res.union(check_indices(var, maxArity-1,maxId,cons_in_c))
    return res    

def get_integer_constraints(formula: FNode):
    integer_operations = get_nodes(formula, lambda f: f.get_type() is INT)
    return {(GT(i, Int(-(2**63)))) for i in integer_operations}.union((LT(i, Int(2**63 - 1))) for i in integer_operations)

def extract_vars(cond: t.List[str], variables: 'dict[str,str]'):    
    vars = dict()
    for var, vartype in variables.items():
        if var + " " in cond or var + ")" in cond or var.split('[')[0] in cond:
            vars[var] = vartype
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

def independent_formulas(conds: OrderedDict, variables: 'dict[str,str]'):
    formula = Graph()
    for cond in conds:
        formula.add_edge(cond,cond)
        vars = extract_vars(cond, variables)
        for other in conds:
            if len(vars.keys() & extract_vars(other, variables).keys()) > 0:
                formula.add_edge(cond, other)
    groups = [sorted(g, key=lambda cond: list(conds.keys()).index(cond)) for g in formula.separate()]
    vars_by_groups = list()
    for group in groups:
        used_vars = dict()
        for cond in group:
            used_vars.update(extract_vars(cond, variables))
        vars_by_groups.append(used_vars)
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

def get_subgroup(groups: t.List[set], vars_by_groups: t.List[t.Dict[str,str]], seed: int):
    if len(groups) == 0:
        return set(), set()
    # get a subset of a randomly selected independent group
    random.seed(seed)
    rand = random.randint(0, len(groups)-1)
    vars = set()
    subgroup = groups[rand]
    for cond in subgroup:
        vars.update(extract_vars(cond, vars_by_groups[rand]))
    return subgroup, vars

def get_array_calls(formula: FNode):
    return get_array_calls_helper(formula, set())

def get_array_calls_helper(formula: FNode, visited_nodes: set):
    visited_nodes.add(formula.node_id())
    calls = []
    min_size = 1
    if formula.is_store() or formula.is_select():
        if formula.args()[1].is_constant():
            min_size = max(min_size, formula.args()[1].constant_value())
        calls = [formula]
    for subformula in formula.args():
        if not (subformula.is_constant() or subformula.is_literal() or subformula.node_id() in visited_nodes):
            sub_min, sub_calls = get_array_calls_helper(subformula, visited_nodes)
            calls += sub_calls
            min_size = max(min_size, sub_min)
    return min_size, calls
    
def get_minimum_array_size_from_file(smt_file: str):
    formula = read_file(smt_file).formula
    return constrain_array_size(formula)[0]

def constrain_array_size(formula: FNode):
    print("NOTE: Calculating array size.")
    min_index, array_ops = get_array_calls(formula)
    if len(array_ops) == 0:
        print("No arrays found")
        return 0, set()

    if not is_sat(formula, solver_name = "z3"):
        formula = Not(formula)
    max_dim = max(map(lambda op : get_array_dim(op.args()[0]),array_ops))
    sat = False
    assertions = set()
    array_size = 2
    
    while array_size < min_index:
        array_size *= 2

    while not sat:
        print("Checking size: %d" % array_size)
        if (math.pow(array_size,max_dim)) > MAXIMUM_ARRAY_SIZE:  
            raise ValueError("Minimum array size too large")
        assertions = {And(i < array_size, i >= 0) for i in map(lambda x: x.args()[1], array_ops)}
        new_formula = And(*assertions, formula)
        sat = is_sat(new_formula, solver_name = "z3")
        array_size *= 2
    array_size //= 2
    print("Sat on size %d."  % array_size)
    return array_size, assertions

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
        # Check that satisfiability is easily found
        # (else everything will take a long time to run)
        print("[*] Check sat:")
        so = smtObject(file_path,'temp')
        so.check_satisfiability(20)
        if so.orig_satisfiability == 'timeout':
            raise ValueError('Takes too long to process')
        print("[*] Done.")


        env = reset_env()
        env.enable_infix_notation = True
        #Check number of atoms
        print("[*] Check atoms:")
        filedata = read_file(file_path).formula
        formula = filedata.formula
        logic = filedata.logic
        clauses = filedata.clauses 
        if len(formula.get_atoms()) < 5:
            raise ValueError("Not enough atoms") 
        print("[*] Done")


        # Check that it is satisfiable on bounded integers
        if 'IA' in str(logic):
            print("[*] Check Integers:")
            if not is_sat(And(formula, *get_integer_constraints(formula)),solver_name='z3'): 
                raise ValueError('Unsat in range')
            print("[*] Done.")

        # Check that it is satisfiable on bounded arrays
        if str(logic).split('_')[-1].startswith('A'):
            print("[*] Check array size:")
            get_minimum_array_size_from_file(file_path)
            print("[*] Done.")


        # Check that everything is understood by the parser
        # and file doesn't get too large          
        print("[*] Check parser:")
        clauses = conjunction_to_clauses(formula)
        for clause in clauses:
            symbols = set()
            buffer = io.StringIO()
            convert(symbols,clause, buffer) 
            print(".",end ="")
        print("")
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
