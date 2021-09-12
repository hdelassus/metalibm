# -*- coding: utf-8 -*-

###############################################################################
# This file is part of metalibm (https://github.com/metalibm/metalibm)
###############################################################################
# MIT License
#
# Copyright (c) 2021 Nicolas Brunie
#
# Permission is hereby granted, free of charge, to any person obtaining a copy
# of this software and associated documentation files (the "Software"), to deal
# in the Software without restriction, including without limitation the rights
# to use, copy, modify, merge, publish, distribute, sublicense, and/or sell
# copies of the Software, and to permit persons to whom the Software is
# furnished to do so, subject to the following conditions:
#
# The above copyright notice and this permission notice shall be included in all
# copies or substantial portions of the Software.
#
# THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
# IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
# FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE
# AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER
# LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM,
# OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE
# SOFTWARE.
###############################################################################
# created:          Sep  5th, 2021
# last-modified:    Sep  5th, 2021
#
# Author(s):        Nicolas Brunie <metalibmdev@gmail.com>
###############################################################################

import os

from metalibm_core.core.target import UniqueTargetDecorator
from metalibm_core.core.ml_operations import (
    SpecificOperation, NearestInteger, Conversion)
from metalibm_core.core.ml_formats import (
    ML_Int64, ML_Int32,
    ML_Binary64, ML_Binary32)

from metalibm_core.code_generation.abstract_backend import LOG_BACKEND_INIT
from metalibm_core.code_generation.code_constant import C_Code
from metalibm_core.code_generation.generator_utility import (
    AsmInlineOperator, FO_Result, FO_Arg, type_strict_match)
from metalibm_core.code_generation.complex_generator import ComplexOperator

from metalibm_core.utility.log_report import Log

from metalibm_core.targets.common.vector_backend import VectorBackend


rdcycleOperator = AsmInlineOperator(
"""{
    unsigned long cycles;
    asm volatile ("rdcycle %%0 " : "=r" (cycles));
    %s = cycles;
}""",
    arg_map = {0: FO_Result(0)},
    arity = 0
)

def RV_singleOpAsmTemplate(insn, regDst="r", regSrc="f"):
    singleOpOperator = AsmInlineOperator(
   """asm volatile ("{insn} %%0, %%1 " : "={regDst}" (%s) : "{regSrc}"(%s));\n""".format(insn=insn, regDst=regDst, regSrc=regSrc),
        arg_map = {0: FO_Result(0), 1: FO_Arg(0)},
        arity=1
    )
    return singleOpOperator

def lowerConversion(intFormat, targetFormat):
    """ expand conversion into a conversion from
        conv's input to <intFormat> and then to <targetFormat> """
    def modifier(conv):
        op = conv.get_input(0)
        return Conversion(Conversion(op, precision=intFormat), precision=targetFormat)
    return modifier

rv64CCodeGenTable = {
    SpecificOperation: {
        SpecificOperation.ReadTimeStamp: {
            lambda _: True: {
                type_strict_match(ML_Int64): rdcycleOperator
            }
        }
    },
    # Conversion are mapped to function by default
    # so we lower them explicity to less-contrained
    # implementation
    NearestInteger: {
        None: {
            lambda optree: True: {
                type_strict_match(ML_Int32, ML_Binary32):
                    RV_singleOpAsmTemplate("fcvt.w.s"),
                type_strict_match(ML_Binary32, ML_Binary32):
                    ComplexOperator(optree_modifier=lowerConversion(ML_Int32, ML_Binary32)),
                type_strict_match(ML_Int64, ML_Binary64):
                    RV_singleOpAsmTemplate("fcvt.l.d"),
                type_strict_match(ML_Int32, ML_Binary64):
                    ComplexOperator(optree_modifier=lowerConversion(ML_Int64, ML_Int32)),
                type_strict_match(ML_Binary64, ML_Binary64):
                    ComplexOperator(optree_modifier=lowerConversion(ML_Int64, ML_Binary64)),
            },
        },
    },
}

def buildRVCompilerPath():
    try:
        RISCV = os.environ["RISCV"]
    except KeyError:
        Log.report(Log.Error, "RISCV env variable must be set such than $RISCV/bin/riscv64-unknown-elf-gcc is accessible")
    compiler = "{}/bin/riscv64-unknown-elf-gcc".format(RISCV)
    return compiler


@UniqueTargetDecorator
class RISCV_RV64(VectorBackend):
    target_name = "rv64g"
    default_compiler = buildRVCompilerPath()
    # only cross-compilation (not binary embedding in python) is currently supported
    support_embedded_bin = False
    cross_platform = True

    code_generation_table = {
        C_Code: rv64CCodeGenTable,
    }

    def __init__(self):
        super().__init__()

    def get_compilation_options(self, ML_SRC_DIR):
        return super(RISCV_RV64, self).get_compilation_options(ML_SRC_DIR) + ["-march=rv64gc"]

    def get_execution_command(self, test_file):
        try:
            pk_bin = os.environ["PK_BIN"]
        except:
            Log.report(Log.Error, "PK_BIN env var must point to proxy-kernel image")

        try:
            spike_bin = os.environ["SPIKE_BIN"]
        except:
            Log.report(Log.Error, "SPIKE_BIN env var must point to spike simulator binary")
        cmd = "{} --isa=RV64gc {}  {}".format(spike_bin, pk_bin, test_file)
        return cmd

# debug message
Log.report(LOG_BACKEND_INIT, "initializing RISC-V targets")
