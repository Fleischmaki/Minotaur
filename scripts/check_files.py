import os, io
from src.maze_gen.smt2 import parser, formula_transforms as ff, converter
from src.maze_gen.storm.smt.smt_object import smtObject
from pysmt.shortcuts import *

def check_files(file_path, resfile):
    parser.set_well_defined(False)
    if os.path.isdir(file_path):
        print("Going into dir %s\n" % file_path)
        for file in sorted(os.listdir(file_path)):
            check_files(os.path.join(file_path,file), resfile)
        return
    if not file_path.endswith('.smt2'):
        return
    print("Checking file " + file_path)
    try:
        # Check that satisfiability is easily found
        # (else everything will take a long time to run)
        print("[*] Check sat:")
        so = smtObject(file_path,'temp')
        so.check_satisfiability(20)
        if so.orig_satisfiability == 'timeout':
            raise ValueError('Takes too long to process')
        print("[*] Done.")


        env = reset_env()
        env.enable_infix_notation = True
        #Check number of atoms
        print("[*] Check atoms:")
        filedata = parser.read_file(file_path)
        formula = filedata.formula
        logic = filedata.logic
        clauses = filedata.clauses 
        if len(formula.get_atoms()) < 5:
            raise ValueError("Not enough atoms") 
        print("[*] Done")


        # Check that it is satisfiable on bounded integers
        if 'IA' in str(logic):
            print("[*] Check Integers:")
            if not is_sat(And(formula, *ff.get_integer_constraints(formula)),solver_name='z3'): 
                raise ValueError('Unsat in range')
            print("[*] Done.")

        # Check that it is satisfiable on bounded arrays
        if str(logic).split('_')[-1].startswith('A'):
            print("[*] Check array size:")
            ff.get_minimum_array_size_from_file(file_path)
            print("[*] Done.")


        # Check that everything is understood by the parser
        # and file doesn't get too large          
        print("[*] Check parser:")
        clauses = ff.conjunction_to_clauses(formula)
        for clause in clauses:
            symbols = set()
            buffer = io.StringIO()
            converter.convert(symbols,clause, buffer) 
            print(".",end ="")
        print("")
        print("[*] Done.")

    except Exception as e:
        print("Error in " + file_path + ': ' + str(e))
        return
        
    f = open(resfile, 'a')
    f.write(file_path + '\n')
    f.close()
