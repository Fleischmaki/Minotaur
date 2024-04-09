import io
from z3 import z3
from . import converter, formula_transforms

def convert_from_str(symbs: dict,node: str,cons: io.TextIOBase):
    ast = z3.parse_smt2_string(node)[0]
    convert(symbs,z3.parse_smt2_string(node)[0],cons)
    

def convert(symbs,node, cons):
    if z3.is_to_real(node):
        fnode = converter.convert_from_str()