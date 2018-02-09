# -*- coding: utf-8 -*-

###############################################################################
# This file is part of Kalray's Metalibm tool
# Copyright (2016)
# All rights reserved
# created:          Nov 17th, 2016
# last-modified:    Nov 17th, 2016
#
# author(s):   Nicolas Brunie (nicolas.brunie@kalray.eu)
# description: Implementation of the class for wrapping
#              the content and interfaces (code) of an architectural 
#              entity
###############################################################################

from ..core.ml_operations import AbstractVariable, Variable, FunctionObject, Statement, ReferenceAssign
from ..core.ml_hdl_operations import Signal, ComponentObject
from .code_object import NestedCode
from .generator_utility import FunctionOperator, FO_Arg
from .code_constant import *
from ..core.attributes import Attributes, AttributeCtor


class CodeEntity(object):
  """ function code object """
  def __init__(self, name, arg_list = None, output_map = None, code_object = None, language = VHDL_Code):
    """ code function initialization """
    self.name = name
    self.arg_list = arg_list if arg_list else []
    self.arg_map = dict((arg.get_tag(), arg) for arg in self.arg_list)
    self.output_map = output_map if output_map else {}
    self.code_object = code_object
    self.entity_object   = None
    self.entity_operator = None
    self.language = language
    self.process_list = []
    self.current_stage = 0
    # component object to generate external instance of entity
    self.component_object = None
    self.instanciate_dyn_attributes()

  def instanciate_dyn_attributes(self):
    # attribute to contain thestage where the pipelined
    # signal was originally created
    self.init_stage_attribute = AttributeCtor("init_stage", default_value = self.current_stage)
    # attribute to contain the original operation for the pipelined signals
    self.init_op_attribute    = AttributeCtor("init_op", default_value = None) 
    Attributes.add_dyn_attribute(self.init_stage_attribute)
    Attributes.add_dyn_attribute(self.init_op_attribute)

  def get_name(self):
    return self.name

  def add_input_variable(self, name, vartype):
    input_var = Variable(name, precision = vartype) 
    self.arg_list.append(input_var)
    self.arg_map[name] = input_var
    return input_var
  def add_output_variable(self, name, output_node):
    output_var = Variable(name, precision = output_node.get_precision(), var_type = Variable.Output)
    output_assign = ReferenceAssign(output_var, output_node)
    if name in self.output_map:
        Log.report(Log.error, "pre-existing name {} in output_map".format(name))
    self.output_map[name] = output_assign

  def add_input_signal(self, name, signaltype):
    input_signal = Signal(name, precision = signaltype) 
    self.arg_list.append(input_signal)
    self.arg_map[name] = input_signal
    return input_signal
  def add_output_signal(self, name, output_node):
    output_var = Signal(name, precision = output_node.get_precision(), var_type = Signal.Output)
    output_assign = ReferenceAssign(output_var, output_node)
    if name in self.output_map:
        Log.report(Log.error, "pre-existing name {} in output_map".format(name))
    self.output_map[name] = output_assign

  def get_input_by_tag(self, tag):
    if tag in self.arg_map:
      return self.arg_map[tag]
    else:
      return None

  def get_port_from_output(self, out):
    return out.get_input(0)
  def get_value_from_output(self, out):
    return out.get_input(1)

  def get_output_assign(self):
    return self.output_map.values()
  def get_output_value_by_name(self, name):
    return self.get_value_from_output(self.output_map[name])
  def get_output_port_by_name(self, name):
    return self.get_port_from_output(self.output_map[name])
  def get_output_list(self):
    return [self.get_value_from_output(op) for op in self.get_output_assign()]
  def get_output_port(self):
    return [self.get_port_from_output(op) for op in self.get_output_assign()]

  def get_current_stage(self):
    return self.current_stage
  def start_new_stage(self):
    self.set_current_stage(self.current_stage + 1)
  def set_current_stage(self, stage_id = 0):
    self.current_stage = stage_id
    self.init_stage_attribute.default_value = self.current_stage

  def add_process(self, new_process):
    self.process_list.append(new_process)
  def register_new_input_variable(self, new_input):
    self.arg_list.append(new_input)

  def get_arg_list(self):
    return self.arg_list
  def clear_arg_list(self):
    self.arg_list = []

  def get_component_object(self):
    if self.component_object is None:
      self.component_object = self.build_component_object()
    return self.component_object

  def build_component_object(self):
    io_map = {}
    for arg_input in self.arg_list:
      io_map[arg_input] = AbstractVariable.Input 
    for arg_output in self.get_output_port():
      io_map[arg_output] = AbstractVariable.Output 
    return ComponentObject(self.name, io_map, self)

  def get_output_precision(self, output):
    """ Retrieve the format of an output ReferenceAssign
        
        Args:
            self (CodeEntity): self object
            output(ReferenceAssign): output assignation

        Returns:
            ML_Format: output format
    """
    assert isinstance(output, ReferenceAssign)
    out_signal = output.get_input(0)
    out_value  = output.get_input(1)
    if out_signal.get_precision() is None:
        return out_value.get_precision()
    else:
        return out_signal.get_precision()
    
  def get_declaration(self, final = True, language = None):
    language = self.language if language is None else language
    # input signal declaration
    input_port_list = ["%s : in %s" % (inp.get_tag(), inp.get_precision().get_code_name(language = language)) for inp in self.arg_list]
    output_port_list = ["%s : out %s" % (self.get_port_from_output(out).get_tag(), self.get_output_precision(out).get_code_name(language = language)) for out in self.get_output_assign()]
    port_format_list = ";\n  ".join(input_port_list + output_port_list)
    # FIXME: add suport for inout and generic
    port_desc = "port (\n  {port_list}\n);".format(port_list = port_format_list)
    if len(port_format_list) == 0:
      port_desc = ""
    return "entity {entity_name} is \n{port_desc}\nend {entity_name};\n\n".format(entity_name = self.name, port_desc = port_desc)

  def get_component_declaration(self, final = True, language = None):
    language = self.language if language is None else language
    # input signal declaration
    input_port_list = ["%s : in %s" % (inp.get_tag(), inp.get_precision().get_code_name(language = language)) for inp in self.arg_list]
    output_port_list = ["%s : out %s" % (self.get_port_from_output(out).get_tag(), self.get_port_from_output(out).get_precision().get_code_name(language = language)) for out in self.get_output_assign()]
    port_format_list = ";\n  ".join(input_port_list + output_port_list)
    port_desc = "port (\n  {port_list}\n);".format(port_list = port_format_list)
    if len(port_format_list) == 0:
      port_desc = ""
    # FIXME: add suport for inout and generic
    return "component {entity_name} \n{port_desc}\nend component;\n\n".format(entity_name = self.name, port_desc = port_desc)

  ## @return function implementation (ML_Operation DAG)
  def get_scheme(self):
    return Statement(*tuple(self.process_list + list(self.get_output_assign())))

  def get_definition(self, code_generator, language, folded = True, static_cst = False):
    code_object = NestedCode(code_generator, static_cst = static_cst, code_ctor = VHDLCodeObject)
    code_object.add_local_header("ieee.std_logic_1164.all")
    code_object.add_local_header("ieee.std_logic_unsigned.all")
    code_object.add_local_header("ieee.numeric_std.all")
    code_object << self.get_declaration(final = False, language = language)
    code_object.open_level(inc = False)
    code_generator.generate_expr(code_object, self.get_scheme(), folded = folded, initial = False, language = language)
    code_object.close_level(inc = False)
    return code_object

  def add_definition(self, code_generator, language, code_object, folded = True, static_cst = False):
    code_object << self.get_declaration(final = False, language = language)
    code_object << "architecture rtl of {entity_name} is\n".format(entity_name = self.name)
    code_object.open_level()
    code_generator.generate_expr(code_object, self.get_scheme(), folded = folded, initial = False, language = language)
    code_object.close_level()
    code_object << "end architecture;\n"
    #code_object.close_level(inc = False)
    return code_object
