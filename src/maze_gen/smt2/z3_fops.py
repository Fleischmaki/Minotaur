"""Contains functions that handle formulas (but not files or transforms)"""
import math
import typing as t
import logging
import io
from z3 import *
from z3.z3consts import *

LOGGER = logging.getLogger(__name__)
MAXIMUM_ARRAY_SIZE = 2**32


def conjunction_to_clauses(node: ExprRef) -> set[ExprRef]:
    """Transform top-level conjuncts of a formula into a set of clauses"""
    clauses = set()
    node_queue = [node]
    while len(node_queue) > 0:
        node = node_queue.pop()
        if is_app_of(node, Z3_OP_AND):
            for subnode in node.children():
                node_queue.append(subnode)
        else:
            clauses.add(node)
    return clauses

def get_bv_width_from_array_type(array_type: SortRef) -> int:
    """ Returns the width for the base element type of an array.
        User get_bv_width(ExprRef) for more precise width computation. 
    :param array_type: type of the array
    """
    node_type = get_array_base_type(array_type) # type: ignore
    if node_type.kind() == Z3_BOOL_SORT:
        return 1
    if node_type.kind() == Z3_INT_SORT:
        return 64
    if node_type.kind() == Z3_BV_SORT:
        return node_type.size() # type: ignore
    raise ValueError(f"Could not compute BVWidth for node of type {node_type}.")


def get_bv_width(node: ExprRef) -> int:
    """Calculate bit width of a node"""
    res = 0
    if node.sort_kind() == Z3_INT_SORT:
        res = 64
    elif node.sort().kind() == Z3_BOOL_SORT:
        if node.num_args == 0:
            res = 1
        else:
            res = get_bv_width(node.children()[0]) # For relations, give width of elements, as relation width is 1
    elif node.sort().kind() == Z3_ARRAY_SORT:
        return get_bv_width_from_array_type(node.sort()) # type: ignore
    elif not (node.sort().kind() == Z3_BV_SORT):
        raise ValueError(f"Could not compute BVWidth for node {node} of type {node.sort()}.")
    else:
        res = node.size() #type: ignore
    if res <= 0 or res > 64:
        raise ValueError(f"Invalid bv width: {res}({node})")
    return res

def needs_declaration(formula):
    return (is_const(formula) and not is_supported_value(formula)) or is_app_of(formula, Z3_OP_UNINTERPRETED) or (is_array(formula) and formula.num_args() == 0)

def is_supported_value(formula):
    return  is_int_value(formula) or \
            is_bv_value(formula) 

def is_neg_sat(c, clauses):
    """Check if negation of a c is sat
    """
    form_neg = Not(c)
    for n in clauses:
        if n is not c:
            form_neg = And(form_neg, n)
    return is_sat(form_neg)


def get_unsat_core(clauses: list[ExprRef]):
    """ Compute unsat core for given clauses
    """
    LOGGER.info('Finding unsat core')
    solver = Solver() 
    LOGGER.debug(solver.check(*clauses))
    core = set(clause for clause in solver.unsat_core())
    LOGGER.info("Found core of size %s", len(core))
    return core


def rename_arrays(formula: ExprRef):
    """ Introduce fresh variable for every chain of array stores
    """
    constraints = set()
    for i in range(len(formula.children())):
        sub = formula.arg(i)
        new_formula, new_constraints = rename_arrays(sub)
        constraints = constraints.union(new_constraints)
        formula = substitute(formula, (sub, new_formula))

    if is_app_of(formula, Z3_OP_STORE):
        old = formula.arg(0)
        if not is_app_of(old, Z3_OP_STORE):
            new = Array(str(old) + '__store', old.sort().domain(),old.sort().range()) #type: ignore
            constraints.add(old == new)
            formula = substitute(formula, (old, new))

    return formula, constraints


def get_nodes(formula: ExprRef, cond: t.Callable[[ExprRef], bool]) -> set[ExprRef]:
    """ Get all nodes that satisfy a condition 
    """
    node_queue = [formula]
    visited_nodes = set()
    matching = set()
    while len(node_queue) > 0:
        node = node_queue.pop()
        visited_nodes.add(node.get_id())
        if cond(node):
            matching.add(node)
        for sub in node.children():
            if sub.get_id() not in visited_nodes:
                node_queue.append(sub)
    return matching

