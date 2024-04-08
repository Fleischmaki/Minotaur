""" Implements translation from SMT Formulas to C Expressions 
"""
import re
import io
import typing as t

from pysmt.shortcuts import And, BV, Plus, Times, Or
from pysmt.fnode import FNode
from pysmt.typing import PySMTType as node_type

from . import formula_transforms as ff

T = t.TypeVar('T')
def deflatten(args: t.List[T], op: t.Callable[[T,T],T]) -> T:
    """ Deflattens functions with many parameters by applying it two at a time
    :param args: arguments of the function
    :param op: the function to apply
    """
    x = args[0]
    for i in range(1,len(args)):
        y = args[i]
        x = op(x,y)
    return x

def error(flag: int, *info):
    """ Raises an error
    :param flag: The kind of error:
        (0: node not recognized)
        (1: node not supported)
        (else: unkown)
    """
    if flag == 0:
        raise ValueError("ERROR: node type not recognized: ", info)
    if flag == 1:
        raise ValueError("ERROR: nodes not supported", info)
    raise ValueError("ERROR: an unknown error occurred")

def set_well_defined(wd: bool):
    global GENERATE_WELL_DEFINED
    GENERATE_WELL_DEFINED = wd

def binary_to_decimal(binary: str, unsigned : bool = True) -> str:
    """Takes BV in binary and translated into decimal number
    """
    if len(binary) > 64:
        error(1, "BV width > 64: ",binary)
    val = str(BV(binary).constant_value() if unsigned else BV(binary).bv_signed_value()) + 'U'
    if len(binary) > 32:
        val += 'LL'
    return val

def bits_to_type(num_bits: int) -> str: # type: ignore
    """ Returns the smallest possible type for given bits
    """
    if num_bits <= 8:
        return "char"
    if num_bits <= 16:
        return "short"
    if num_bits <= 32:
        return "int"
    if num_bits <= 64:
        return "long"
    error(1, "BV width > 64:", num_bits)

def bits_to_stype(numb_bits: int) -> str:
    """ Returns the smallest possible signed type for given bits
    """
    return "signed " + bits_to_type(numb_bits)
def bits_to_utype(num_bits: int) -> str:
    """ Returns the smallest possible unsigned type for given bits
    """
    return "unsigned " + bits_to_type(num_bits)

def has_matching_type(numb_bits: int) -> bool:
    """ Check if a C-Type exists that matches width exactly
    """
    return numb_bits in (8,16,32,64)

def is_signed(node: FNode) -> str:
    """ Check if a function needs signed arguments
    """
    return node.is_bv_sle() or node.is_bv_slt() or node.is_bv_ashr() or node.is_bv_sext() or node.is_bv_srem() or node.is_bv_sdiv()

def needs_signed_cast(node: FNode) -> bool:
    """ Checks if a node needs children to be recast. This is the case if:
        - width non-standard or < 32 (avoiding automatic upcasting)
        - is a constant or symbol or similar
        - some children (if any) are not signed
        - some children (if any) are larger
    """
    width = ff.get_bv_width(node)
    return width not in (32,64) or \
        len(node.args()) == 0 or \
        all(map(lambda n: n.is_bv_constant() or n.is_symbol(), node.args())) or \
        not all(map(is_signed, node.args())) or \
        not all(map(lambda n: ff.get_bv_width(n)<=width,filter(lambda n: n.get_type().is_bv_type(),node.args()))) 

def needs_unsigned_cast(node: FNode):
    """ Checks if a node needs children to be recast. This is the case if:
        - width non-standard or < 32 (avoiding automatic upcasting)
        - is a constant or symbol or similar
        - all children (if any) are signed
        - some children (if any) are larger
    """
    width = ff.get_bv_width(node)
    return width not in (32,64) or \
        len(node.args()) == 0 or \
        all(map(lambda n: n.is_bv_constant() or n.is_symbol(), node.args())) or \
        all(map(is_signed, node.args())) or \
        not all(map(lambda n: ff.get_bv_width(n)<=width,filter(lambda n: n.get_type().is_bv_type(),node.args())))

def write_signed(symbs,parent: FNode,cons, node: FNode, always=True):
    """ Writes a node as a signed integer
    """
    width = ff.get_bv_width(parent)
    scast = bits_to_stype(width)
    if always or needs_signed_cast(parent):
        if GENERATE_WELL_DEFINED or not has_matching_type(width):
            if width != 64:
                cons.write(f'({scast})')
            cons.write('scast_helper(')
        else:
            cons.write(f'({scast})')
    convert(symbs,node,cons)
    if not has_matching_type(width) or (GENERATE_WELL_DEFINED and (always or needs_signed_cast)):
        cons.write(f', {width})')


