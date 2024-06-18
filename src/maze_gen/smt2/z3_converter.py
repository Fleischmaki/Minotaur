import io
import logging
import typing as t
import re
from z3.z3consts import *
from z3.z3 import ExprRef, SortRef, is_app_of, is_const, is_true,is_false, is_app, is_bv_value, is_int_value, And, Or
from . import z3_fops as ff

ARRAY_SIZE_STRING = "ARRAY_SIZE"
LOGGER = logging.getLogger(__name__)

# def convert_from_str(symbs: dict,node: str,cons: io.TextIOBase):
#     ast = z3.parse_smt2_string(node)[0]
#     convert(symbs,z3.parse_smt2_string(node)[0],cons)

T = t.TypeVar('T')
def deflatten(args: t.List[T], op: t.Callable[[T,T],T]) -> T:
    """ Deflattens functions with many parameters by applying it two at a time
    :param args: arguments of the function
    :param op: the function to apply
    """
    if len(args) == 1:
        return args[0]
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
    
def binary_to_decimal(binary: str, unsigned : bool = True) -> str:
    """Takes BV in binary and translated into decimal number
    """
    if len(binary) > 64:
        error(1, "BV width > 64: ",binary)
    val = str(int(binary,2) if unsigned or not binary.startswith('1')  else str(int(binary,2)-2**len(binary)))
    if unsigned:
        val += 'U'
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

def needs_signed_children(node: ExprRef) -> bool:
    """ Check if a function needs signed arguments
    """
    return  is_app_of(node, Z3_OP_SLEQ) or is_app_of(node, Z3_OP_SLT) or \
            is_app_of(node, Z3_OP_SGEQ) or is_app_of(node, Z3_OP_SGT) or \
            is_app_of(node, Z3_OP_BSREM) or is_app_of(node, Z3_OP_BSDIV)

def needs_downcasting(node: ExprRef) -> bool:
    """ CHeck if we need to cast down after converting a node
    """
    return is_app_of(node, Z3_OP_BSDIV) or is_app_of(node, Z3_OP_BUDIV) or is_app_of(node, Z3_OP_BSREM) or is_app_of(node, Z3_OP_BUREM) \
        or is_app_of(node, Z3_OP_EXT_ROTATE_RIGHT) or is_app_of(node, Z3_OP_EXT_ROTATE_LEFT) or is_app_of(node, Z3_OP_BASHR) \
        or is_app_of(node, Z3_OP_SELECT)

def is_signed(node: ExprRef) -> bool:
    """ Check if a function needs signed arguments
    """
    return is_app_of(node,Z3_OP_SIGN_EXT) or is_app_of(node, Z3_OP_BSREM) or is_app_of(node, Z3_OP_BSDIV) or is_app_of(node, Z3_OP_SELECT) 

def needs_unsigned_cast(node: ExprRef):
    """ Checks if a node needs children to be recast. This is the case if:
        - width non-standard or < 32 (avoiding automatic upcasting)
        - is a constant or symbol or similar
        - all children (if any) are signed
        - some children (if any) are larger
        - some children are helper functions
    """
    width = ff.get_bv_width(node)
    return width not in (32,64) or \
        node.num_args() == 0 or \
        all(map(lambda n: n.num_args() == 0, node.children())) or \
        all(map(is_signed, node.children())) or \
        not all(map(lambda n: ff.get_bv_width(n)<=width,filter(lambda n: n.sort_kind() == Z3_BV_SORT,node.children()))) or \
        width == 32 and any(map(needs_downcasting, node.children()))

def get_unsigned_cast(node: ExprRef, always=False) -> str:
    """ Returns the neede cast. Need to close a bracket ) if non-standard width ist used
    """
    width = ff.get_bv_width(node)
    if not always and not needs_unsigned_cast(node):
        return ''
    if has_matching_type(width):
        return '(' + bits_to_utype(width) + ') '
    return f"({bits_to_utype(width)}) ({binary_to_decimal('1'*width)} & "

