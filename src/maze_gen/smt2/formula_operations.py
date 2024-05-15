"""Contains functions that handle formulas (but not files or transforms)"""
import array
import math
import typing as t
import logging

from pysmt.shortcuts import And, Not, is_sat,\
    get_env,FreshSymbol, Equals, BV, EqualsOrIff
from pysmt import typing as smt_types
from pysmt.fnode import FNode
from pysmt.solvers.z3 import Z3Solver


LOGGER = logging.getLogger(__name__)
MAXIMUM_ARRAY_SIZE = 2**8

def get_bv_width_from_array_type(array_type: smt_types._ArrayType) -> int:
    """ Returns the width for the base element type of an array.
        User get_bv_width(FNode) for more precise width computation. 
    :param array_type: type of the array
    """
    node_type = get_array_base_type(array_type)
    if node_type.is_bool_type():
        return 1
    if node_type.is_int_type():
        return 64
    if node_type.is_bv_type():
        return node_type.width # type: ignore
    raise ValueError(f"Could not compute BVWidth for node of type {node_type}.")


def get_bv_width(node: FNode) -> int: # 
    """Calculate bit width of a node"""
    res = 0
    if node.get_type().is_int_type():
        res = 64
    elif node.get_type().is_bool_type():
        if node.is_bool_constant() or node.is_symbol():
            res = 1
        else:
            res = get_bv_width(node.args()[0]) ## Boolean relations
    elif node.get_type().is_array_type():
        return get_bv_width_from_array_type(node.get_type())
    elif not (node.get_type().is_bv_type()):
        raise ValueError(f"Could not compute BVWidth for node {node} of type {node.get_type()}.")
    elif node.is_bv_comp():
        return 1
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
        raise ValueError(f"Could not compute BV width: for {node} of type {type}")
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

    for sub in formula.args():
        new_formula, new_constraints = rename_arrays(sub)
        constraints = constraints.union(new_constraints)
        formula = formula.substitute({sub: new_formula})

    if formula.is_store():
        old = formula.arg(0)
        if not old.is_store():
            new = FreshSymbol(typename=old.get_type())
            constraints.add(Equals(old,new))
            formula = formula.substitute({old : new})

    return formula, constraints


def get_nodes(formula: FNode, cond: t.Callable[[FNode], bool]):
    """ Get all nodes that satisfy a condition 
    """
    node_queue = [formula]
    visited_nodes = set()
    matching = set()
    while len(node_queue) > 0:
        node = node_queue.pop()
        visited_nodes.add(node.node_id())
        if cond(node):
            matching.add(node)
        for sub in node.args():
            if sub.node_id() not in visited_nodes:
                node_queue.append(sub)
    return matching

def get_division_constraints(formula: FNode) -> list[FNode]:
    """ Returns constraints encoding that divisors should not be zero  
    """
    divisions = get_nodes(formula, (lambda f : f.is_div() or f.is_bv_udiv() or f.is_bv_sdiv() or f.is_bv_urem() or f.is_bv_srem()))
    return [Not(Equals(BV(0,get_bv_width(div)),div)) for div in map(lambda division : division.args()[1], divisions)]

def get_shift_constraints(formula: FNode) -> list[FNode]:
    """ Returns constraints encoding that shifts cannot be larger than the width of the index  
    """
    shifts = get_nodes(formula, lambda f: f.is_bv_ashr() or f.is_bv_lshr() or f.is_bv_lshl())
    return  [(shift.arg(1) < get_bv_width(shift)) for shift in shifts]

def get_array_index_calls(formula: FNode):
    """ Collect all array calls and maximum index for formula
    """
    return get_array_calls_helper(formula, set())

def get_array_calls_helper(formula: FNode, visited_nodes: set):
    """Helper for get_array_index_calls
    """
    visited_nodes.add(formula.node_id())
    calls = []
    min_size = 1
    if formula.is_store() or formula.is_select():
        if formula.args()[1].is_constant():
            min_size = max(min_size, formula.arg(1).constant_value())
        if formula.args()[1].is_bv_zext() and formula.arg(1).arg(0).is_bv_constant():
            min_size = max(min_size, formula.arg(1).arg(0).constant_value())
        calls = [formula]
    for subformula in formula.args():
        if not (subformula.is_constant() or subformula.is_literal() or subformula.node_id() in visited_nodes):
            sub_min, sub_calls = get_array_calls_helper(subformula, visited_nodes)
            calls += sub_calls
            min_size = max(min_size, sub_min)
    return min_size, calls

def get_indices_for_each_array(array_operations: list[FNode]) -> dict[str,set[int]]:
    """"Get a dict containing the constant indeces used for every array
    :param array_operations: A list of array operations. Should only use constant indeces.
    """
    res = {}
    for op in array_operations:
        name = get_array_name(op.arg(0))
        if get_array_name(op) not in res:
            res[name] = set()
        if op.is_equals():
            name2 = get_array_name(op.arg(1))
            if name2 not in res:
                res[name2] = set()
        else:
            index = op.args()[1]
            if not(index.is_constant()):
                raise ValueError("Should not be collecting non-constant indeces")
            res[name].add(index.constant_value())
    return res

