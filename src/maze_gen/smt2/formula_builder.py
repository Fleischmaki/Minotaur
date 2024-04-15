""" Build self.random smt formulas from scratch or using given subexpressions
"""
from typing import FrozenSet
from pysmt.fnode import FNode
import pysmt.operators as ops
import pysmt.typing as types
import pysmt.shortcuts as sc
from pysmt.shortcuts import get_env

from storm.utils.randomness import Randomness # pylint: disable=import-error

from  . import formula_transforms

BV_UNARY_OPS = frozenset([ops.BV_NOT, ops.BV_NEG, ops.BV_ROL,ops.BV_ROR])
BV_BINARY_OPS = frozenset([ ops.BV_AND, ops.BV_OR, ops.BV_XOR, ops.BV_ADD, \
                            ops.BV_SUB, ops.BV_MUL, ops.BV_UDIV,\
                            ops.BV_UREM,  ops.BV_SDIV, ops.BV_SREM])
OTHER_BV_OPS = frozenset([ops.BV_ZEXT, ops.BV_SEXT, ops.BV_EXTRACT, ops.BV_CONCAT, ops.BV_COMP, ops.BV_LSHL, ops.BV_ASHR, ops.BV_LSHR])
MY_IRA_OPS = frozenset(filter(lambda t: t not in (ops.BV_TONATURAL, ops.TOREAL),ops.IRA_OPERATORS))

assert BV_UNARY_OPS | BV_BINARY_OPS | OTHER_BV_OPS == ops.BV_OPERATORS


def get_constants_for_type(node_type: types.PySMTType) -> set[FNode] | FrozenSet[FNode]:
    if node_type == types.BOOL:
        return frozenset([sc.FALSE(), sc.TRUE()])
    if node_type == types.INT:
        return frozenset([sc.Int(0), sc.Int(1), sc.Int(2**63 - 1), sc.Int(2**63 + 1)])
    if node_type.is_bv_type():
        width = node_type.width # type: ignore
        return set([sc.BVZero(width), sc.BVOne(width), sc.BV(2**width - 1, width), sc.BV(2**(width-1), width)])
    return set()

class FormulaBuilder():
    def __init__(self, formula: FNode, logic: str, max_depth: int, rand: Randomness):
        self.variables_by_type = {}
        for variable in formula_transforms.get_nodes(formula, lambda _: True):
            node_type = variable.get_type()
            if variable.get_type() not in self.variables_by_type:
                self.variables_by_type[node_type] = set()
            self.variables_by_type[node_type].add(variable)
        self.logic = logic
        self.max_depth = max_depth
        self.bv_types = set(filter(lambda t: t.is_bv_type(), self.variables_by_type.keys()))
        self.variables_depths = formula_transforms.label_formula_depth(formula)
        self.random = rand
        self.has_arrays = len(formula_transforms.get_array_index_calls(formula)[1]) > 0
        
    def get_random_assertion(self, max_depth: int):
        return self.build_formula_of_type(types.BOOL, max_depth)
    
    def build_formula_of_type(self, node_type: types.PySMTType, max_depth: int) -> FNode:
        if max_depth == 0:
            return self.random.random_choice(self.get_leaves_for_type(node_type, max_depth))
        res = self.random.random_choice(self.get_ops_for_outtype(node_type)\
                                                             + [(l, []) for l in self.get_leaves_for_type(node_type, max_depth)])
        next_operation, subtypes_needed = res
        if isinstance(next_operation, FNode):
            return next_operation
        node_args = tuple(self.build_formula_of_type(t, max_depth-1) for t in subtypes_needed)
        payload = self.get_payload_for_op(next_operation, node_type, subtypes_needed)
        return get_env().formula_manager.create_node(next_operation, node_args, payload)
    
    def get_ops_for_outtype(self, out_type: types.PySMTType) -> list[tuple[int,list[types.PySMTType]]]:
        res = []
        if out_type == types.BOOL:
            res.append((ops.NOT,[types.BOOL]))
            res.extend([(o,[types.BOOL, types.BOOL]) for o in filter(lambda o: o != ops.NOT, ops.BOOL_CONNECTIVES)])
            if ('BV' in self.logic):
                res.extend([(o,[t,t]) for o in ops.BV_RELATIONS for t in self.bv_types])
                res.extend([(ops.EQUALS,[t,t]) for t in self.bv_types])
            if ('IA' in self.logic):
                res.extend([(o,[types.INT,types.INT]) for o in ops.IRA_RELATIONS])
                res.append([(ops.EQUALS,[types.INT,types.INT])])
        if out_type.is_bv_type:
            res.extend([(o,[out_type]) for o in BV_UNARY_OPS])
            res.extend([(o,[out_type, out_type]) for o in BV_BINARY_OPS])
        if out_type.is_int_type:
            res.extend([(o,[types.INT, types.INT]) for o in MY_IRA_OPS])

        if self.has_arrays and 'ABV' in self.logic:
            res.extend([(ops.ARRAY_SELECT,[types.ArrayType(bv_t,out_type),bv_t]) for bv_t in self.bv_types])
            if out_type.is_bool_type():
                res.extend([(ops.EQUALS,[types.ArrayType(bv_t,out_type),types.ArrayType(bv_t,out_type)]) for bv_t in self.bv_types])
            if out_type.is_array_type():
                    res.extend([(ops.ARRAY_STORE,[types.ArrayType(bv_t,out_type),bv_t,out_type]) for bv_t in self.bv_types])

        if self.has_arrays and ('AL' in self.logic or 'AN' in self.logic):
            res.append((ops.ARRAY_SELECT,[types.ArrayType(types.INT,out_type),types.INT]))
            if out_type.is_bool_type():
                res.append((ops.ARRAY_SELECT,[types.ArrayType(types.INT,out_type),types.ArrayType(types.INT,out_type)]))
            if out_type.is_array_type():
                res.append((ops.ARRAY_SELECT,[types.ArrayType(types.INT,out_type),types.INT,out_type]))

        return res
    
    def get_leaves_for_type(self,node_type: types.PySMTType, maximum_depth: int) -> list[FNode]:
        return list(filter(lambda v: self.variables_depths[v] <= maximum_depth, self.variables_by_type[node_type])) + list(get_constants_for_type(node_type))
    
    def get_payload_for_op(self,op: int, node_type: types.PySMTType, argtypes: list[types.PySMTType]):
        if op in (ops.BV_ZEXT, ops.BV_SEXT):
            return (argtypes[0].width, argtypes[0].width - node_type.width) #type: ignore
        if op == ops.BV_CONCAT:
            return (argtypes[0].width + argtypes[1].width,) # type: ignore
        if op == ops.BV_EXTRACT:
            diff = argtypes[0].width - node_type.width#type: ignore
            offset = self.random.get_random_integer(0,diff) # type: ignore # TODO: see what is correct here
            return (diff, offset, argtypes[0].width+offset-1) #type: ignore
        if op in (ops.BV_ROL, ops.BV_ROR):
            return (node_type.width, self.random.get_random_integer(0,node_type.width-1)) #type: ignore
        if op in ops.BV_OPERATORS:
            return (node_type.width,) # type: ignore
        return None
