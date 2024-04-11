""" Checks SMT2-files for good potential candidates  
"""
import os
import io
import logging
from src.maze_gen.smt2 import parser, formula_transforms as ff, converter
from src.maze_gen.storm.smt.smt_object import smtObject
from pysmt.shortcuts import reset_env, is_sat, And, Not

LOGGER = logging.getLogger(__name__)

def check_files(file_path: str, resfile: str, sat: str) -> None:
    """Performs various checks on SMT2 files to see if they are valid.
    :param file_path:   Input files. If a directory, recursively check all smt2 files
                        in the directory and subdirectory.
    :param resfile:     Valid files will be written to this path
    """
    parser.set_well_defined(False)
    if os.path.isdir(file_path):
        LOGGER.info("Going into dir %s\n", file_path)
        for file in sorted(os.listdir(file_path)):
            check_files(os.path.join(file_path,file), resfile, sat)
        return
    if not file_path.endswith('.smt2'):
        return
    LOGGER.info("Checking file %s", file_path)
    try:
        env = reset_env()
        env.enable_infix_notation = True
        #Check number of atoms
        LOGGER.info("Check atoms:")
        filedata = parser.read_file(file_path)
        logic = filedata.logic
        clauses = filedata.clauses
        if len(filedata.formula.get_atoms()) < 5:
            raise ValueError("Not enough atoms")
        LOGGER.info("Done")

        # Check that satisfiability is easily found
        # (else everything will take a long time to run)
        LOGGER.info("Check sat:")
        so = smtObject(file_path,'temp')
        so.check_satisfiability(20, sat)
        if so.get_final_satisfiability() == "timeout":
            raise ValueError('Takes too long to process')
        if so.get_final_satisfiability() != sat:
            raise ValueError(f"Can't generate {sat} file from this")
        LOGGER.info("Done.")

        formula = filedata.formula if not so.valid else Not(filedata.formula)

        # Check that it is satisfiable on bounded integers
        if 'IA' in str(logic):
            LOGGER.info("Check Integers:")
            if not is_sat(And(formula, *ff.get_integer_constraints(formula)),solver_name='z3'):
                raise ValueError('Unsat in range')
            LOGGER.info("Done.")

        arrays_constant = False
        # Check that it is satisfiable on bounded arrays
        if str(logic).rsplit('_', maxsplit=1)[-1].startswith('A'):
            LOGGER.info("Check array size:")
            arrays_constant = parser.get_minimum_array_size_from_file(file_path)[2]
            LOGGER.info("Done.")

        converter.set_arrays_constant(arrays_constant)

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
    check_files(argv[0],argv[1],argv[2])
