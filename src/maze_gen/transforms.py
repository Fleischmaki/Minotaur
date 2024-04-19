import random
import logging
import typing as t
import math as m

from pysmt.shortcuts import And, TRUE, Not, is_sat, FALSE

from storm.utils.randomness import Randomness # pylint: disable=import-error
from storm.smt.smt_object import smtObject # pylint: disable=import-error
from storm.fuzzer.fuzzer import generate_mutants # pylint: disable=import-error
from storm.parameters import get_parameters_dict # pylint: disable=import-error
from smt2 import parser, formula_builder as fb, formula_operations # pylint: disable=import-error


LOGGER = logging.getLogger(__name__)

def remove_constraints(constraints: dict, dc: int):
    curr = len(constraints)
    rm = m.ceil(curr*(dc/100))
    while rm > 0:
        r = random.choice(list(constraints.keys()))
        constraints.pop(r)
        rm -= 1

def make_const(variables: dict, mc: int):
    symbols = list(filter(lambda t: '[' not in t, variables.keys()))
    goal = m.ceil(len(symbols)*(mc/100))
    for _ in range(goal):
        const = symbols.pop(random.randrange(0,len(symbols)))
        variables[const] = 'const ' + variables[const]

ListAElemT = t.TypeVar('ListAElemT')
ListBElemT = t.TypeVar('ListBElemT')

def coshuffle(list_a: list[ListAElemT],list_b: list[ListBElemT]) -> tuple[list[ListAElemT], list[ListBElemT]]:
    temp = list(zip(list_a,list_b)) #shuffle groups and vars together
    random.shuffle(temp)
    r1, r2 = zip(*temp)
    return list(r1), list(r2)

def parse_transformations(t_type: str) -> dict:
    transformations = t_type.split('_')
    shuffle = False
    storm = False
    sat = True
    well_defined = False
    mc = 0
    keep_id = t_type == 'id'
    dc = 0
    dag = 0
    last = False
    neg = False
    ca = False
    max_assert = max_depth = 0
    for transformation in transformations:
        if transformation == 'sh':
            shuffle = True
        elif transformation.startswith('storm'):
            storm = True
            max_assert = 5
            max_depth = 10
            if len(transformation) > 5:
                max_assert, max_depth = transformation.removeprefix("storm").split('x')   
        elif transformation == 'wd':
            well_defined = True
        elif transformation.startswith('dc'):
            dc = int(transformation[2:])
        elif transformation == 'keepId':
            keep_id = True
        elif transformation.startswith('mc'):
            mc = int(transformation[2:])
        elif transformation == 'unsat':
            sat = False
        elif transformation.startswith('dag'):
            dag = int(transformation[3:])
        elif transformation == 'last':
            last = True
        elif transformation == 'neg':
            neg = True
        elif transformation == 'neg':
            ca = True
    return {'sh': shuffle, 'dc': dc, 'storm' : storm, 'keepId' : keep_id, 'wd' : well_defined, 'mc' : mc, \
            'sat' : sat, 'dag': dag, 'last': last, 'neg': neg, 'ca': ca, 'max_assert': max_assert, 'max_depth': max_depth}

def run_storm(smt_file: str, mutant_path: str, seed: int, n: int, generate_sat: bool = True) -> list:
    if n <= 0:
        return []
    LOGGER.info("Running Storm.")
    file_data = parser.read_file(smt_file)

    smt_obj = smtObject(smt_file, mutant_path, generate_sat)
    smt_obj.check_satisfiability(10*60, 'sat' if generate_sat else 'unsat')
    if smt_obj.get_final_satisfiability() == "timeout":
        LOGGER.warning("Could not fuzz file: timeout.")
        if generate_sat:
            return [smt_file] * n
        core = FALSE
    elif smt_obj.get_final_satisfiability() == "sat" and not generate_sat:
        if not 'A' in file_data.logic:
            LOGGER.warning("Could not fuzz file: cannot generate unsat files from sat %s files.", file_data.logic)
            return [smt_file] * n
        # Try to see if we can get an unsat core from array constraints
        min_index, calls  = formula_operations.get_array_index_calls(file_data.formula)
        core = And(formula_operations.get_array_constraints(calls, min_index))
        LOGGER.info("Formula is sat, trying to build core from array constraints.")
        if is_sat(And(core,file_data.formula),solver_name='z3',logic=file_data.logic):
            LOGGER.warning("Could not get core from array constraints, using trivial core.")
            core = FALSE
    elif generate_sat:
        core = TRUE
    else:
        clauses = [Not(file_data.formula)] if smt_obj.orig_satisfiability != smt_obj.final_satisfiabiliy else file_data.clauses
        core = And(*parser.get_unsat_core(clauses, file_data.logic))

    fpars = get_parameters_dict(False, 0)
    fpars['number_of_mutants'] = n
    fpars['max_depth'] = 10 # Reduce the depth, we want simpler formulas
    fpars['max_assert'] = 10

    # Find the logic of the formula

    if generate_sat:
        generate_mutants(smt_obj, mutant_path, fpars['max_depth'],fpars['max_assert'],seed, file_data.logic,fpars)

    mutants = [mutant_path + f'/mutant_{i}.smt2' for i in range(n)]
    if not generate_sat:
        rand = Randomness(seed) # Need to set the seed once for all mutants
        for mutant in mutants:
            builder = fb.FormulaBuilder(file_data.formula, file_data.logic, rand)
            assertions = [builder.get_random_assertion(fpars['max_depth']) for _ in range(fpars['max_assert'])]
            parser.write_to_file(And(*assertions, core), mutant)
    return mutants 