import re, io
from pysmt.shortcuts import *
from pysmt.fnode import FNode
from pysmt.typing import PySMTType as node_type
import typing as t
from . import formula_transforms as ff

T = t.TypeVar('T')
def deflatten(args: t.List[T], op: t.Callable[[T,T],T]) -> T:
    x = args[0]
    for i in range(1,len(args)):
        y = args[i]
        x = op(x,y)
    return x

def error(flag: int, *info):
    if flag == 0:
        raise ValueError("ERROR: node type not recognized: ", info)
    elif flag == 1:
        raise ValueError("ERROR: nodes not supported", info)
    else:
        raise ValueError("ERROR: an unknown error occurred")

def set_well_defined(wd: Bool):
    global GENERATE_WELL_DEFINED
    GENERATE_WELL_DEFINED = wd 

def binary_to_decimal(binary: str, unsigned : bool = True) -> str:
    if len(binary) > 64:
        error(1, "BV width > 64: ",binary)
    val = str(BV(binary).constant_value() if unsigned else BV(binary).bv_signed_value())
    if len(binary) > 32:
        val += 'ULL' if unsigned else 'LL'
    return val 

def bits_to_type(num_bits: int):
    if num_bits <= 8:
        return "char"
    elif num_bits <= 16:
        return "short"
    elif num_bits <= 32:
        return "int"
    elif num_bits <= 64:
        return "long"
    else:
        error(1, "BV width > 64:", num_bits)
        
def bits_to_stype(numb_bits: int) -> str:
    return "signed " + bits_to_type(numb_bits)
def bits_to_utype(num_bits: int) -> str:
    return "unsigned " + bits_to_type(num_bits)
def has_matching_type(numb_bits: int) -> bool:
    return numb_bits in (8,16,32,64)

def is_signed(node: FNode) -> str:
    return node.is_bv_sle() or node.is_bv_slt() or node.is_bv_ashr() or node.is_bv_sext() or node.is_bv_srem() or node.is_bv_sdiv()

def write_or_convert(symbs,node,cons: 'FNode | str'):
    if type(node) is FNode:
        convert(symbs,node,cons)
    else:
        cons.write(node)

def write_signed(symbs,node: FNode,cons, text: 'FNode | str', always=True) -> str:
    width = ff.get_bv_width(node)
    scast = bits_to_stype(width)  
    if always or width in (32,64) or (len(node.args()) != 0 and (not all(map(is_signed, node.args())) or not all(map(lambda n: ff.get_bv_width(n)<=width,node.args())))):
        if not GENERATE_WELL_DEFINED or width == 64:
            cons.write('(%s) ' % (scast))
        else:
            cons.write('scast_helper(')
    write_or_convert(symbs,text,cons)
    if GENERATE_WELL_DEFINED and (always or width in (32,64) or (len(node.args()) != 0 and (not all(map(is_signed, node.args())) or not all(map(lambda n: ff.get_bv_width(n)<=width,node.args()))))):
        cons.write(', %s)') % width

def write_unsigned(symbs, node: FNode, cons, text: 'FNode | str', always=True) -> str:
    width = ff.get_bv_width(node)
    if always or width not in (32,64) or (len(node.args()) != 0 and (all(map(is_signed, node.args())) or not all(map(lambda n: ff.get_bv_width(n)<=width,node.args())))):
        cons.write(get_unsigned_cast(node))
    write_or_convert(symbs,text,cons)
    if not has_matching_type(width):
        cons.write(')')

def write_cast(symbs, node: FNode, cons, text: 'FNode | str', always=False) -> str:
    if node.get_type().is_bv_type() or (node.get_type().is_array_type() and node.get_type().elem.type().is_bv_type()) or node.is_theory_relation() and node.arg(0).get_type().is_bv_type():
        write_signed(symbs, node, cons,text, always) if is_signed(node) else write_unsigned(symbs, node, cons,text, always)
    else:
        write_or_convert(symbs,text,cons)
    
def get_unsigned_cast(node: FNode,) -> str:
    width = ff.get_bv_width(node)
    if width in (32,64) and (len(node.args()) == 0 or (not all(map(is_signed, node.args())) and all(map(lambda n: ff.get_bv_width(n)<=width,node.args())))):
        return ''
    if has_matching_type(width):
        return '(' + bits_to_utype(width) + ') '
    return '(%s) (%s & ' % (bits_to_utype(width),binary_to_decimal('1'*width))
    

