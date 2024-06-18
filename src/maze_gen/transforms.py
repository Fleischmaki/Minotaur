import random
import logging
import typing as t
import math as m
import os
import subprocess
import sys
from z3 import BoolVal, And, Not

from storm.smt.smt_object import smtObject # pylint: disable=import-error
from storm.fuzzer.fuzzer import generate_mutants # pylint: disable=import-error
from storm.parameters import get_parameters_dict # pylint: disable=import-error
from storm.utils.randomness import Randomness # pylint: disable=import-error
from smt2 import z3_parser as parser, z3_formula_builder as fb, formula_operations, z3_fops as ff # pylint: disable=import-error


LOGGER = logging.getLogger(__name__)

def remove_constraints(constraints: dict, dc: int):
    """Remove dc% of constraints"""
    curr = len(constraints)
    rm = m.ceil(curr*(dc/100))
    while rm > 0:
        r = random.choice(list(constraints.keys()))
        constraints.pop(r)
        rm -= 1

def make_const(variables: dict, mc: int):
    """Make mc% of variables constant"""
    symbols = list(filter(lambda t: '[' not in t, variables.keys()))
    goal = m.ceil(len(symbols)*(mc/100))
    for _ in range(goal):
        const = symbols.pop(random.randrange(0,len(symbols)))
        variables[const] = 'const ' + variables[const]

ListAElemT = t.TypeVar('ListAElemT')
ListBElemT = t.TypeVar('ListBElemT')

def coshuffle(list_a: list[ListAElemT],list_b: list[ListBElemT]) -> tuple[list[ListAElemT], list[ListBElemT]]:
    """Shuffle two lists together, i.e. x=l1[i] and y=l2[i] <=> x=l1'[j] and y=l2'[j] for some j"""
    temp = list(zip(list_a,list_b))
    random.shuffle(temp)
    r1, r2 = zip(*temp)
    return list(r1), list(r2)

def parse_transformations(t_type: str) -> dict:
    """ Parse the transformation parameter.
    :param t_type:  the string after the -t parameter, containing the transformations separated by '_'
    :returns:       a dict containing the values for the transformations specified by 't_type' or default 
                    values if no explicit values was set.
                    In particular this means that all the keys will be set to some value, so they are
                    always safe to call.
    """
    transformations = t_type.split('_')
    shuffle = False
    storm = False
    sat = True
    init_arrays = True
    well_defined = False
    mc = 0
    keep_id = t_type == 'id'
    dc = 0
    dag = 0
    last = False
    neg = False
    ca = False
    fuzz = False
    yinyang = False
    mutator = None
    assume = False
    max_assert = max_depth = 0
    for transformation in transformations:
        if transformation == 'sh':
            shuffle = True
        elif transformation.startswith('storm'):
            storm = True
            max_assert = 20
            max_depth = 10
            if len(transformation) > 5:
                max_assert, max_depth = transformation.removeprefix("storm").split('x')
        elif transformation.startswith('fuzz'):
            fuzz = True
            max_assert = 10
            max_depth = 10
            if len(transformation) > 4:
                max_assert, max_depth = transformation.removeprefix("fuzz").split('x')
        elif transformation.startswith('yinyang'):
            yinyang = True
            mutator = transformation.split('-')[1]

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
        elif transformation == 'ca':
            ca = True
        elif transformation == 'no-init-arrays':
            init_arrays = False
    return {'sh': shuffle, 'dc': dc, 'storm' : storm, 'keepId' : keep_id, 'wd' : well_defined, 'mc' : mc, 'fuzz': fuzz, \
            'sat' : sat, 'dag': dag, 'last': last, 'neg': neg, 'ca': ca, 'max_assert': int(max_assert), 'max_depth': int(max_depth), \
            'mutator': mutator, 'yinyang': yinyang, 'init_arrays': init_arrays}

