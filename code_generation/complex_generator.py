# -*- coding: utf-8 -*-

###############################################################################
# This file is part of Kalray's Metalibm tool
# Copyright (2013)
# All rights reserved
# created:          Oct 6th, 2015
# last-modified:    
#
# author(s): Nicolas Brunie (nicolas.brunie@kalray.eu)
###############################################################################

from ..utility.log_report import Log
from ..utility.common import ML_NotImplemented, zip_index
from .generator_utility import ML_CG_Operator


## complex generator for symbol-like operators, 
#  the generate expression modifies the optree before calling the 
#  code_generator.generate_expr
#
class ComplexOperator(ML_CG_Operator):

  ## constructor
  def __init__(self, optree_modifier, backup_operator = None, **kwords):
    ML_CG_Operator.__init__(self, **kwords)
    ## function used to modify optree before code generation
    self.optree_modifier = optree_modifier
    ## generator used when optree returned by modifier is None
    self.backup_operator = backup_operator

  ## generate expression for operator
  # @param self current operator
  # @param code_generator CodeGenerator object used has helper for code generation services
  # @param code_object    CobeObject receiving generated code
  # @param optree         Operation object being generated
  # @param arg_tuple      tuple of optree's arguments
  # @param generate_pre_process  lambda function (None by default) used in preprocessing
  # @param kwords         generic keywords dictionnary (see ML_CG_Operator() class for list of supported arguments)
  def generate_expr(self, code_generator, code_object, optree, arg_tuple, generate_pre_process = None, **kwords):
    new_optree = self.optree_modifier(optree)
    if new_optree is None and self.backup_operator != None:
      return self.backup_operator.generate_expr(code_generator, code_object, optree, arg_tuple, generate_pre_process = generate_pre_process, **kwords)
    else:
      return code_generator.generate_expr(code_object, new_optree, **kwords)

