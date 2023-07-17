import random
from storm.smt.smt_object import smtObject
from storm.fuzzer.fuzzer import generate_mutants
from storm.parameters import get_parameters_dict
import math as m
import smt2_parser as sp

from z3 import *
from pysmt.smtlib.parser import SmtLibParser
from pysmt.shortcuts import *
from pysmt.typing import *
from pysmt.smtlib.solver import *

def remove_constraints(constraints, dc):
    curr = len(constraints)
    rm = m.ceil(curr*(dc/100)) 
    #random.shuffle(constraints)
    while rm > 0:
        r = list(constraints.keys())[0]
        constraints.pop(r)
        rm -= 1

def coshuffle(list1,list2):
    temp = list(zip(list1,list2)) #shuffle groups and vars together
    random.shuffle(temp)
    r1, r2 = zip(*temp)
    return list(r1), list(r2)

def parse_transformations(t_type):
    transformations = t_type.split('_')
    shuffle = False
    storm = False
    keepId = t_type == 'id'
    dc = 0
    for t in transformations:
        if t == 'sh':
            shuffle = True
        elif t == 'storm':
            storm = True
        elif t.startswith('dc'):
            dc = int(t[2:])
        elif t == 'keepId':
            keepId = True
    return {'sh': shuffle, 'dc': dc, 'storm' : storm, 'keepId' : keepId}

def run_storm(smt_file,mutant_path, seed,n):
    if n <= 0:
        return
    smt_obj = smtObject(smt_file, mutant_path)
    smt_obj.check_satisfiability(10*60)
    if smt_obj.orig_satisfiability == "timeout":
        return [smt_file] * n
    fpars = get_parameters_dict(False, 0)
    fpars['number_of_mutants'] = n
    fpars['max_depth'] = 10 # Reduce the depth, we want simpler formulas
    generate_mutants(smt_obj, mutant_path, fpars['max_depth'],fpars['max_assert'],seed, 'QF_AUFBV',fpars)
    return [mutant_path + '/mutant_%s.smt2' % i for i in range(n)]