def write_unsigned(symbs, parent: FNode, cons, node: FNode, always=True):
    """ Writes a node as an unsigned integer
    """
    width = ff.get_bv_width(parent)
    cons.write(get_unsigned_cast(parent, always))
    convert(symbs,node,cons)
    if not has_matching_type(width):
        cons.write(')')

def write_cast(symbs, parent: FNode, cons, node: FNode, always=False):
    """ Writes a node as the type needed by the parent
    """
    if parent.get_type().is_bv_type() or (parent.get_type().is_array_type() and parent.get_type().elem.type().is_bv_type()) or parent.is_theory_relation() and parent.arg(0).get_type().is_bv_type():
        if is_signed(parent):
            write_signed(symbs, parent, cons,node, always)
        else:
            write_unsigned(symbs, parent, cons,node, always)
    else:
        convert(symbs,node,cons)


def get_unsigned_cast(node: FNode, always=False) -> str:
    """ Returns the neede cast. Need to close a bracket ) if non-standard width ist used
    """
    width = ff.get_bv_width(node)
    if not always and not needs_unsigned_cast(node):
        return ''
    if has_matching_type(width):
        return '(' + bits_to_utype(width) + ') '
    return f"({bits_to_utype(width)}) ({binary_to_decimal('1'*width)} & "

def type_to_c(ntype: node_type) -> str:
    """ Get corresponding C type for pySMT type 
    """
    if ntype.is_int_type():
        return 'long'
    if ntype.is_bool_type():
        return 'bool'
    if ntype.is_bv_type():
        return bits_to_utype(ntype.width) # type: ignore
    if ntype.is_function_type():
        return type_to_c(ntype.return_type) # type: ignore
    if ntype.is_array_type():
        if ntype.elem_type.is_array_type(): # type: ignore
            return f'{type_to_c(ntype.elem_type)}[ARRAY_SIZE]' # type: ignore
        return 'long[ARRAY_SIZE]'
    error(0, ntype)
    return ''

def convert_helper(symbs: t.Set[str],node: FNode, cons: io.TextIOBase, op: str, always_cast_args=False):
    """ Helper for normal binary convert operations
    """
    (l, r) = node.args()
    write_cast(symbs,node,cons,l, always=always_cast_args)
    cons.write(f" {op} ")
    write_cast(symbs,node,cons,r, always=always_cast_args)

def check_shift_size(node: FNode) -> None:
    """ Check if shift is valid
    :param node: Some bv-shift FNode
    Shift is valid if it is contant and that ammount <= size of the bv 
    """
    if GENERATE_WELL_DEFINED:
        (_,r) = node.args()
        if not r.is_bv_constant() or r.constant_value() > ff.get_bv_width(node):
            error(1, "Invalid shift: ", node)

def div_helper(symbs: t.Set[str],node: FNode, cons: io.TextIOBase):
    """ Converts divisons and remainders
    :param node: should be (s)rem or (s)div
    """
    (l,r) = node.args()
    width = ff.get_bv_width(node)

    if GENERATE_WELL_DEFINED:
        if node.is_bv_srem():
            helper = 'srem_helper'
        elif node.is_bv_urem():
            helper = 'rem_helper'
        elif node.is_bv_udiv():
            helper = 'div_helper'
        else:
            helper = 'sdiv_helper'
        cons.write(get_unsigned_cast(node, always=True))
        cons.write(helper)
        cons.write('(')
        write_cast(symbs,node,cons,l)
        cons.write(',')
        write_cast(symbs,node,cons,r)
        cons.write(f',{width})')
        if not has_matching_type(width):
            cons.write(')')


    else:
        if node.is_bv_urem() or node.is_bv_srem():
            op = '%'
        else:
            op = '/'
        cons.write(get_unsigned_cast(node))
        cons.write('(')
        write_cast(symbs,node,cons,l)
        cons.write(f" {op} ")
        write_cast(symbs,node,cons,r)
        cons.write(')')
        if not has_matching_type(width):
            cons.write(')')


def convert_to_string(symbs: t.Set[str], node: FNode) -> str:
    """ Convert and FNode to a string and add encountered symbols to symbs
    Usually convert() is preferred as that does not open a new buffer
    """
    buff = io.StringIO()
    convert(symbs, node, buff)
    res = buff.getvalue()
    buff.close()
    return res

def get_array_size_from_dim(dim: int) -> str:
    """ Return array_size for a given dimension 
    """
    if dim <= 0:
        return '1'
    return ('ARRAY_SIZE*'*dim)[:-1]