def label_formula_depth(formula: FNode) -> dict[FNode, int]:
    node_queue = [formula]
    compute_queue = [formula]
    depths = {}
    while len(node_queue) > 0:
        node = node_queue.pop(0) # BFS so we do bottom up afterwards
        for sub_formula in node.args():
            if sub_formula.is_constant() or sub_formula.is_symbol():
                depths[sub_formula] = 0
            else:
                node_queue.append(sub_formula)
                compute_queue.append(sub_formula)
    for node in reversed(compute_queue):
        depths[node] = max(map(lambda s: depths[s], node.args())) + 1
    return depths

def constrain_array_size(formula: FNode, logic: str):
    """ Compute a minimal array size for the formula
    Returns the minimal array_size and the list of generated constraints 
    """
    LOGGER.info("Calculating array size.")
    min_index, array_ops = get_array_index_calls(formula)
    all_constant = all(map(lambda node: node.args()[1].is_constant(), array_ops)) and not any(map(lambda op: op.is_store(), array_ops))
    if len(array_ops) == 0:
        LOGGER.info("No arrays found")
        return -1, [], -1, True
    if not is_sat(formula, solver_name = "z3"):
        formula = Not(formula)
    max_dim = max(map(lambda op : get_array_dim(op.args()[0]),array_ops))
    assertions = []
    array_size = max(min_index,2)
    max_size = MAXIMUM_ARRAY_SIZE if 'BV' not in logic else min(MAXIMUM_ARRAY_SIZE, *map(lambda op: 2**(op.arg(0).get_type().index_type.width), array_ops))
    sat = all_constant and array_size**max_dim <= max_size
    if sat:
        array_size *= 2
    while not sat:
        LOGGER.debug("Checking size: %d",  array_size)
        if (math.pow(array_size,max_dim)) > max_size:
            raise ValueError("Minimum array size too large")
        assertions = get_array_constraints(array_ops, array_size)
        new_formula = And(*assertions, formula)
        sat = is_sat(new_formula, solver_name = "z3", logic=logic)
        array_size *= 2
    array_size //= 2
    LOGGER.info("Sat on size %d.", array_size)
    return array_size, assertions, min_index, all_constant

def get_array_base_type(node_type: smt_types.PySMTType) -> smt_types.PySMTType:
    while node_type.is_array_type():
        node_type = node_type.elem_type # type: ignore
    return node_type

def get_array_name(node: FNode) -> str:
    """Get the name of an array from a sequence of stores/selects
    """
    while not node.is_symbol():
        node = node.args()[0]
    return str(node)

def get_array_dim(node: FNode):
    """ Returns dimension of an array, or 0 if it is not an array
    """
    dim = 0
    curr_type = node.get_type()
    while curr_type.is_array_type():
        curr_type = curr_type.elem_type
        dim += 1
    return dim

def get_array_constraints(array_ops, array_size) -> list[FNode]:
    """Helper"""
    return sorted({And(i <= array_size, i >= 0) for i in filter(lambda index: not index.is_constant(), map(lambda x: x.arg(1), array_ops))},
                  key = lambda op: len(get_array_index_calls(op)[1]))

def get_integer_constraints(formula: FNode):
    """ Collect constraints that no integer expression in the formula overflows
    """
    integer_operations = get_nodes(formula, lambda f: f.get_type().is_int_type())
    return {(i > -(2**63)) for i in integer_operations}.union((i < (2**63 - 1)) for i in integer_operations)

def extract_vars(cond: t.List[str], variables: t.Dict[str,str]):
    """ Find all variables appearing in a condition
    """
    variables = {}
    for variable, vartype in variables.items():
        if variable + " " in cond or variable + ")" in cond or variable.split('[')[0] in cond:
            variables[variable] = vartype
    return variables

def daggify(formula: FNode, limit: int):
    """ Replace subexpression that occur often with new variables
    :param limit:   How often a subexpression needs to occur before it is replaced
    """
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
                        sub = compute_substitution_fixpoint(subs, sub)
                        subs.update({sub: var})
                        formula = formula.substitute(subs)
            else:
                seen[sub.node_id()] = 0
                node_queue.append(sub)
    formula = And(*[EqualsOrIff(sub,var) for (sub,var) in subs.items()], formula)
    return formula, set(subs.values())

def compute_substitution_fixpoint(current_subs: dict, new_sub: FNode):
    """ Add a new substitution to a list of substitutions and compute fixpoint
    Ensures that the new subsitution is in turn applied to all previous ones, if possible
    """
    old = new_sub
    new_sub = old.substitute(current_subs)
    while old != new_sub:
        old = new_sub
        new_sub = new_sub.substitute(current_subs)
    return new_sub
