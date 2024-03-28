import sys, random, logging

from collections import defaultdict, OrderedDict, namedtuple

from pysmt.smtlib.parser import SmtLibParser
from pysmt.shortcuts import *
from pysmt.oracles import get_logic
from pysmt.smtlib.commands import SET_LOGIC
from pysmt.fnode import FNode
import pysmt.exceptions
import typing as t

from . import converter, formula_transforms as ff

LOGGER = logging.getLogger(__name__)

SmtFileData = namedtuple('SmtFileData',['decl_arr','formula', 'logic', 'clauses'])

def parse(file_path: str, check_neg: bool, continue_on_error=True, generate_well_defined=True, generate_sat = True, limit=0):
    sys.setrecursionlimit(10000)
    set_well_defined(generate_well_defined)
    LOGGER.info("Converting %s: " % file_path)
    decl_arr, formula, logic, formula_clauses = read_file(file_path, limit)
    if generate_sat:
        clauses, array_size = run_checks(formula, logic, formula_clauses)
    else:
        array_size, array_calls = ff.get_array_index_calls(formula)
        array_size += 1
        clauses = list(ff.get_array_constraints(array_calls, array_size)) + list(formula_clauses)
    try:
        core = set() if generate_sat else get_unsat_core(clauses, logic)
    except pysmt.exceptions.SolverStatusError as e:
        LOGGER.warning("Could not find core, will abort if any clause fails")
        continue_on_error = False
    parsed_cons = OrderedDict()
    variables = dict()
    
    if GENERATE_WELL_DEFINED:
        clauses.sort(key=lambda c: len(ff.get_array_index_calls(c)[1]))

    for c, clause in enumerate(clauses,start=1):
        ldecl_arr = decl_arr

        if logic.split('_')[-1].startswith('A'):
            LOGGER.debug("Renaming array stores")
            clause, constraints = ff.rename_arrays(clause)
            LOGGER.info("Added %d new arrays" % len(constraints))
            clause = And(*constraints, clause) # Make sure to render constraints first
            ldecl_arr.extend(map(lambda c: c.args()[1],constraints))

        symbs = set()

        try:
            LOGGER.debug("Converting clause %d/%d." % (c,len(clauses)))
            result = converter.convert_to_string(symbs,clause)
        except Exception as e:
            LOGGER.warning("Could not convert clause: %s", e.with_traceback())
            if continue_on_error:
                if clause not in core:
                    continue
                parsed_cons['(1==0)'] = True if check_neg else "" # Make sure condition remains unsat
            else:
                raise e
        LOGGER.debug("Done.")

        add_parsed_cons(check_neg, clauses, parsed_cons, clause, result)
        add_used_variables(variables, ldecl_arr, symbs)

    return parsed_cons, variables, array_size

def add_parsed_cons(check_neg:bool, clauses:list, parsed_cons:OrderedDict, clause:FNode, cons_in_c: str):
    # if "model_version" not in cons_in_c:
    if check_neg == True:
        neg_sat = ff.is_neg_sat(clause, clauses)
        parsed_cons[cons_in_c] = neg_sat
    else:
        parsed_cons[cons_in_c] = ""

def add_used_variables(variables: set, ldecl_arr: t.List[FNode], symbs: t.Set[str]):
    for symb in symbs:
        decls = list(map(lambda x: converter.clean_string(x), ldecl_arr))
        if symb in decls:
            decl = symb
        elif 'c' in decls and symb == '__original_smt_name_was_c__':
            decl = 'c'
        else:
            decl = symb.split("_")[0]
        i = decls.index(decl)
        vartype = ldecl_arr[i].get_type()
        type_in_c = converter.type_to_c(vartype)
        if vartype.is_array_type():
            first_bracket = type_in_c.find('[')
            symb += type_in_c[first_bracket:]
            type_in_c = type_in_c[:first_bracket]
        variables[symb] = type_in_c

def set_well_defined(generate_well_defined: bool):
    global GENERATE_WELL_DEFINED
    GENERATE_WELL_DEFINED = generate_well_defined
    converter.set_well_defined(generate_well_defined)

def run_checks(formula: FNode, logic: str, formula_clauses: t.Set[FNode]):
    constraints = set()
    clauses = list(formula_clauses)

    if 'BV' not in logic and GENERATE_WELL_DEFINED:
        LOGGER.warning("Can only guarantee well-definedness on bitvectors")
    
    if logic.split('_')[-1].startswith('A'):
        array_size, array_constraints = ff.constrain_array_size(formula)
        if GENERATE_WELL_DEFINED:
            clauses.extend(filter(lambda c: len(c.get_free_variables()) > 0, array_constraints))
        constraints.update(array_constraints)
    else:
        array_size = -1
        array_constraints = []
    
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
    
    return clauses,array_size

