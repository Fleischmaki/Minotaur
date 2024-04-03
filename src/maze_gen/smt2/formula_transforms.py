"""Contains functions that handle formulas (but not files or transforms)"""
import math
import typing as t
import logging

from pysmt.shortcuts import And, Not, is_sat,\
    get_env,FreshSymbol, Equals, Int, GT, LT, BV, EqualsOrIff
from pysmt.typing import INT
from pysmt.fnode import FNode
from pysmt.solvers.z3 import Z3Solver


LOGGER = logging.getLogger(__name__)
MAXIMUM_ARRAY_SIZE = 2**10 - 1 

def get_bv_width(node: FNode) -> int:
    """Calculate bit width of a node"""
    res = 0
    if node.get_type().is_bool_type():
        if node.is_bool_constant() or node.is_symbol():
            res = 1
        else:
            res = get_bv_width(node.args()[0])
    elif node.is_bv_extract():
        res = node.bv_extract_end() - node.bv_extract_start()  + 1
    elif node.is_bv_constant() or node.is_symbol() or node.is_function_application() or node.is_ite() or node.is_select():
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
        elif l.is_bv_constant() or l.is_symbol or l.is_function_application() or l.is_ite() or l.is_select():
            res =  l.bv_width()
        elif r.is_bv_constant() or r.is_symbol or r.is_function_application() or r.is_ite() or r.is_select():
            res = r.bv_width()
    else:
        raise ValueError("Could not compute BV width: " + str(node))
    if res <= 0 or res > 64:
        raise ValueError(f"Invalid bv width: {res}({node})")
    return res

def is_neg_sat(c, clauses):
    """Check if negation of a c is sat
    """
    form_neg = Not(c)
    for n in clauses:
        if n is not c:
            form_neg = form_neg.And(n)
    sat = is_sat(form_neg, solver_name = "z3")
    return sat


def get_unsat_core(clauses: list[FNode], logic: str):
    """ Compute unsat core for given clauses
    """
    LOGGER.info('Finding unsat core')
    solver = Z3Solver(get_env(),logic,unsat_cores_mode='all')
    solver.add_assertions(clauses)
    solver.solve()
    core = set(solver.get_unsat_core())
    LOGGER.info("Done")
    return core


def rename_arrays(formula: FNode):
    """ Introduce fresh variable for every chain of array stores
    """
    constraints = set()
    subs = {}

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


def get_nodes(formula: FNode, cond: t.Callable[[FNode], bool]):
    """ Get all nodes that satisfy a condition 
    """
    return get_nodes_helper(formula,cond,set())

def get_nodes_helper(node: FNode,cond: t.Callable[[FNode], bool],visited_nodes: set) -> t.Set[FNode]:
    """ Helper function for get_nodes
    """
    visited_nodes.add(node.node_id())
    matching = set()
    if cond(node):
        matching.add(node)
    for sub in node.args():
        if sub.node_id() not in visited_nodes:
            matching.update(get_nodes_helper(sub, cond, visited_nodes))
    return matching


def get_division_constraints(formula: FNode):
    """ Returns constraints encoding that divisors should not be zero  
    """
    divisions = get_nodes(formula, (lambda f : f.is_div() or f.is_bv_udiv() or f.is_bv_sdiv() or f.is_bv_urem() or f.is_bv_srem()))
    return [Not(Equals(BV(0,get_bv_width(div)),div)) for div in map(lambda division : division.args()[1], divisions)]


def check_indices(symbol: str,maxArity: int,maxId :int, cons_in_c: str):
    if maxArity == 0:
        return set([symbol]) if symbol in cons_in_c else set()
    for index in range(maxId):
        var = symbol + '_' + str(index)
        res = set([var]) if var in cons_in_c else set()
        res = res.union(check_indices(var, maxArity-1,maxId,cons_in_c))
    return res

def get_array_index_calls(formula: FNode):
    return get_array_calls_helper(formula, set())

def constrain_array_size(formula: FNode):
    LOGGER.info("Calculating array size.")
    min_index, array_ops = get_array_index_calls(formula)
    if len(array_ops) == 0:
        LOGGER.info("No arrays found")
        return 0, set()
    if not is_sat(formula, solver_name = "z3"):
        formula = Not(formula)
    max_dim = max(map(lambda op : get_array_dim(op.args()[0]),array_ops))
    sat = False
    assertions = set()
    array_size = max(min_index,2)
    
    while not sat:
        LOGGER.debug("Checking size: %d",  array_size)
        if (math.pow(array_size,max_dim)) > MAXIMUM_ARRAY_SIZE:  
            raise ValueError("Minimum array size too large")
        assertions = get_array_constraints(array_ops, array_size)
        new_formula = And(*assertions, formula)
        sat = is_sat(new_formula, solver_name = "z3")
        array_size *= 2
    array_size //= 2
    LOGGER.info("Sat on size %d.", array_size)
    return array_size, assertions

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

def get_array_dim(node: FNode):
    dim = 0
    curr_type = node.get_type() 
    while curr_type.is_array_type():
        curr_type = curr_type.elem_type
        dim += 1
    return dim

def get_array_constraints(array_ops, array_size):
    return {And(i < array_size, i >= 0) for i in map(lambda x: x.args()[1], array_ops)}


def get_integer_constraints(formula: FNode):
    integer_operations = get_nodes(formula, lambda f: f.get_type() is INT)
    return {(GT(i, Int(-(2**63)))) for i in integer_operations}.union((LT(i, Int(2**63 - 1))) for i in integer_operations)

def extract_vars(cond: t.List[str], variables: t.Dict[str,str]):    
    variables = {}
    for variable, vartype in variables.items():
        if variable + " " in cond or variable + ")" in cond or variable.split('[')[0] in cond:
            variables[variable] = vartype
    return variables

def daggify(formula: FNode, limit: int):
    node_queue = [formula]
    seen = {}
    subs = {}
    while len(node_queue) > 0:
        node = node_queue.pop()
        for sub in node.args():
            if sub.node_id() in seen:
                seen[sub.node_id()] += 1
                if seen[sub.node_id()] == limit:
                    if not (sub.is_constant() or sub.is_symbol() or sub.is_function_application() or sub.is_not()):
                        var = FreshSymbol(sub.get_type())
                        # Compute fixpoint over substitution
                        sub = calculate_substitution_fixpoint(subs, sub)
                        subs.update({sub: var})
                        formula = formula.substitute(subs)
            else:
                seen[sub.node_id()] = 0
                node_queue.append(sub)
    formula = And(*[EqualsOrIff(sub,var) for (sub,var) in subs.items()], formula)
    return formula, set(subs.values())

def calculate_substitution_fixpoint(subs: dict, sub: FNode):
    old = sub
    sub = old.substitute(subs)
    while old != sub:
        old = sub
        sub = sub.substitute(subs)
    return sub