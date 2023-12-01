import random
from storm.smt.smt_object import smtObject
from storm.fuzzer.fuzzer import generate_mutants
from storm.parameters import get_parameters_dict
import math as m

from z3 import *
from pysmt.smtlib.parser import SmtLibParser
from pysmt.shortcuts import *
from pysmt.smtlib.commands import SET_LOGIC
from pysmt.oracles import get_logic


def remove_constraints(constraints, dc):
    curr = len(constraints)
    rm = m.ceil(curr*(dc/100)) 
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

    # Find the logic of the formula
    parser = SmtLibParser()
    script = parser.get_script_fname(smt_file)
    if script.contains_command(SET_LOGIC):
        logic = str(script.filter_by_command_name(SET_LOGIC).__next__().args[0])
        print('Found Logic: %s' % str(logic))
    else:
        formula = script.get_strict_formula()
        logic = str(get_logic(formula))
        print('Logic not found in script. Using logic from formula: ' % (logic))

    generate_mutants(smt_obj, mutant_path, fpars['max_depth'],fpars['max_assert'],seed, logic,fpars)
    return [mutant_path + '/mutant_%s.smt2' % i for i in range(n)]