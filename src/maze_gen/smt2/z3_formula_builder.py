""" Build self.random smt formulas from scratch or using given subexpressions
"""
from typing import FrozenSet, Callable
from logging import getLogger

from z3 import z3
from z3 import z3consts


from storm.utils.randomness import Randomness # pylint: disable=import-error

from  . import z3_fops as formula_operations


def eq(x,y):
    return x == y

UNARY_BOOL_OPS = frozenset([z3.Not])
BINARY_BOOL_OPS = frozenset([z3.Implies, z3.And, z3.Or, z3.Xor, eq])

BINARY_IA_OPS = frozenset([lambda x,y: x+y, lambda x,y: x-y, lambda x,y: x*y, lambda x,y: x/y, lambda x,y: x/y])
IA_RELATIONS = frozenset([lambda x,y: x<y, lambda x,y: x<=y, lambda x,y: x>y, lambda x,y: x>=y])


UNARY_BV_OPS = frozenset([lambda x: ~x, lambda x: -x, z3.RotateLeft,z3.RotateRight])
BV_SHIFTS = frozenset([lambda x,y: x << y, lambda x,y: x >> y, z3.LShR])
BINARY_BV_OPS = frozenset([lambda x,y: x&y, lambda x,y: x|y, lambda x,y: x^y]+list(BINARY_IA_OPS)+list(BV_SHIFTS))
OTHER_BV_OPS = frozenset([z3.ZeroExt, z3.SignExt, z3.Extract, z3.Concat])
BV_RELATIONS = frozenset([z3.ULE,z3.ULT,z3.UGT,z3.UGE] + list(IA_RELATIONS))


ARRAY_OPERATORS = frozenset([z3.Select, z3.Store])

LOGGER = getLogger(__name__)

def get_constants_for_type(node_type: z3.SortRef,is_index_or_shift: bool=False) -> set[z3.ExprRef] | FrozenSet[z3.ExprRef]:
    """Returns interesting constants of type node_type"""
    if node_type.kind() == z3consts.Z3_BOOL_SORT:
        return frozenset([z3.BoolVal(True), z3.BoolVal(False)])
    if node_type.kind() == z3consts.Z3_INT_SORT:
        return frozenset([z3.IntVal(0), z3.IntVal(1)])
    if node_type.kind() == z3consts.Z3_BV_SORT:
        width = node_type.size() # type: ignore
        if is_index_or_shift:
            return set([z3.BitVecVal(0,width), z3.BitVecVal(1,width)])
        return set([z3.BitVecVal(0,width), z3.BitVecVal(1,width), z3.BitVecVal(2**width - 1, width), z3.BitVecVal(2**(width-1), width)])
    return set()