def check_indices(symbol: str,maxArity: int,maxId :int, cons_in_c: str):
    if maxArity == 0:
        return set([symbol]) if symbol in cons_in_c else set()
    for id in range(maxId):
        var = symbol + '_' + str(id)
        res = set([var]) if var in cons_in_c else set()
        res = res.union(check_indices(var, maxArity-1,maxId,cons_in_c))
    return res    

def read_file(file_path: str, limit = 0) -> SmtFileData:
    parser = SmtLibParser()
    script = parser.get_script_fname(file_path)
    decl_arr = list()
    decls = script.filter_by_command_name("declare-fun")
    for d in decls:
        for arg in d.args:
            # if (str)(arg) != "model_version":
            decl_arr.append(arg)
    formula = script.get_strict_formula()
    if limit > 0:
        formula, new_decls = ff.daggify(formula, limit)
        decl_arr.extend(new_decls)
    
    logic = get_logic_from_script(script)  
    clauses = conjunction_to_clauses(formula)
    return SmtFileData(decl_arr,formula,logic,clauses)

def get_logic_from_script(script):
    if script.contains_command(SET_LOGIC):
        logic = str(script.filter_by_command_name(SET_LOGIC).__next__().args[0])
    else:
        formula = script.get_strict_formula()
        logic = str(get_logic(formula))
        LOGGER.info('Logic not found in script. Using logic from formula: '  + logic)
    return logic

def conjunction_to_clauses(formula: FNode):
    clauses = set()
    if formula.is_and():
        for node in formula.args():
            clauses = clauses.union(conjunction_to_clauses(node))
    else:
        clauses.add(formula)
    return clauses

def write_to_file(formula : FNode, file: str):
    if isinstance(formula,t.Iterable):
        formula = And(*formula)
    return write_smtlib(formula, file)


class Graph:
    def __init__(self):
        self.graph = defaultdict(list)

    def add_edge(self, node, neighbour):
        self.graph[node].append(neighbour)

    def get_edges(self, node):
        return self.graph[node]

    def separate_helper(self, node, visited: set):
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

def extract_vars(cond: t.List[str], variables: t.Dict[str,str]):    
    vars = dict()
    for var, vartype in variables.items():
        if var + " " in cond or var + ")" in cond or var.split('[')[0] in cond:
            vars[var] = vartype
    return vars

def get_negated(conds: dict, group: t.Set[str], vars: t.Dict[str,str], numb: int):
    negated_groups = list()
    new_vars = dict()
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
    elif n == 0:
        new_vars['c'] = 'signed char' # If we don't have any clauses to negate, revert to choice
        for i in range(numb):
            cond_neg = '(c %s %d)' % ('>=' if i == numb-1 else '==', i)
            negated_groups.append([cond_neg])
        return negated_groups, new_vars

    else: 
        for i in range(numb):
            new_group = set()
            # negate one of the original and add same conds for new var
            for cond in group:
                if conds[cond] == True:
                    cond_neg = "(!" + cond + ")"
                    break
            new_group.add(cond_neg)
            for j, cond in enumerate(group):
                cond_vars = sorted(list(extract_vars(cond, vars).keys()),key=len,reverse=True)
                for v in cond_vars:
                    new_var = "__neg_%d_%d__%s" % (i,j,v)
                    cond = cond.replace("(%s)" % v.split('[')[0], "(%s)" % new_var.split('[')[0])
                    new_vars[new_var] = vars[v]
                new_group.add(cond)
            negated_groups.append(new_group)
    vars.update(new_vars)
    return negated_groups, vars 

def get_subgroup(groups: t.List[set], vars_by_groups: t.List[t.Dict[str,str]], seed: int):
    if len(groups) == 0:
        return set(),dict()
    # get a subset of a randomly selected independent group
    random.seed(seed)
    rand = random.randint(0, len(groups)-1)
    vars = dict()
    subgroup = groups[rand]
    for cond in subgroup:
        vars.update(extract_vars(cond, vars_by_groups[rand]))
    return subgroup, vars

def get_minimum_array_size_from_file(smt_file: str):
    formula = read_file(smt_file).formula
    return ff.constrain_array_size(formula)[0]