def run_yinyang(smt_file: str, mutant_path: str, seed: int, n: int, transformations) -> list[str]:
    if n <= 0:
        return []
    LOGGER.info("Building %s new assertions.", n)
    subprocess.run(f"{transformations['mutator']} -i {n*2} -ks {mutant_path} -S {seed} {'z3;echo'} {smt_file}".split(), check=False)
    mutants = []
    for i, mutant in enumerate(os.listdir(mutant_path)):
        fmutant = os.path.join(mutant_path, mutant)
        LOGGER.info("Checking sat on %s", fmutant)
        fd = parser.read_file(fmutant)
        sat = 'sat' if ff.is_sat(fd.formula) else 'unsat'
        outfile = os.path.join(mutant_path, f"mutant_{i}_{sat}.smt2")
        subprocess.run(f"mv {fmutant} {outfile}".split(), check=False)
        mutants.append(outfile)
    return mutants


def run_formula_builder(smt_file: str, mutant_path: str, seed: int, n: int, transformations) -> list[str]:
    if n <= 0:
        return []
    LOGGER.info("Building %s new assertions.", n)
    sys.setrecursionlimit(10000)
    filedata = parser.read_file(smt_file)
    if not transformations['sat']:
        core = ff.get_unsat_core(filedata.clauses)
    builder = fb.FormulaBuilder(filedata.formula, filedata.logic, Randomness(seed))
    mutants = []
    for i in range(n):
        clauses = [builder.get_random_assertion(transformations['max_depth']) for _ in range(transformations['max_assert'])]
        formula = And(*clauses) if transformations['sat'] else And(*clauses,*core)
        sat_status = 'unsat'
        if transformations['sat'] and ff.is_sat(formula):
            sat_status = 'sat'
        respath = os.path.join(mutant_path, f'mutant_{i}_{sat_status}.smt2')
        mutants.append(respath)
        parser.write_to_file(formula,filedata.logic, respath) # type:ignore
    return mutants

def run_storm(smt_file: str, mutant_path: str, seed: int, n: int, transformations: dict) -> list[str]:
    if n <= 0:
        return []
    LOGGER.info("Running Storm.")
    file_data = parser.read_file(smt_file)

    smt_obj = smtObject(smt_file, mutant_path, transformations['sat'])
    smt_obj.check_satisfiability(10*60, 'sat' if transformations['sat'] else 'unsat')
    if smt_obj.get_final_satisfiability() == "timeout":
        LOGGER.warning("Could not fuzz file: timeout.")
        if transformations['sat']:
            return [smt_file] * n
        core = {BoolVal(True)}
    elif smt_obj.get_final_satisfiability() == "sat" and not transformations['sat']:
        if not 'A' in file_data.logic:
            LOGGER.warning("Could not fuzz file: cannot generate unsat files from sat %s files.", file_data.logic)
            return [smt_file] * n
        # Try to see if we can get an unsat core from array constraints
        min_index, calls  = formula_operations.get_array_index_calls(file_data.formula)
        core = set(formula_operations.get_array_constraints(calls, min_index))
        LOGGER.info("Formula is sat, trying to build core from array constraints.")
        if ff.is_sat(And(*core,file_data.formula)):
            LOGGER.warning("Could not get core from array constraints, using trivial core.")
            core ={ BoolVal(True)}
    elif transformations['sat']:
        core = {BoolVal(True)}
    else:
        clauses = [Not(file_data.formula)] if smt_obj.orig_satisfiability != smt_obj.final_satisfiabiliy else file_data.clauses
        core = ff.get_unsat_core(clauses) # type: ignore

    fpars = get_parameters_dict(False, 0)
    fpars['number_of_mutants'] = n
    fpars['max_depth'] = transformations['max_depth']
    fpars['max_assert'] = transformations['max_assert']

    generate_mutants(smt_obj, mutant_path, fpars['max_depth'],fpars['max_assert'],seed, file_data.logic,fpars)

    mutants = [mutant_path + f'/mutant_{i}.smt2' for i in range(n)]
    if not transformations['sat']:
        for mutant in mutants:
            assertions = parser.read_file(mutant).clauses
            parser.write_to_file(core.union(assertions),file_data.logic, mutant) #type: ignore
    return mutants 