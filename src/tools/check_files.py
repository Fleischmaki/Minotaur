import os, io, logging
from src.maze_gen.smt2 import parser, formula_transforms as ff, converter
from src.maze_gen.storm.smt.smt_object import smtObject
from pysmt.shortcuts import *

LOGGER = logging.getLogger(__name__)

def check_files(file_path, resfile):
    parser.set_well_defined(False)
    if os.path.isdir(file_path):
        LOGGER.info("Going into dir %s\n" % file_path)
        for file in sorted(os.listdir(file_path)):
            check_files(os.path.join(file_path,file), resfile)
        return
    if not file_path.endswith('.smt2'):
        return
    LOGGER.info("Checking file " + file_path)
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
        if str(logic).split('_')[-1].startswith('A'):
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

    except Exception as e:
        LOGGER.warning("Error in " + file_path + ': ' + str(e))
        return
        
    f = open(resfile, 'a')
    f.write(file_path + '\n')
    f.close()
def load(argv):
    check_files(argv[0],argv[1])