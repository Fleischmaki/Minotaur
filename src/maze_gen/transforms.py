import random,logging

from storm.smt.smt_object import smtObject
from storm.fuzzer.fuzzer import generate_mutants
from storm.parameters import get_parameters_dict
import math as m

from z3 import *
from pysmt.shortcuts import *
from smt2 import parser

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

def coshuffle(list1: list,list2: list) -> 'tuple[list, list]':
    temp = list(zip(list1,list2)) #shuffle groups and vars together
    random.shuffle(temp)
    r1, r2 = zip(*temp)
    return list(r1), list(r2)

def parse_transformations(t_type: str) -> dict:
    transformations = t_type.split('_')
    shuffle = False
    storm = False
    sat = True
    well_defined = False
    make_const = 0
    keepId = t_type == 'id'
    dc = 0
    dag = 0
    last = False
    for t in transformations:
        if t == 'sh':
            shuffle = True
        elif t == 'storm':
            storm = True
        elif t == 'wd':
            well_defined = True
        elif t.startswith('dc'):
            dc = int(t[2:])
        elif t == 'keepId':
            keepId = True
        elif t.startswith('mc'):
            make_const = int(t[2:])
        elif t == 'unsat':
            sat = False
        elif t.startswith('dag'):
            dag = int(t[3:])
        elif t == 'last':
            last = True
    return {'sh': shuffle, 'dc': dc, 'storm' : storm, 'keepId' : keepId, 'wd' : well_defined, 'mc' : make_const, 'sat' : sat, 'dag': dag, 'last': last}

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
    fpars['max_depth'] = 10 # Reduce the depth, we want simpler formulas

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