def needs_signed_cast(node: ExprRef) -> bool:
    """ Checks if a node needs children to be recast. This is the case if:
        - width non-standard or < 32 (avoiding automatic upcasting)
        - is a constant or symbol or similar
        - some children (if any) are not signed
        - some children (if any) are larger
        - some children are helper functions
    """
    width = ff.get_bv_width(node)
    return width not in (32,64) or \
        node.num_args() == 0 or \
        all(map(lambda n: n.num_args() == 0, node.children())) or \
        not all(map(is_signed, node.children())) or \
        not all(map(lambda n: ff.get_bv_width(n)<=width,filter(lambda n: n.sort_kind() == Z3_BV_SORT,node.children()))) or \
        width == 32 and any(map(lambda n: is_app_of(n, Z3_OP_BSMOD) or is_app_of(n,Z3_OP_BUREM), node.children())) or \
        width == 32 and any(map(needs_downcasting, node.children()))

def get_array_size_from_dim(dim: int) -> str:
    """ Return array_size for a given dimension 
    """
    if dim <= 0:
        return '1'
    return (f'{ARRAY_SIZE_STRING}*'*dim)[:-1]


def get_array_size(node: ExprRef):
    """ Get array size from a Node
    """
    return get_array_size_from_dim(ff.get_array_dim(node))

def clean_string(s: str | ExprRef):
    """Makes sure that the string is a valid varibale name in C"""
    s = str(s)
    if s == 'c':
        return '__original_smt_name_was_c__'
    if 'func' in s:
        s = '__' + s
    return re.sub('[^A-Za-z0-9_]+','_',s)

def type_to_c(ntype: SortRef, constant_arrays: bool = False) -> str: # type: ignore
    """ Get corresponding C type for pySMT type 
    """
    if ntype.kind() == Z3_INT_SORT:
        return 'long'
    if ntype.kind() == Z3_BOOL_SORT:
        return 'bool'
    if ntype.kind() == Z3_BV_SORT:
        return bits_to_utype(ntype.size()) # type: ignore
    if ntype.kind() == Z3_ARRAY_SORT:
        if constant_arrays:
            return type_to_c(ntype.range(), constant_arrays) #type: ignore
        if ntype.range().kind() == Z3_ARRAY_SORT: # type: ignore
            return f'{type_to_c(ntype.range())}[{ARRAY_SIZE_STRING}]' # type: ignore
        return f'long[{ARRAY_SIZE_STRING}]'
    error(0, ntype)

    