class FormulaBuilder():
    """Builds random formulas using subexpressions from a given seed formula
    :param formula: Seeds formula
    :param logic: The logic to use for the built formula
    :param rand: A source of randomness
    """
    def __init__(self, formula: z3.ExprRef, logic: str, rand: Randomness):
        self.variables_by_type = {}
        for variable in formula_operations.get_nodes(formula, lambda _: True):
            node_type = variable.sort()
            if variable.sort() not in self.variables_by_type:
                self.variables_by_type[node_type] = set()
            self.variables_by_type[node_type].add(variable)
        self.logic = logic
        self.bvs = set(filter(lambda t: t.kind() == z3consts.Z3_BV_SORT and t.size() <= 64, self.variables_by_type.keys()))
        if 'BV' in logic and len(self.bvs) == 0:
            LOGGER.warning("No valid bv z3consts in seed!")
        self.variables_depths = formula_operations.label_formula_depth(formula)
        self.random = rand
        self.arrays = set(filter(lambda t: t.kind() == z3consts.Z3_ARRAY_SORT, self.variables_by_type.keys()))
        
    def get_random_assertion(self, max_depth: int):
        """ Build a random boolean formulas of maximum depth 
        """
        res = self.build_formula_of_type(z3.BoolSort(), max_depth)
        return res

    def build_formula_of_type(self, node_type: z3.SortRef, max_depth: int, is_index_or_shift: bool = False) -> z3.ExprRef:
        """ Build a random formula of the given type and depth """
        if max_depth == 0:
            return self.random.random_choice(self.get_leaves_for_type(node_type, max_depth, is_index_or_shift))
        res = self.random.random_choice(self.get_ops_for_outtype(node_type)\
            + self.get_leaves_for_type(node_type, max_depth, is_index_or_shift))
        
        if isinstance(res, z3.ExprRef):
            return res
        next_operation, subs_needed = res
        node_args = tuple(self.build_formula_of_type(t, max_depth-1, \
                                                    i == 1 and (next_operation in ARRAY_OPERATORS or next_operation in BV_SHIFTS)) \
                                                                for i, t in enumerate(subs_needed))
        payload = self.get_payload_for_op(next_operation, node_type, subs_needed)
        return next_operation(*payload,*node_args) if has_params_first(next_operation) else next_operation(*node_args,*payload)
    
    def get_ops_for_outtype(self, out_type: z3.SortRef) -> list[tuple[int,list[int]]]:
        """ Returns all possible supported operations for a given SMT-Node Type
            BV Types are restrained to those present in the seed formula
            Only arrays declared in the seed are used, i.e. no new Arrays are created.
        """
        res = []
        if out_type.kind() == z3consts.Z3_BOOL_SORT:
            res.append((z3.Not,[z3.BoolSort()]))
            res.extend([(o,[z3.BoolSort(), z3.BoolSort()]) for o in BINARY_BOOL_OPS])
            if ('BV' in self.logic):
                res.extend([(o,[t,t]) for o in BV_RELATIONS for t in self.bvs])
                res.extend([(eq,[t,t]) for t in self.bvs])
            if ('IA' in self.logic):
                res.extend([(o,[z3.IntSort(),z3.IntSort()]) for o in IA_RELATIONS])
                res.append((eq,[z3.IntSort(),z3.IntSort()]))

        if out_type.kind() == z3consts.Z3_BV_SORT:
            res.extend([(o,[out_type]) for o in UNARY_BV_OPS])
            res.extend([(o,[out_type, out_type]) for o in BINARY_BV_OPS])
            # Size changing z3consts:
            res.extend([(o,[smaller_type]) for o in (z3.SignExt,z3.ZeroExt) \
                        for smaller_type in filter(lambda st: st.size() < out_type.size(), self.bvs)]) #type: ignore
            res.extend([(z3.Extract,[larger_type]) \
                        for larger_type in filter(lambda st: st.size() > out_type.size(), self.bvs)]) #type: ignore
            for type1 in self.bvs:
                for type2 in self.bvs:
                    if type1.size() + type2.size() == out_type.size(): #type: ignore
                        res.append((z3.Concat,[type1,type2]))

        if out_type.kind() == z3consts.Z3_INT_SORT:
            res.extend([(o,[z3.IntSort(), z3.IntSort()]) for o in BINARY_IA_OPS])

        if 'ABV' in self.logic or 'AL' in self.logic or 'AN' in self.logic:
            arrays_for_out_type = set(filter(lambda at: at.range() == out_type, self.arrays))
            if len(arrays_for_out_type) > 0:
                res.extend([(z3.Select,[at, at.domain()]) for at in arrays_for_out_type])
                if out_type.kind() == z3consts.Z3_BOOL_SORT:
                    res.extend([(eq,[at,at]) for at in self.arrays])
                if out_type.kind() == z3consts.Z3_ARRAY_SORT:
                    res.append((z3.Store,[out_type,out_type.domain(),out_type.range()])) #type: ignore
        return res
    
    def get_leaves_for_type(self,node_type: z3.SortRef, maximum_depth: int, is_index_or_shift: bool = False) -> list[z3.ExprRef]:
        """ Get constants or subexpressions so we don't need to generate subformulas 
        """
        res = list(get_constants_for_type(node_type, is_index_or_shift))
        if node_type in self.variables_by_type:
            res.extend(filter(lambda v: self.variables_depths[v] <= maximum_depth, self.variables_by_type[node_type]))
        if len(res) > 0:
            return res
        return list(self.variables_by_type[node_type])

    def get_payload_for_op(self,op: Callable, node_type: z3.SortRef, args: list[z3.SortRef]):
        """ Returns the necessary additional information pySMT needs to create a node """
        if op in (z3.ZeroExt, z3.SignExt):
            return (node_type.size()-args[0].size(),) #type: ignore
        if op == z3.Extract: # pylint: disable=W0143
            diff = args[0].size() - node_type.size()#type: ignore
            offset = self.random.get_random_integer(0,diff) # type: ignore #
            return ( node_type.size()+offset-1,offset) #type: ignore
        if op in (z3.RotateLeft, z3.RotateRight):
            return (self.random.get_random_integer(0,node_type.size()-1),) #type: ignore
        return []

def has_params_first(op: Callable):
    return op in (z3.SignExt, z3.ZeroExt, z3.Extract)