def get_division_constraints(formula: ExprRef) -> list[ExprRef]:
    """ Returns constraints encoding that divisors should not be zero  
    """
    divisions = get_nodes(formula, (lambda f : is_app_of(f, Z3_OP_DIV) or is_app_of(f, Z3_OP_BUDIV) or is_app_of(f, Z3_OP_BSDIV) \
                                            or is_app_of(f, Z3_OP_MOD) or is_app_of(f, Z3_OP_BUREM) or is_app_of(f, Z3_OP_BSREM)))
    return [BitVec(0,get_bv_width(div)) != div for div in map(lambda division : division.children()[1], divisions)] # type: ignore

def get_shift_constraints(formula: ExprRef) -> list[ExprRef]:
    """ Returns constraints encoding that shifts cannot be larger than the width of the index  
    """
    shifts = get_nodes(formula, lambda f: is_app_of(f, Z3_OP_BASHR) or is_app_of(f, Z3_OP_BLSHR) or is_app_of(f, Z3_OP_BSHL))
    return  [(shift.arg(1) < get_bv_width(shift)) for shift in shifts] # type: ignore
def get_array_index_calls(formula: ExprRef):
    """ Collect all array calls and maximum index for formula
    """
    calls = get_nodes(formula, lambda n: is_app_of(n, Z3_OP_STORE) or is_app_of(n, Z3_OP_SELECT))
    constant_indices = list(map(lambda n: int(str(n)), filter(is_constant_value, map(lambda n: n.arg(1), calls))))
    max_constant_access = 2 if len(constant_indices) == 0 else max(constant_indices)
    return max_constant_access, list(calls)

def is_constant_value(node: ExprRef):
    return is_bv_value(node) or is_int_value(node)

def get_indices_for_each_array(array_operations: list[ExprRef]) -> dict[str,set[int]]:
    """"Get a dict containing the constant indeces used for every array
    :param array_operations: A list of array operations. Should only use constant indeces.
    """
    res = {}
    for op in array_operations:
        name = get_array_name(op.arg(0))
        if get_array_name(op) not in res:
            res[name] = set()
        if is_app_of(op, Z3_OP_EQ):
            name2 = get_array_name(op.arg(1))
            if name2 not in res:
                res[name2] = set()
        else:
            index = op.children()[1]
            if not(is_constant_value(index)):
                raise ValueError("Should not be collecting non-constant indeces")
            res[name].add(int(str(index)))
    return res

def label_formula_depth(formula: ExprRef) -> dict[ExprRef, int]:
    """ Collect the depth of the formula and every subformula
    :returns : a dict mapping each subformula to its depth 
    """
    node_queue = [formula]
    compute_queue = [formula]
    depths = {}
    while len(node_queue) > 0:
        node = node_queue.pop(0) # BFS so we do bottom up afterwards
        for sub_formula in node.children():
            if sub_formula.num_args() == 0:
                depths[sub_formula] = 0
            else:
                node_queue.append(sub_formula)
                compute_queue.append(sub_formula)
    for node in reversed(compute_queue):
        depths[node] = max(map(lambda s: depths[s], node.children())) + 1
    return depths

def constrain_array_size(formula: ExprRef, logic: str):
    """ Compute a minimal array size for the formula
    Returns the minimal array_size and the list of generated constraints 
    """
    LOGGER.info("Calculating array size.")
    min_index, array_ops = get_array_index_calls(formula)
    all_constant = all(map(lambda node: is_constant_value(node.arg(1)), array_ops)) and not any(map(lambda op: is_app_of(op, Z3_OP_STORE), array_ops))
    if len(array_ops) == 0:
        LOGGER.info("No arrays found")
        return -1, [], -1, True
    if not is_sat(formula):
        formula = Not(formula) # type: ignore
    max_dim = max(map(lambda op : get_array_dim(op.children()[0]),array_ops))
    assertions = []
    array_size = max(min_index,2)
    max_size = MAXIMUM_ARRAY_SIZE if 'BV' not in logic else min(MAXIMUM_ARRAY_SIZE, *map(lambda op: 2**(op.arg(0).sort().domain().size()), array_ops)) #type: ignore
    sat = all_constant and array_size**max_dim <= max_size
    if sat:
        array_size *= 2
    while not sat:
        LOGGER.debug("Checking size: %d",  array_size)
        if (math.pow(array_size,max_dim)) > max_size:
            raise ValueError("Minimum array size too large")
        assertions = get_array_constraints(array_ops, array_size)
        new_formula = And(*assertions, formula)
        sat = is_sat(new_formula)
        array_size *= 2
    array_size //= 2
    LOGGER.info("Sat on size %d.", array_size)
    return array_size, assertions, min_index, all_constant

def is_sat(formula) -> bool:
    s = Solver()
    s.add(formula)
    return s.check() == sat

