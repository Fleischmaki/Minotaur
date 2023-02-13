import random
from storm.smt.smt_object import smtObject
from storm.fuzzer.fuzzer import generate_mutants
from storm.parameters import get_parameters_dict
import os
from z3 import *

def remove_constraints(constraints, dc):
    curr = len(constraints)
    rm = int(curr*(dc/100)) 
    while rm > 0:
        r = random.choice(list(constraints.keys()))
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
    dc = 0
    for t in transformations:
        if t == 'sh':
            shuffle = True
        elif t == 'storm':
            storm = True
        elif t.startswith('dc'):
            dc = int(t[2:])
    return {'sh': shuffle, 'dc': dc, 'storm' : storm}

def run_storm(smt_file,output_dir, seed,n):
    MUTANT_PATH=os.path.join(output_dir,'smt')
    smt_obj = smtObject(smt_file, MUTANT_PATH)
    smt_obj.check_satisfiability(15*60)
    fpars = get_parameters_dict(False, 0)
    fpars['number_of_mutants'] = n
    fpars['max_assert'] = 1 #Fuzzle expects only 1 assertion 
    generate_mutants(smt_obj, MUTANT_PATH, fpars['max_depth'],fpars['max_assert'],seed, 'QF_AUFBV',fpars)
    return [MUTANT_PATH + '/mutant_%s.smt2' % i for i in range(n)]