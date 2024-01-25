import random
from storm.smt.smt_object import smtObject
from storm.fuzzer.fuzzer import generate_mutants
from storm.parameters import get_parameters_dict
import smt2_parser as s2
import math as m

from z3 import *
from pysmt.shortcuts import *


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

def coshuffle(list1: list,list2: list) -> (list, list):
    temp = list(zip(list1,list2)) #shuffle groups and vars together
    random.shuffle(temp)
    r1, r2 = zip(*temp)
    return list(r1), list(r2)

def parse_transformations(t_type: str) -> dict:
    transformations = t_type.split('_')
    shuffle = False
    storm = False
    well_defined = False
    make_const = 0
    keepId = t_type == 'id'
    dc = 0
    for t in transformations:
        if t == 'sh':
            shuffle = True
        elif t.startswith('storm'):
            storm = t[5:]
        elif t == 'wd':
            well_defined = True
        elif t.startswith('dc'):
            dc = int(t[2:])
        elif t == 'keepId':
            keepId = True
        elif t.startswith('mc'):
            make_const = int(t[2:])
    return {'sh': shuffle, 'dc': dc, 'storm' : storm, 'keepId' : keepId, 'wd' : well_defined, 'mc' : make_const}

def run_storm(smt_file: str, mutant_path: str, seed: int, n: int, generate_sat: bool = True) -> list:
    print("NOTE: Running Storm.")
    if n <= 0:
        return
    smt_obj = smtObject(smt_file, mutant_path)
    smt_obj.check_satisfiability(10*60)
    if smt_obj.orig_satisfiability == "timeout":
        print("WARNING: Could not fuzz file: timeout")
        return [smt_file] * n
    if smt_obj.orig_satisfiability == "sat" and not generate_sat:
        print("WARNING: Could not fuzz file: cannot generate unsat files from sat files")
        return [smt_file] * n
    fpars = get_parameters_dict(False, 0)
    fpars['number_of_mutants'] = n
    fpars['max_depth'] = 10 # Reduce the depth, we want simpler formulas

    # Find the logic of the formula
    file_data = s2.read_file(smt_file)
    logic = file_data.logic
    cores = list(s2.get_unsat_cores(file_data.clauses, file_data.logic))
    
    generate_mutants(smt_obj, mutant_path, fpars['max_depth'],fpars['max_assert'],seed, logic,fpars)
    mutants = [mutant_path + '/mutant_%s.smt2' % i for i in range(n)]
    if not generate_sat:
        for mutant in mutants:
            s2.write_to_file(And(random.choice(cores), *s2.read_file(mutant).clauses), mutant)
    return mutants 