def get_array_base_type(node_type: ArraySortRef) -> SortRef:
    """ Get the base element type for a (potentially multi-dimensional) array-type
    """
    while node_type.kind() == Z3_ARRAY_SORT:
        node_type = node_type.domain() # type: ignore
    return node_type

def get_array_name(node: ExprRef) -> str:
    """Get the name of an array from a sequence of stores/selects
    """
    while not node.num_args() == 0:
        node = node.arg(0)
    return str(node)

def get_array_dim(node: ExprRef):
    """ Returns dimension of an array, or 0 if it is not an array
    """
    dim = 0
    curr_type = node.sort()
    while curr_type.kind() == Z3_ARRAY_SORT:
        curr_type = curr_type.domain() # type: ignore
        dim += 1
    return dim

def get_array_constraints(array_ops: list[ExprRef], array_size: int) -> list[ExprRef]:
    """ Get constraints ensuring that the indices should be at most the given size.
    :return: A list of constraints, sorted by the number of array accesses in the constraints.
    """
    return sorted([And(i <= array_size, i >= 0) for i in filter(lambda index: not is_constant_value(index), map(lambda x: x.arg(1), array_ops))], #type: ignore
                  key = lambda op: len(get_array_index_calls(op)[1])) 

def get_integer_constraints(formula: ExprRef):
    """ Collect constraints that no integer expression in the formula overflows
    """
    integer_operations = get_nodes(formula, lambda f: f.sort_kind() == Z3_INT_SORT)
    return {(i > -(2**63)) for i in integer_operations}.union((i < (2**63 - 1)) for i in integer_operations)

def extract_vars(cond: t.List[str], variables: t.Dict[str,str]):
    """ Find all variables appearing in a condition
    """
    variables = {}
    for variable, vartype in variables.items():
        if variable + " " in cond or variable + ")" in cond or variable.split('[')[0] in cond:
            variables[variable] = vartype
    return variables

def daggify(formula: ExprRef, limit: int):
    """ Replace subexpression that occur often with new variables
    :param limit:   How often a subexpression needs to occur before it is replaced
    """
    node_queue = [formula]
    seen = {}
    subs = []
    while len(node_queue) > 0:
        node = node_queue.pop()
        for sub in node.children():
            if sub.get_id() in seen:
                seen[sub.get_id()] += 1
                if seen[sub.get_id()] == limit:
                    if sub.num_args() > 1:
                        var = Const(sub.get_id(),sub.sort())
                        sub = compute_substitution_fixpoint(subs, sub)
                        subs.append((sub, var))
                        formula = substitute(formula,*subs)
            else:
                seen[sub.get_id()] = 0
                node_queue.append(sub)
    formula = And(*[sub == var for (sub,var) in subs], formula) #type: ignore
    print(is_sat(formula))
    return formula

def compute_substitution_fixpoint(current_subs: dict, new_sub: ExprRef):
    """ Add a new substitution to a list of substitutions and compute fixpoint
    Ensures that the new subsitution is in turn applied to all previous ones, if possible
    """
    old = new_sub
    new_sub = substitute(old, *current_subs)
    while not old.eq(new_sub):
        print(old, new_sub)
        old = new_sub
        new_sub = substitute(new_sub, *current_subs)
    return new_sub

def clauses_to_smtlib(clauses : ExprRef | t.Iterable[ExprRef], logic: str):
    """Write a formula to a file
    :param formula: If an iterable is provided, takes a conjunction of those clauses
    """
    string_builder = io.StringIO()
    if isinstance(clauses,ExprRef):
        formula = clauses
        clauses = [clauses]
    else:
        formula: ExprRef = And(*clauses) # type: ignore

    decls = get_nodes(formula, needs_declaration)
    string_builder.write(f"(set-logic {logic})\n")
    for decl in decls:
        string_builder.write(f"(declare-fun {decl} () {sort_to_smtlib(decl.sort())})\n")
    for clause in clauses:
        string_builder.write(f"(assert {clause.sexpr()})\n")
    string_builder.write("(check-sat)\n")
    string_builder.seek(0)
    result_string = string_builder.read()
    string_builder.close()
    return result_string

def sort_to_smtlib(sort: SortRef):
    if sort.kind() == Z3_ARRAY_SORT:
        return f"(Array {sort_to_smtlib(sort.domain())} {sort_to_smtlib(sort.range())})" #type: ignore
    if sort.kind() == Z3_BV_SORT:
        return f"(_ BitVec {sort.size()})" #type:ignore
    return str(sort)

