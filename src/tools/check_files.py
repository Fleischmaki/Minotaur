""" Checks SMT2-files for good potential candidates  
"""
import os
import io
import logging
from src.maze_gen.smt2 import parser, formula_transforms as ff, converter
from src.maze_gen.storm.smt.smt_object import smtObject
from pysmt.shortcuts import reset_env, is_sat, And

LOGGER = logging.getLogger(__name__)

def check_files(file_path: str, resfile: str) -> None:
    """Performs various checks on SMT2 files to see if they are valid.
    :param file_path:   Input files. If a directory, recursively check all smt2 files
                        in the directory and subdirectory.
    :param resfile:     Valid files will be written to this path
    """
    parser.set_well_defined(False)
    if os.path.isdir(file_path):
        LOGGER.info("Going into dir %s\n", file_path)
        for file in sorted(os.listdir(file_path)):
            check_files(os.path.join(file_path,file), resfile)
        return
    if not file_path.endswith('.smt2'):
        return
    LOGGER.info("Checking file %s", file_path)
    try:
        # Check that satisfiability is easily found
        # (else everything will take a long time to run)
        LOGGER.info("Check sat:")
        so = smtObject(file_path,'temp')
        so.check_satisfiability(20)
        if so.orig_satisfiability == 'timeout':
            raise ValueError('Takes too long to process')
        LOGGER.info("Done.")


        env = reset_env()
        env.enable_infix_notation = True
        #Check number of atoms
        LOGGER.info("Check atoms:")
        filedata = parser.read_file(file_path)
        formula = filedata.formula
        logic = filedata.logic
        clauses = filedata.clauses 
        if len(formula.get_atoms()) < 5:
            raise ValueError("Not enough atoms") 
        LOGGER.info("Done")


        # Check that it is satisfiable on bounded integers
        if 'IA' in str(logic):
            LOGGER.info("Check Integers:")
            if not is_sat(And(formula, *ff.get_integer_constraints(formula)),solver_name='z3'): 
                raise ValueError('Unsat in range')
            LOGGER.info("Done.")

        # Check that it is satisfiable on bounded arrays
        if str(logic).rsplit('_', maxsplit=1)[-1].startswith('A'):
            LOGGER.info("Check array size:")
            parser.get_minimum_array_size_from_file(file_path)
            LOGGER.info("Done.")


        # Check that everything is understood by the parser
        # and file doesn't get too large          
        LOGGER.info("Check parser:")
        clauses = parser.conjunction_to_clauses(formula)
        for clause in clauses:
            symbols = set()
            buffer = io.StringIO()
            converter.convert(symbols,clause, buffer) 
            print(".",end ="")
        LOGGER.info("")
        LOGGER.info("Done.")

    except (ValueError, RecursionError) as e:
        LOGGER.warning("Error in %s: %s", file_path, str(e))
        return
    with open(resfile, 'a') as f:
        f.write(file_path + '\n')

def load(argv):
    """Call via __main.py__"""
    check_files(argv[0],argv[1])