def type_to_c(ntype: node_type) -> str:
    if ntype.is_int_type():
        return 'long'
    if ntype.is_bool_type():
        return 'bool'
    elif ntype.is_bv_type():
        return bits_to_utype(ntype.width)
    elif ntype.is_function_type():
        return type_to_c(ntype.return_type)
    elif ntype.is_array_type():
        if ntype.elem_type.is_array_type():
            return '%s[ARRAY_SIZE]' % type_to_c(ntype.elem_type) # otherwise store might be unsound, we can always cast afterwards
        return 'long[ARRAY_SIZE]'
    # elif type.is_string_type():
    #     return 'string'
    else:
        error(0, ntype)

def convert_helper(symbs: t.Set[str],node: FNode, cons: io.TextIOBase, op: str):
    (l, r) = node.args()
    write_cast(symbs,node,cons,l)
    cons.write(" %s " % op)
    write_cast(symbs,node,cons,r)

def check_shift_size(node: FNode) -> None:
    global GENERATE_WELL_DEFINED
    if GENERATE_WELL_DEFINED:
        (l,r) = node.args()        
        if not r.is_bv_constant() or r.constant_value() > ff.get_bv_width(node):
            error(1, "Invalid shift: ", node)

def div_helper(symbs: t.Set[str],node: FNode, cons: io.TextIOBase):
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
        cons.write(get_unsigned_cast(node))
        cons.write(helper)
        cons.write('(')
        convert(symbs,node,cons,l)
        cons.write(',')
        convert(symbs,node,cons,r)
        cons.write(',%s,)' % width)
        if not has_matching_type(width):
            cons.write(')')


    else:
        if node.is_bv_urem() or node.is_bv_srem():
            op = '%'
        else:
            op = '/'
        cons.write(get_unsigned_cast(node))
        cons.write('(')
        convert(symbs,l,cons)
        cons.write(" %s " % op)
        convert(symbs,r,cons)
        cons.write(')')
        if not has_matching_type(width):
            cons.write(')')


def convert_to_string(symbs: t.Set[str], node: FNode):
    buff = io.StringIO()
    convert(symbs, node, buff)
    lString = buff.getvalue()
    buff.close()
    return lString

def get_array_size_from_dim(dim: int):
    if dim <= 0:
        return '1'
    return ('ARRAY_SIZE*'*dim)[:-1]


def get_array_size(node: FNode):
    return get_array_size_from_dim(ff.get_array_dim(node))    

def convert(symbs: t.Set[str],node: FNode,cons: io.TextIOBase):
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
        convert_helper(symbs,node, cons, " >> ") # C >> is logical for unsigned, arithmetic for signed
    elif node.is_bv_ashr():
        check_shift_size(node)
        convert_helper(symbs,node, cons, " >> ")
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
        convert_helper(symbs,node, cons, " << ")
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
        if not (old_width < 32 and new_width == 32) and not (32 < old_width and old_width < 64 and new_width == 64):
            cons.write('(')
            cons.write(get_unsigned_cast(node))
            convert(symbs,l, cons)
            cons.write(')')
            if not has_matching_type(new_width):
                cons.write(')')
        else:
            convert(symbs, l, cons)
    elif node.is_bv_concat():
        (l,r) = node.args()
        write_unsigned(symbs,node,cons,l)
        cons.write(' << %d | ' % ff.get_bv_width(r))
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
        base = binary_to_decimal("1" + "0" * (ff.get_bv_width(s)))
        write_unsigned(symbs,node,cons,base)
        cons.write(' - ')
        write_unsigned(symbs,node,cons,s)
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
        if dim == 0:
            cons.write(get_unsigned_cast(node))
        cons.write(var)
        if dim == 0 and not has_matching_type(ff.get_bv_width(node)):
            cons.write(')')
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
            cons.write("+(%s*" % size)
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
        return("")
    cons.write(')')
    return ""

def rotate_helper(symbs: t.Set[str], node: FNode, cons: io.TextIOBase, op: str):
    (l,) = node.args()
    m = ff.get_bv_width(node)
    i = node.bv_rotation_step()
    convert(symbs,l,cons)
    cons.write('((')
    convert(symbs,l,cons)
    cons.write(' %s %s) & ((1 %s %s+1) - 1)) | (' % (op, i, op, i)) # TODO exponential blowup possible
    convert(symbs,l,cons)
    cons.write(' %s (%s-%s) )' % (op, i, m))

def clean_string(s: str):
    if s == 'c':
        return '__original_smt_name_was_c__'
    s = str(s)
    return re.sub('[^A-Za-z0-9_]+','_',s)

