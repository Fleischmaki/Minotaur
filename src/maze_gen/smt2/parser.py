""" Handles reading and writing SMT Files and similar operation  
"""
import sys
import random
import logging
import typing as t

from collections import defaultdict, OrderedDict, namedtuple

from pysmt.smtlib.parser import SmtLibParser
from pysmt.shortcuts import is_sat, write_smtlib, And, Not, get_env
from pysmt.solvers.z3 import Z3Solver
from pysmt.oracles import get_logic
from pysmt.smtlib.commands import SET_LOGIC
from pysmt.fnode import FNode
import pysmt.exceptions

from . import converter, formula_transforms as ff

LOGGER = logging.getLogger(__name__)

SmtFileData = namedtuple('SmtFileData',['decl_arr','formula', 'logic', 'clauses'])

def parse(file_path: str, transformations: dict, check_neg: bool, continue_on_error = True)\
    -> tuple[OrderedDict[str,bool],dict[str,str],int]:
    """Parses an smt file, converts it into C clauses and extracts the corresponding variables
    :returns:   An OrderedDict containing the resulting C-expressions as keys and value indicating whether the negated expression is also sat
                A dict containing variable names as keys and their respecitve types in C as values
                The minimal array size for the clauses to be valid
    """
    sys.setrecursionlimit(10000)
    generate_well_defined=transformations['wd']
    generate_sat=transformations['sat']
    limit=transformations['dag']
    negate_formula=transformations['neg']
    set_well_defined(generate_well_defined)
    LOGGER.info("Converting %s: ", file_path)
    decl_arr, formula, logic, formula_clauses = read_file(file_path, limit, negate_formula)
    all_arrays_constant = False
    if generate_sat:
        clauses, array_size, all_arrays_constant = run_checks(formula, logic, formula_clauses)
    else:
        array_size, array_calls = ff.get_array_index_calls(formula)
        array_size += 1
        clauses = list(ff.get_array_constraints(array_calls, array_size)) + list(formula_clauses)

    if all_arrays_constant and transformations['ca']:
        converter.set_constant_array_indices(ff.get_indices_for_each_array(ff.get_array_index_calls(formula)[1]))
        array_size = -1
    else:
        converter.set_constant_array_indices({})

    try:
        core = set() if generate_sat else get_unsat_core(clauses, logic)
    except pysmt.exceptions.SolverStatusError as e:
        LOGGER.warning("Could not find core, will abort if any clause fails: %s", e)
        continue_on_error = False
    parsed_cons = OrderedDict()
    variables = {}

    if GENERATE_WELL_DEFINED:
        clauses.sort(key=lambda c: len(ff.get_array_index_calls(c)[1]))

    for c, clause in enumerate(clauses,start=1):
        ldecl_arr = decl_arr

        if logic.split('_')[-1].startswith('A'):
            LOGGER.debug("Renaming array stores")
            clause, constraints = ff.rename_arrays(clause)
            if len(constraints) > 0:
                LOGGER.info("Added %d new arrays", len(constraints)//2)
            clause = And(*constraints, clause) # Make sure to render constraints first
            ldecl_arr.extend(map(lambda c: c.args()[1],constraints))

        symbs = set()

        try:
            LOGGER.debug("Converting clause %d/%d.", c,len(clauses))
            result = converter.convert_to_string(symbs,clause)
        except (ValueError, RecursionError) as e:
            LOGGER.warning("Could not convert clause: %s", str(e))
            if continue_on_error:
                if clause not in core:
                    continue
                parsed_cons['(1==0)'] = True if check_neg else "" # Make sure condition remains unsat
            else:
                raise e
        LOGGER.debug("Done.")

            
        add_parsed_cons(check_neg, clauses, parsed_cons, clause, result)
        add_used_variables(variables, ldecl_arr, symbs, all_arrays_constant)

    return parsed_cons, variables, array_size

def get_unsat_core(clauses, logic):
    """Copmutes the unsat core"""
    LOGGER.info('Computing unsat core')
    solver = Z3Solver(get_env(),logic,unsat_cores_mode='all')
    solver.add_assertions(clauses)
    LOGGER.debug("Solver returned %s", str(solver.solve()))
    core = set(solver.get_unsat_core())
    LOGGER.info("Done")
    return core

def add_parsed_cons(check_neg:bool, clauses:list, parsed_cons:OrderedDict, clause:FNode, cons_in_c: str): 
    """Add condition to the list of conditions""" # TODO weird functions
    if check_neg:
        neg_sat = ff.is_neg_sat(clause, clauses)
        parsed_cons[cons_in_c] = neg_sat
    else:
        parsed_cons[cons_in_c] = ""

def add_used_variables(variables: dict, ldecl_arr: list[FNode], symbs: t.Set[str], constant_arrays:bool):
    """Add a variable to the variable dict"""
    for symb in symbs:
        decls = list(map(converter.clean_string, ldecl_arr))
        if symb in decls:
            decl = symb
        elif 'c' in decls and symb == '__original_smt_name_was_c__':
            decl = 'c'
        else:
            decl = "_".join(symb.split("_")[:-1])
        i = decls.index(decl)
        vartype = ldecl_arr[i].get_type()
        type_in_c = converter.type_to_c(vartype, constant_arrays)
        if vartype.is_array_type() and not constant_arrays:
            first_bracket = type_in_c.find('[')
            symb += type_in_c[first_bracket:]
            type_in_c = type_in_c[:first_bracket]
        variables[symb] = type_in_c

def set_well_defined(generate_well_defined: bool):
    global GENERATE_WELL_DEFINED
    GENERATE_WELL_DEFINED = generate_well_defined
    converter.set_well_defined(generate_well_defined)

def run_checks(formula: FNode, logic: str, formula_clauses: t.Set[FNode]):
    """Check whether the translated formula is going to have valid soltuions"""
    constraints = set()
    clauses = list(formula_clauses)

    if 'BV' not in logic and GENERATE_WELL_DEFINED:
        LOGGER.warning("Can only guarantee well-definedness on bitvectors")

    if logic.split('_')[-1].startswith('A'):
        array_size, array_constraints, _, all_constant = ff.constrain_array_size(formula)
        if GENERATE_WELL_DEFINED:
            clauses.extend(filter(lambda c: len(c.get_free_variables()) > 0, array_constraints))
        constraints.update(array_constraints)
    else:
        array_size = -1
        array_constraints = []
        all_constant = False

    if 'IA' in logic:
        LOGGER.info("Generating integer constraints")
        constraints.update(ff.get_integer_constraints(formula))

    if not GENERATE_WELL_DEFINED:
        LOGGER.info("Generating divsion constraints")
        constraints.update(ff.get_division_constraints(formula))

    if len(constraints) > len(array_constraints):
        LOGGER.info("Checking satisfiability with global constraints")
        if not is_sat(And(*constraints, formula), solver_name='z3'):
            raise ValueError("Cannot guarantee a valid solution")
        LOGGER.info("Done.")
    
    return clauses,array_size, all_constant

def read_file(file_path: str, limit : int = 0, negate_formula : bool = False) -> SmtFileData:
    """Read an SMTfile and extract important fields"""
    parser = SmtLibParser()
    script = parser.get_script_fname(file_path)
    decl_arr = []
    decls = script.filter_by_command_name("declare-fun")
    for d in decls:
        for arg in d.args:
            # if (str)(arg) != "model_version":
            decl_arr.append(arg)
    formula = script.get_strict_formula()
    if negate_formula:
        formula = formula if not is_sat(formula, solver_name='z3') else Not(formula)
    if limit > 0:
        formula, new_decls = ff.daggify(formula, limit)
        decl_arr.extend(new_decls)
    
    logic = get_logic_from_script(script)  
    clauses = conjunction_to_clauses(formula)
    return SmtFileData(decl_arr,formula,logic,clauses)

def get_logic_from_script(script):
    """Read logic from an pysmt script, or guess minimal logic if none is provided"""
    if script.contains_command(SET_LOGIC):
        logic = str(script.filter_by_command_name(SET_LOGIC).__next__().args[0])
    else:
        formula = script.get_strict_formula()
        logic = str(get_logic(formula))
        LOGGER.info('Logic not found in script. Using logic from formula: %s', logic)
    return logic

def conjunction_to_clauses(formula: FNode) -> set[FNode]:
    """Transform top-level conjuncts of a formula into a set of clauses"""
    clauses = set()
    if formula.is_and():
        for node in formula.args():
            clauses = clauses.union(conjunction_to_clauses(node))
    else:
        clauses.add(formula)
    return clauses

def write_to_file(formula : FNode | t.Iterable[FNode], file: str):
    """Write a formula to a file
    :param formula: If an iterable is provided, takes a conjunction of those clauses
    """
    if isinstance(formula,t.Iterable):
        formula = And(*formula)
    return write_smtlib(formula, file)


class Graph:
    """Graph helper for separating variable disjoint subformulas"""
    def __init__(self):
        self.graph = defaultdict(list)

    def add_edge(self, node: str, neighbour:str):
        self.graph[node].append(neighbour)

    def get_edges(self, node: str):
        return self.graph[node]

    def separate_helper(self, node: str, visited: set[str]):
        group = {node}
        current = {node}
        while len(current) != 0:
            new = set()
            for currnode in current:
                for neighbour in self.graph[currnode]:
                    if neighbour not in visited:
                        new.add(neighbour)
            visited.update(new)
            group.update(new)
            current = new
        return group


    def separate(self) -> list[str]:
        visited = set()
        groups = []
        for node in self.graph:
            if node not in visited:
                group = self.separate_helper(node, visited)
                groups.append(group)
        return groups

def independent_formulas(conds: dict[str,bool], variables: dict[str,str], array_size: int) -> tuple[list[list],list[dict]]:
    formula = Graph()
    for cond in conds:
        formula.add_edge(cond,cond)
        cond_vars = extract_vars(cond, variables)
        for other in conds:
            if len(cond_vars.keys() & extract_vars(other, variables).keys()) > 0:
                formula.add_edge(cond, other)
            if is_array_constraint_of(cond,other,array_size):
                formula.add_edge(cond,other)
    groups = [sorted(g, key=lambda cond: list(conds.keys()).index(cond)) for g in formula.separate()]
    vars_by_groups = []
    for group in groups:
        used_vars = {}
        for cond in group:
            used_vars.update(extract_vars(cond, variables))
        vars_by_groups.append(used_vars)
    return groups, vars_by_groups

def extract_vars(cond: str, variables: dict[str,str]):
    used_variables = {}
    for variable, vartype in variables.items():
        if variable + " " in cond or variable + ")" in cond or variable.split('[')[0] in cond:
            used_variables[variable] = vartype
    return used_variables

def is_array_constraint_of(cond: str,other: str,array_size: int):
    if '[' not in cond:
        return False
    index = cond.split('[',1)[1].rsplit(']',1)[0]
    return index in other and '0' in other and str(array_size) in other # TODO maybe refine this

def get_negated(conds: dict, group: list[str], variables: dict[str,str], numb: int) -> tuple[list[str],dict[str,str]]: 
    negated_groups = []
    new_vars = {}
    n = 0
    for cond in group:
        if conds[cond]:
            n = n + 1
    if n >= numb:
        negated = set()
        for i in range(numb):
            negated_group = []
            for cond in reversed(group):
                if conds[cond] and len(negated) <= i and cond not in negated:
                    negated_group.append("(!" + cond + ")")
                    negated.add(cond)
                else:
                    negated_group.append(cond)
            negated_group.reverse()
            negated_groups.append(negated_group)
    elif n == 0:
        new_vars['c'] = 'signed char' # If we don't have any clauses to negate, revert to choice
        for i in range(numb):
            cond_neg = f"(c {'>=' if i == numb-1 else '=='} {i})"
            negated_groups.append([cond_neg])
    else:
        for i in range(numb):
            new_group = set()
            # negate one of the original and add same conds for new var
            for cond in group:
                if conds[cond]:
                    cond_neg = "(!" + cond + ")"
                    break
            new_group.add(cond_neg)
            for j, cond in enumerate(group):
                cond_vars = sorted(list(extract_vars(cond, variables).keys()),key=len,reverse=True)
                for v in cond_vars:
                    new_var = f"__neg_{i}_{j}__{v}"
                    cond = cond.replace(f"({v.split('[')[0]})", f"({new_var.split('[')[0]})")
                    new_vars[new_var] = variables[v]
                new_group.add(cond)
            negated_groups.append(new_group)
    variables.update(new_vars)
    return negated_groups, variables

def get_subgroup(groups: list[list], vars_by_groups: t.List[t.Dict[str,str]], seed: int)\
    -> tuple[list[str],dict[str,str]] :
    if len(groups) == 0:
        return [],{}
    # get a subset of a randomly selected independent group
    random.seed(seed)
    rand = random.randint(0, len(groups)-1)
    variables = {}
    subgroup = groups[rand]
    for cond in subgroup:
        variables.update(extract_vars(cond, vars_by_groups[rand]))
    return subgroup, variables

def get_minimum_array_size_from_file(smt_file: str):
    """Computes the minimum array size for an SMT_File
    :param smt_file: Path to the file
    """
    formula = read_file(smt_file).formula
    return ff.constrain_array_size(formula)