def get_array_size(node: FNode):
    """ Get array size from a Node
    """
    return get_array_size_from_dim(ff.get_array_dim(node))

def convert(symbs: t.Set[str],node: FNode,cons: io.TextIOBase):
    """ Converts a formula into C-expression
    :param symbs: Set into which encountered symbols (variables, arrays, functions etc.) are stored
    :param node: Root node of the formula
    :param cons: File in which to write the C expression 
    """
    if cons.tell() > 2**20:
        raise ValueError("Parse result too large") # Avoid file sizes > 1 MB
    cons.write('(')
    if node.is_iff() or node.is_equals() or node.is_bv_comp():
        (l, r) = node.args()
        if "Array" in str(l.get_type()):
            if "Array" in str(r.get_type()):
                cons.write("array_comp(")
                convert(symbs,l,cons)
                cons.write(",")
                convert(symbs,r,cons)
                cons.write(",%s))" % get_array_size(l))
                return
            error(1, "Cannot compare array with non-array", node)
        convert_helper(symbs,node, cons, " == ")
    elif node.is_int_constant():
        value = str(node.constant_value())
        if int(value) > 2**32:
            value += 'LL'
        cons.write(value)
    elif node.is_plus():
        node = deflatten(node.args(),Plus)
        convert_helper(symbs,node,cons,' + ')
    elif node.is_minus():
        convert_helper(symbs,node,cons,' - ')
    elif node.is_times():
        node = deflatten(node.args(),Times)
        convert_helper(symbs,node,cons,' * ')
    elif node.is_div():
        convert_helper(symbs,node,cons,' / ')
    elif node.is_le():
        convert_helper(symbs,node,cons,' <= ')
    elif node.is_lt():
        convert_helper(symbs,node,cons,' < ')
    elif node.is_bv_sle():
        convert_helper(symbs,node, cons, " <= ")
    elif node.is_bv_ule():
        convert_helper(symbs,node, cons, " <= ")
    elif node.is_bv_slt():
        convert_helper(symbs,node, cons, " < ")
    elif node.is_bv_ult():
        convert_helper(symbs,node, cons, " < ")
    elif node.is_bv_lshr():
        check_shift_size(node)
        convert_helper(symbs,node, cons, " >> ", True) # C >> is logical for unsigned, arithmetic for signed
    elif node.is_bv_ashr():
        check_shift_size(node)
        convert_helper(symbs,node, cons, " >> ", True) # Always need to cast for shifts, as we dont only look at left operand
    elif node.is_bv_add():
        convert_helper(symbs,node, cons, " + ") # Recast result on all operations that can exceed value ranges
    elif node.is_bv_sub():
        convert_helper(symbs,node, cons, " - ")
    elif node.is_bv_mul():
        convert_helper(symbs,node, cons, " * ")# Recast result on all operations that can exceed value ranges
    elif node.is_bv_udiv() or node.is_bv_sdiv() or node.is_bv_urem() or node.is_bv_srem():
        div_helper(symbs,node, cons)
    elif node.is_bv_xor():
        convert_helper(symbs,node, cons, " ^ ")
    elif node.is_bv_or():
        convert_helper(symbs,node, cons, " | ")
    elif node.is_bv_and():
        convert_helper(symbs,node, cons, " & ")
    elif node.is_bv_lshl():
        check_shift_size(node)
        convert_helper(symbs,node, cons, " << ", True)
    elif node.is_bv_not():
        (b,) = node.args()
        cons.write("(~")
        write_unsigned(symbs,b,cons,b)
        cons.write(")")
    elif node.is_bv_sext():
        (l,) = node.args()
        cons.write('((')
        cons.write(bits_to_utype(ff.get_bv_width(node)))
        cons.write(')')
        write_signed(symbs,l,cons,l)
        cons.write(')')
    elif node.is_bv_zext():
        new_width = ff.get_bv_width(node)
        (l,) = node.args()
        old_width = ff.get_bv_width(l)
        if not (old_width < 32 and new_width == 32) and not (32 < old_width < 64 and new_width == 64):
            cons.write('(')
            cons.write(get_unsigned_cast(node, always=True))
            write_unsigned(symbs,l, cons,l)
            cons.write(')')
            if not has_matching_type(new_width):
                cons.write(')')
        else:
            write_unsigned(symbs,l,cons,l)
    elif node.is_bv_concat():
        (l,r) = node.args()
        write_unsigned(symbs,node,cons,l)
        cons.write(f' << {ff.get_bv_width(r)} | ')
        write_unsigned(symbs,node,cons,r)        
    elif node.is_bv_extract():
        ext_start = node.bv_extract_start()
        ext_end = node.bv_extract_end()
        dif = ext_end - ext_start + 1
        (l,) = node.args()
        m = ff.get_bv_width(l)
        mask = binary_to_decimal("1" * (dif))
        newtype = bits_to_utype(dif)
        cons.write("(" + newtype +") (")
        convert(symbs,l, cons)
        cons.write(" >> " + str(ext_start))
        if ext_end != m:
            cons.write(" & " + mask)
        cons.write(")")
    elif node.is_and():
        node = deflatten(node.args(),And)
        convert_helper(symbs,node, cons, " && ")
    elif node.is_or():
        node = deflatten(node.args(),Or)
        convert_helper(symbs,node, cons, " || ")
    elif node.is_not():
        (b,) = node.args()
        cons.write("!")
        convert(symbs,b, cons)
    elif node.is_implies():
        (l,r) = node.args()
        cons.write("!")
        convert(symbs,l,cons)
        cons.write(" | ")
        convert(symbs,r,cons)
    elif node.is_ite():
        (g,p,n) = node.args()
        convert(symbs,g,cons)
        cons.write(' ? ')
        convert(symbs,p, cons)
        cons.write(' : ')
        convert(symbs,n, cons)
    elif node.is_bv_neg():
        (s,) = node.args()
        base = binary_to_decimal("1" * (ff.get_bv_width(s)))
        cons.write(f"{base}")
        cons.write(' - ')
        write_unsigned(symbs,node,cons,s)
        cons.write('+ 1U')
    elif node.is_bv_rol():
        rotate_helper(symbs, node, cons, "<<")
    elif node.is_bv_ror():
        rotate_helper(symbs, node, cons, ">>")
    elif node.is_bv_constant():
        value =  str(node.constant_value()) + 'U'
        if node.bv_width() > 32:
            value += "LL"
        cons.write(value)
    elif node.is_bool_constant():
        value =  "1" if node.is_bool_constant(True) else "0"
        cons.write(value)
    elif node.is_symbol():
        dim = ff.get_array_dim(node)
        cons.write("*"*(dim-1))
        var = clean_string(str(node))
        cons.write(f'({var})')
        symbs.add(var)
    elif node.is_select():
        (a, p) = node.args()
        if 'BV' in str(node.get_type()): 
            ucast = get_unsigned_cast(node)
            cons.write(ucast)
        dim = ff.get_array_dim(a)
        convert(symbs, a, cons)
        if dim == 1:
            cons.write("[")
            convert(symbs,p,cons)
            cons.write("]")
        else:
            size = get_array_size_from_dim(dim-1)
            cons.write(f"+({size}*")
            convert(symbs,p,cons)
            cons.write(")")
        if 'BV' in str(node.get_type()) and not has_matching_type(ff.get_bv_width(node)): 
            cons.write(')')
    elif node.is_store():
        (a, p, v) = node.args()
        a_dim = ff.get_array_dim(a)
        v_dim = ff.get_array_dim(v)
        if v_dim != (a_dim -1):
            error(1, "Invalid array dimensions for store", node)
        if v_dim == 0:
            cons.write("value_store(")
        else:
            cons.write("array_store(")
        convert(symbs, a, cons)
        cons.write(",")
        convert(symbs,p,cons)
        cons.write(",")
        convert(symbs,v,cons)
        if v_dim > 0:
            cons.write(",")
            cons.write(get_array_size_from_dim(v_dim))
        cons.write(")")
    elif node.is_function_application():
        for n in node.args():
            if not (n.is_bv_constant() or node.is_int_constant()):
                error(1, "Non-constant function call: ", node)
        index = "".join(["_" + str(n.constant_value()) for n in node.args()])
        fn = clean_string(node.function_name())
        cons.write(fn + index)
        symbs.add(fn + index)
    else:
        error(0, node.get_type())
        return ""
    cons.write(')')
    return ""

def rotate_helper(symbs: t.Set[str], node: FNode, cons: io.TextIOBase, op: str):
    """ Helper function for left and right rotates
    """
    (l,) = node.args()
    m = ff.get_bv_width(node)
    i = node.bv_rotation_step()
    convert(symbs,l,cons)
    cons.write('((')
    convert(symbs,l,cons)
    cons.write(f' {op} {i}) & ((1 {op} {i}+1) - 1)) | (') # TODO exponential blowup possible
    convert(symbs,l,cons)
    cons.write(f' {op} ({i}-{m}) )')

def clean_string(s: str | FNode):
    if s == 'c':
        return '__original_smt_name_was_c__'
    s = str(s)
    return re.sub('[^A-Za-z0-9_]+','_',s)

