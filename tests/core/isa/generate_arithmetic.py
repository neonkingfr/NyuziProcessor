#!/usr/bin/env python3
#
# Copyright 2011-2015 Jeff Bush
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obop1typein a copy of the License at
#
#     http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limiop1typetions under the License.
#

"""
Create an assembly test that verifies all major integer instruction forms.
The output of this is checked in, so this only needs to be run if the instruction
set changes.
"""

import math
import random
import sys

VECTOR_WIDTH = 16

def vector_op(vec1, vec2, op):
    return [ op(a, b) for a, b in zip(vec1, vec2) ]

def splat(val):
    return [ val for i in range(VECTOR_WIDTH) ]

def apply_mask(mask, value):
    return [ val if (mask & (1 << i)) else 0 for i, val in enumerate(value) ]

def hexlist(values):
    str = ''
    for x in values:
        if str:
            str += ', ' + hex(x)
        else:
            str = hex(x)

    return str

def ashr32(val, amt):
    if val & 0x80000000:
        val |= 0xffffffff00000000

    return (val >> amt) & 0xffffffff

def sext64(val):
    return val | 0xffffffff00000000 if (val & 0x80000000) != 0 else val

def clz(val):
    for bitidx in range(32):
        if (val & (0x80000000 >> bitidx)) != 0:
            return bitidx

    return 32

def ctz(val):
    for bitidx in range(32):
        if (val & (1 << bitidx)) != 0:
            return bitidx

    return 32

vector_operand1 = [ random.randint(0, 0xffffffff) for x in range(VECTOR_WIDTH) ]
vector_operand2 = [ random.randint(0, 0xffffffff) for x in range(VECTOR_WIDTH) ]
vector_operand3 = [ random.randint(0, 16) for x in range(VECTOR_WIDTH) ]
vector_results = []

FORMS = [
    ('s', 's', ''),
    ('v', 's', ''),
    ('v', 's', '_mask'),
    ('v', 'v', ''),
    ('v', 'v', '_mask'),
    ('s', 'i', ''),
    ('v', 'i', ''),
    ('v', 'i', '_mask')
]

BINOPS = [
    ('or',      False, lambda a, b: (a | b) & 0xffffffff),
    ('and',     False, lambda a, b: (a & b) & 0xffffffff),
    ('xor',     False, lambda a, b: (a ^ b) & 0xffffffff),
    ('add_i',   False, lambda a, b: (a + b) & 0xffffffff),
    ('sub_i',   False, lambda a, b: (a - b) & 0xffffffff),
    ('mull_i',  False, lambda a, b: (a * b) & 0xffffffff),
    ('mulh_u',  False, lambda a, b: (a * b) >> 32),
    ('mulh_i',  False, lambda a, b: ((sext64(a) * sext64(b)) >> 32) & 0xffffffff),
    ('ashr',    False, ashr32),
    ('shr',     False, lambda a, b: int(math.fabs(a)) >> b),
    ('shl',     False, lambda a, b: (a << b) & 0xffffffff),
    ('clz',     True, lambda a, b: clz(b)),
    ('ctz',     True, lambda a, b: ctz(b)),
    ('move',    True, lambda a, b: b),
]

print('# This file auto-generated by ' + sys.argv[0] + '''. Do not edit.
            #include "arithmetic_macros.inc"

            .globl _start
_start:''')

for mnemonic, is_unary, func in BINOPS:
    for op1type, op2type, suffix in FORMS:
        if op2type == 'i' and is_unary:
            continue

        has_mask = suffix != ''
        maskval = random.randint(0, 0xffff)
        if mnemonic in ('shr', 'shl', 'ashr'):
            op2range = 15
        elif op2type == 'i':
            op2range = 0x7f
        else:
            op2range = 0xffffffff

        if op1type == 'v':
            op1 = 'voperand1'
            if op2type == 'v':
                if op2range < 0xffffffff:
                    op2 = 'voperand3'
                    op2val = vector_operand3
                else:
                    op2 = 'voperand2'
                    op2val = vector_operand2

                resultval = vector_op(vector_operand1, op2val, func)
                if has_mask:
                    resultval = apply_mask(maskval, resultval)

                result = 'result' + str(len(vector_results))
                vector_results.append(resultval)
            else:
                # Scalar op2
                op2val = random.randint(0, op2range)
                op2 = hex(op2val)
                resultval = vector_op(vector_operand1, splat(op2val), func)
                if has_mask:
                    resultval = apply_mask(maskval, resultval)

                result = 'result' + str(len(vector_results))
                vector_results.append(resultval)
        else:
            op1val = random.randint(0, 0xffffffff)
            op2val = random.randint(0, op2range)
            op1 = hex(op1val)
            op2 = hex(op2val)
            resultval = func(op1val, op2val)
            result = hex(resultval)

        opstr = '        test_{}{}{}{} {}, {}, '.format(op1type,
            '' if is_unary else op1type,
            op2type,
            'm' if has_mask else '',
            mnemonic + suffix, result)
        if has_mask:
            opstr += hex(maskval) + ', '

        if is_unary:
            opstr += '{}'.format(op2)
        else:
            opstr += '{}, {}'.format(op1, op2)

        print(opstr)

print('        call pass_test\n')
print('        .align 64')
print('voperand1:     .long ' + hexlist(vector_operand1))
print('voperand2:     .long ' + hexlist(vector_operand2))
print('voperand3:     .long ' + hexlist(vector_operand3))
for i, value in enumerate(vector_results):
    print('result' + str(i) + ': .long ' + hexlist(value))
