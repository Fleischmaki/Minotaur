import random
import logging
import typing as t
import math as m

from pysmt.shortcuts import And, TRUE

from storm.smt.smt_object import smtObject # pylint: disable=import-error
from storm.fuzzer.fuzzer import generate_mutants # pylint: disable=import-error
from storm.parameters import get_parameters_dict # pylint: disable=import-error
from smt2 import parser # pylint: disable=import-error



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
    for transformation in transformations:
        if transformation == 'sh':
            shuffle = True
        elif transformation == 'storm':
            storm = True
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
    return {'sh': shuffle, 'dc': dc, 'storm' : storm, 'keepId' : keep_id, 'wd' : well_defined, 'mc' : mc, 'sat' : sat, 'dag': dag, 'last': last, 'neg': neg}

def run_storm(smt_file: str, mutant_path: str, seed: int, n: int, generate_sat: bool = True) -> list:
    LOGGER.info("Running Storm.")
    if n <= 0:
        return []
    smt_obj = smtObject(smt_file, mutant_path, generate_sat)
    smt_obj.check_satisfiability(10*60)
    if smt_obj.orig_satisfiability == "timeout":
        LOGGER.warning("Could not fuzz file: timeout")
        return [smt_file] * n
    if smt_obj.orig_satisfiability == "sat" and not generate_sat:
        LOGGER.warning("Could not fuzz file: cannot generate unsat files from sat files")
        return [smt_file] * n
    fpars = get_parameters_dict(False, 0)
    fpars['number_of_mutants'] = n
    fpars['max_depth'] = 5 # Reduce the depth, we want simpler formulas

    # Find the logic of the formula
    file_data = parser.read_file(smt_file)
    logic = file_data.logic
    core = TRUE if generate_sat else And(*parser.get_unsat_core(file_data.clauses, file_data.logic))
    
    generate_mutants(smt_obj, mutant_path, fpars['max_depth'],fpars['max_assert'],seed, logic,fpars)
    mutants = [mutant_path + '/mutant_%s.smt2' % i for i in range(n)]
    if not generate_sat:
        for mutant in mutants:
            assertions = parser.read_file(mutant).formula
            parser.write_to_file(And(core,assertions), mutant)
    return mutants 