class Converter():
    """ Handles conversion of formulas
    Caches C-strings for ExprRefs so don't reset pySMT enviroment and use the same converter.
    """
    def __init__(self):
        self.well_defined = False
        self.array_indices = {}
        self.node_cache = {}
        self.symbs = {}

    def set_well_defined(self, well_defined: bool):
        """ Sets the converters well-definedness.
        If it is different from before, we have to clear the cache to ensure translations remain valid.
        """
        if well_defined != self.well_defined:
            self.well_defined = well_defined
            self.node_cache = {}
            LOGGER.debug("Well definedness changed, have to clear node cache")

    def set_array_indices(self, array_indices: dict[str,set[int]]):
        """ Sets the converters array-indices if all arrays are constant.
        If it is different from before, we have to clear the cache to ensure translations remain valid.
        """
        LOGGER.debug("Using the following indices for arrays: %s", array_indices)
        if array_indices != self.array_indices:
            self.array_indices = array_indices
            self.node_cache = {}
            LOGGER.debug("Array indices changed, have to clear node cache")

    def write_unsigned(self, parent: ExprRef, cons, node: ExprRef, always=True):
        """ Writes a node as an unsigned integer
        """
        if is_const(node) and not always:
            self.write_node(node, cons)
            return
        width = ff.get_bv_width(parent)
        if width < 32:
            cons.write(f'({bits_to_utype(32)})')
        cons.write(get_unsigned_cast(parent, always))
        self.write_node(node,cons)
        if (always or needs_unsigned_cast(parent)) and not has_matching_type(width):
            cons.write(')')

    def write_signed(self, parent: ExprRef, cons, node: ExprRef, always=True):
        """ Writes a node as a signed integer
        """
        width = ff.get_bv_width(parent)
        scast = bits_to_stype(width)
        if always or needs_signed_cast(parent):
            if self.well_defined or not has_matching_type(width):
                if width != 64:
                    cons.write(f'({scast})')
                cons.write('scast_helper(')
            else:
                cons.write(f'({scast})')
            self.write_unsigned(node,cons,node)
            if self.well_defined or not has_matching_type(width):
                cons.write(f', {width})')
        else:
            self.write_node(node,cons)

    def write_cast(self, parent: ExprRef, cons, node: ExprRef, always=False):
        """ Writes a node as the type needed by the parent
        """
        if parent.sort_kind() == Z3_BV_SORT or (parent.sort_kind() == Z3_ARRAY_SORT and parent.sort_kind().range().kind() == Z3_BV_SORT)\
              or (parent.sort_kind() == Z3_BOOL_SORT and is_app(parent) and parent.arg(0).sort_kind() == Z3_BV_SORT):
            if needs_signed_children(parent):
                self.write_signed(parent, cons,node, always)
            else:
                self.write_unsigned(parent, cons,node, always)
        else:
            self.write_node(node,cons)


    def convert_helper(self, node: ExprRef, cons: io.TextIOBase, op: str, always_cast_args=False, keep_arg_size=False):
        """ Helper for normal binary convert operations
        """
        (l, r) = (node.arg(0), node.arg(1))
        self.write_cast(l if keep_arg_size else node,cons,l, always=always_cast_args)
        cons.write(f" {op} ")
        self.write_cast(r if keep_arg_size else node,cons,r, always=always_cast_args)

    def div_helper(self,node: ExprRef, cons: io.TextIOBase):
        """ Converts divisons and remainders
        :param node: should be (s)rem or (s)div
        """
        (l, r) = (node.arg(0), node.arg(1))
        width = ff.get_bv_width(node)

        if self.well_defined:
            if is_app_of(node, Z3_OP_BSREM):
                helper = 'srem_helper'
            elif is_app_of(node, Z3_OP_BUREM):
                helper = 'rem_helper'
            elif is_app_of(node, Z3_OP_BUDIV) or is_app_of(node, Z3_OP_BSDIV):
                helper = 'div_helper'
            else:
                helper = 'sdiv_helper'
            cons.write(helper)
            cons.write('(')
            self.write_cast(node,cons,l,width != 64)
            cons.write(',')
            self.write_cast(node,cons,r,width != 64)
            cons.write(f',{width})')
            return

        if is_app_of(node, Z3_OP_BUREM) or is_app_of(node, Z3_OP_BSREM):
            op = '%'
        else:
            op = '/'
        cons.write('(')
        self.write_cast(node,cons,l)
        cons.write(f" {op} ")
        self.write_cast(node,cons,r)
        cons.write(')')

    def write_node(self, node: ExprRef, cons: io.TextIOBase):
        temp = self.symbs
        text, new_symbs = self.convert(node)
        temp.update(new_symbs)
        self.symbs = temp
        cons.write(text)

    def convert(self,node: ExprRef) -> tuple[str,dict[str, SortRef]]:
        """ Converts a formula into C-expression.
        :param node: Root node of the formula
        """
        if node.get_id() in self.node_cache:
            return self.node_cache[node.get_id()]
        cons = io.StringIO()
        self.symbs = {}
        cons.write('(')
        if is_app_of(node, Z3_OP_IFF) or is_app_of(node, Z3_OP_EQ) or is_app_of(node,Z3_OP_BCOMP):
            (l, r) = node.arg(0),node.arg(1)
            if l.sort_kind() == Z3_ARRAY_SORT:
                if r.sort_kind() == Z3_ARRAY_SORT:
                    if len(self.array_indices) == 0:
                        cons.write("array_comp(")
                        self.write_node(l,cons)
                        cons.write(",")
                        self.write_node(r,cons)
                        cons.write(f",{get_array_size(l)})")
                    else:
                        lname = ff.get_array_name(l)
                        rname = ff.get_array_name(r)
                        all_indices = self.array_indices[lname].union(self.array_indices[rname])
                        for index in all_indices:
                            self.symbs[f"{lname}_{index}"] =  l.sort()
                            self.symbs[f"{rname}_{index}"] = r.sort()
                            cons.write(f'({lname}_{index}=={rname}_{index}) && ')
                        cons.write("1")
                else:
                    error(1, "Cannot compare array with non-array", node)
            else:
                self.convert_helper(node, cons, " == ", keep_arg_size=is_app_of(node, Z3_OP_BCOMP)) 
        elif is_int_value(node) and node.sort_kind() == Z3_INT_SORT:
            value = str(node)
            if int(value) > 2**32:
                value += 'LL'
            cons.write(value)
        elif is_app_of(node, Z3_OP_ADD):
            node = deflatten(node.children(),lambda l,r: (l+r)) #type: ignore
            self.convert_helper(node,cons,' + ')
        elif is_app_of(node, Z3_OP_SUB):
            self.convert_helper(node,cons,' - ')
        elif is_app_of(node, Z3_OP_IDIV):
            self.convert_helper(node,cons,' / ')
        elif is_app_of(node, Z3_OP_MOD):
            self.convert_helper(node,cons,' % ')
        elif is_app_of(node, Z3_OP_MUL):
            node = deflatten(node.children(),lambda l,r: (l*r)) #type: ignore
            self.convert_helper(node,cons,' * ')
        elif is_app_of(node, Z3_OP_BSDIV):
            self.div_helper(node,cons)
        elif is_app_of(node, Z3_OP_LE):
            self.convert_helper(node,cons,' <= ')
        elif is_app_of(node, Z3_OP_LT):
            self.convert_helper(node,cons,' < ')
        elif is_app_of(node, Z3_OP_GE):
            self.convert_helper(node,cons,' >= ')
        elif is_app_of(node, Z3_OP_GT):
            self.convert_helper(node,cons,' > ')
        elif is_app_of(node, Z3_OP_SLEQ) or is_app_of(node, Z3_OP_ULEQ):
            self.convert_helper(node, cons, " <= ")
        elif is_app_of(node, Z3_OP_SLT) or is_app_of(node, Z3_OP_ULT):
            self.convert_helper(node, cons, " < ")
        elif is_app_of(node, Z3_OP_SGEQ) or is_app_of(node, Z3_OP_UGEQ):
            self.convert_helper(node, cons, " >= ")
        elif is_app_of(node, Z3_OP_SGT) or is_app_of(node, Z3_OP_UGT):
            self.convert_helper(node, cons, " > ")

        elif is_app_of(node, Z3_OP_BLSHR):
            self.convert_helper(node, cons, " >> ", True)
        elif is_app_of(node, Z3_OP_BASHR):
            cons.write(get_unsigned_cast(node, True))
            cons.write("ashift_helper(")
            self.write_unsigned(node, cons, node.arg(0), True)
            cons.write(",")
            self.write_unsigned(node, cons, node.arg(1), True)
            cons.write(")")
            if not has_matching_type(ff.get_bv_width(node)):
                cons.write(")")
        elif is_app_of(node, Z3_OP_BADD):
            self.convert_helper(node, cons, " + ")
        elif is_app_of(node, Z3_OP_BSUB):
            self.convert_helper(node, cons, " - ")
        elif is_app_of(node, Z3_OP_BMUL):
            self.convert_helper(node, cons, " * ")
        elif is_app_of(node, Z3_OP_BUDIV) or is_app_of(node, Z3_OP_BSDIV) or is_app_of(node, Z3_OP_BUREM) or is_app_of(node, Z3_OP_BSREM):
            self.div_helper(node,cons)
        elif is_app_of(node, Z3_OP_BXOR):
            self.convert_helper(node, cons, " ^ ")
        elif is_app_of(node, Z3_OP_BOR):
            self.convert_helper(node, cons, " | ")
        elif is_app_of(node, Z3_OP_BAND):
            self.convert_helper(node, cons, " & ")
        elif is_app_of(node, Z3_OP_BSHL):
            self.convert_helper(node, cons, " << ", True)
        elif is_app_of(node, Z3_OP_BNOT):
            b = node.arg(0)
            cons.write("(~")
            self.write_cast(node, cons, b, True)
            cons.write(")")
        elif is_app_of(node, Z3_OP_EXT_ROTATE_LEFT) or is_app_of(node, Z3_OP_EXT_ROTATE_RIGHT):
            l = node.arg(0)
            cons.write("rotate_helper(")
            self.write_unsigned(node,cons,l)
            cons.write(f",{node.arg(1)},{'1' if is_app_of(node, Z3_OP_EXT_ROTATE_LEFT) else '0'},{ff.get_bv_width(node)})")
        elif is_app_of(node,Z3_OP_SIGN_EXT):
            l = node.arg(0)
            if needs_signed_cast(node):
                cons.write('(')
                cons.write(bits_to_stype(ff.get_bv_width(node)))
                cons.write(')')
            self.write_signed(l,cons,l, True)
        elif is_app_of(node,Z3_OP_ZERO_EXT):
            new_width = ff.get_bv_width(node)
            l = node.arg(0)
            old_width = ff.get_bv_width(l)
            if not (old_width < 32 and new_width == 32) and not (32 < old_width < 64 and new_width == 64):
                cons.write('(')
                cons.write(get_unsigned_cast(node, always=True))
                self.write_unsigned(l, cons,l)
                cons.write(')')
                if not has_matching_type(new_width):
                    cons.write(')')
            else:
                self.write_unsigned(l,cons,l, True)
        elif is_app_of(node, Z3_OP_CONCAT):
            (l, r) = (node.arg(0), node.arg(1))
            self.write_unsigned(node,cons,l, True)
            cons.write(f' << {ff.get_bv_width(r)} | ')
            self.write_unsigned(r,cons,r, True)
        elif is_app_of(node, Z3_OP_EXTRACT):
            ext_start = node.params()[1]
            ext_end = node.params()[0]
            diff = ext_end - ext_start + 1 #type: ignore
            l = node.arg(0)
            m = ff.get_bv_width(l)
            mask = binary_to_decimal("1" * (diff))
            newtype = bits_to_utype(diff)
            cons.write("(" + newtype +") (")
            self.write_unsigned(l,cons,l, True)
            cons.write(" >> " + str(ext_start))
            if ext_end != m:
                cons.write(" & " + mask)
            cons.write(")")
        elif is_app_of(node, Z3_OP_AND):
            node = deflatten(node.children(),And) # type: ignore
            self.convert_helper(node, cons, " && ")
        elif is_app_of(node, Z3_OP_OR):
            node = deflatten(node.children(),Or) # type: ignore
            self.convert_helper(node, cons, " || ")
        elif is_app_of(node, Z3_OP_NOT):
            b = node.arg(0)
            cons.write("!")
            self.write_node(b,cons)
        elif is_app_of(node, Z3_OP_IMPLIES):
            (l, r) = (node.arg(0), node.arg(1))
            cons.write("!")
            self.write_node(l,cons)
            cons.write(" | ")
            self.write_node(r,cons)
        elif is_app_of(node, Z3_OP_XOR):
            (l, r) = (node.arg(0), node.arg(1))
            cons.write("(!")
            self.write_node(l,cons)
            cons.write(" && ")
            self.write_node(r,cons)
            cons.write(") || (")
            self.write_node(l,cons)
            cons.write(" && !")
            self.write_node(r,cons)
            cons.write(")")
        elif is_app_of(node, Z3_OP_ITE):
            (g,p,n) = (node.arg(0), node.arg(1), node.arg(2))
            self.write_node(g,cons)
            cons.write(' ? ')
            self.write_node(p,cons)
            cons.write(' : ')
            self.write_node(n,cons)
        elif is_app_of(node, Z3_OP_BNEG):
            s = node.arg(0)
            base = binary_to_decimal("1" * (ff.get_bv_width(s)))
            cons.write(f"{base}")
            cons.write(' - ')
            self.write_unsigned(node,cons,s)
            cons.write('+ 1U')
        elif is_bv_value(node):
            value =  str(node) + 'U'
            if node.size() > 32: # type: ignore
                value += "LL"
            cons.write(value)
        elif is_true(node) or is_false(node):            
            value =  "1" if is_true(node) else "0"
            cons.write(value)
        elif is_const(node):
            dim = ff.get_array_dim(node)
            if dim >= 1:
                cons.write("(long *)")
            var = clean_string(str(node))
            if dim == 0 and node.sort_kind() == Z3_BV_SORT and not has_matching_type(ff.get_bv_width(node)):
                cons.write(get_unsigned_cast(node, always=True))
            cons.write(f'({var})')
            if dim == 0 and node.sort_kind() == Z3_BV_SORT and not has_matching_type(ff.get_bv_width(node)):
                cons.write(')')
            self.symbs[var] = node.sort()
        elif is_app_of(node, Z3_OP_SELECT):
            (a, p) = node.children()
            dim = ff.get_array_dim(a)
            if node.sort_kind() == Z3_BV_SORT:
                ucast = get_unsigned_cast(node)
                cons.write(ucast)
            if len(self.array_indices) > 0:
                array_name = f'{clean_string(ff.get_array_name(a))}_{p}'
                cons.write(array_name)
                self.symbs[array_name] = a.sort()
            else:
                cons.write('(')
                self.write_node(a,cons)
                if dim == 1:
                    cons.write("[")
                    self.write_unsigned(p,cons,p)
                    cons.write("]")
                else:
                    size = get_array_size_from_dim(dim-1)
                    cons.write(f"+({size}*")
                    self.write_unsigned(p,cons,p)
                    cons.write(")")
                cons.write(")")
            if 'BV' in str(node.sort_kind()) and not has_matching_type(ff.get_bv_width(node)) and needs_unsigned_cast(node):
                cons.write(")")
        elif is_app_of(node, Z3_OP_STORE):
            (a, p, v) = node.children()
            a_dim = ff.get_array_dim(a)
            v_dim = ff.get_array_dim(v)
            if v_dim != (a_dim -1):
                error(1, "Invalid array dimensions for store", node)
            if v_dim == 0 or len(self.array_indices) > 0:
                cons.write("value_store(")
            else:
                cons.write("array_store(")
            if len(self.array_indices) > 0:
                array_name = f'{clean_string(ff.get_array_name(a))}_{p}'
                cons.write(array_name)
                self.symbs[array_name] = node.sort()
                cons.write(',')
            else:
                self.write_node(a,cons)
                cons.write(",")
            self.write_unsigned(p,cons,p)
            cons.write(",")
            if v_dim == 0:
                self.write_signed(a,cons,v)
            else:
                self.write_node(v, cons)
                cons.write(",")
                cons.write(get_array_size_from_dim(v_dim))
            cons.write(")")
        elif is_app_of(node, Z3_OP_UNINTERPRETED):
            for n in node.children():
                if not ((is_const(n) and n.sort_kind() == Z3_BV_SORT) or (is_const(node) and node.sort_kind() == Z3_INT_SORT)):
                    error(1, "Non-constant function call: ", node)
            index = "".join(["_" + str(n) for n in node.children()])
            fn = clean_string(node.decl().name())
            cons.write(fn + index)
            self.symbs[fn + index] = node.sort()
        else:
            error(0, node.decl().kind())
            return "", {}
        cons.write(')')
        cons.seek(0)
        node_in_c = cons.read()
        self.node_cache[node.get_id()] = (node_in_c,self.symbs)
        cons.close()
        return node_in_c, self.symbs

CONVERTER = Converter()

def get_converter() -> Converter:
    """Use converter as a singleton, so we can reuse the cache"""
    return CONVERTER
