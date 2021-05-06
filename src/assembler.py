from argparse import ArgumentParser
import pyparsing as pp
import sys
import os
from typing import List, Union, Dict
import pipeline
from eisa import EISA

# region instruction formats
# ALU
"""Format:
<mnemonic> <dest: reg>, <op1: reg>, <op2: reg | op2: literal>
"""

# Special
"""Format
NOT
---
NOT <dest: reg>, <op2: reg | op2: literal>
"op1" is implicitly -1

MOV
---
MOV <dest: reg>, <op2: reg | op2: literal>
"op1" is implicitly 0

CMP
---
CMP <op1: reg>, <op2: reg | op2: literal>
CMP instruction does not have a "dest" field
"""

# Branch
"""Format:
(B | BL)<cond> (#<immediate: literal> | \[<base: reg>[, # <offset: literal>]\])
"""

# Load/Store
"""Format:
LDR <dest: reg> (#<immediate: literal> | \[<base: reg>[, # <offset: literal>]\])
STR <src: reg> (#<immediate: literal> | \[<base: reg>[, # <offset: literal>]\])
"""

# Push/Pop
"""Format:
PUSH (<src: reg> | \[<src 1: reg>, ... , <src n: reg>\])
POP (<dest: reg> | \[<dest 1: reg>, ... , <dest n: reg>\])
"""
# endregion instruction formats
class AssemblerError(RuntimeError):
    def __init__(self, symbol):
        super().__init__()
        self.message = f"Unexpected symbol \'{symbol}\' was encountered"

    def __str__(self):
        return self.message


MOV_dest = -1
cur_instruction = pipeline.OpCode.NOOP  # type: pipeline.OpCode

whitespace = pp.White()
whitespace.setName('whitespace')

def parse_mnemonic(mnemonic: str) -> Dict[str, int]:
    """parses the input string for the mnemonic, and also condition code if relevant

    Parameters
    ----------
    parse_string : str
        the string to parse

    Returns
    -------
    dict
        the dictionary
    """

    # parse the strings backwards, that way the condition codes will always be parsed first

    # reverse the original string
    mnemonic = mnemonic[::-1]

    # gets the condition code if there is one
    cond_code_toks_rev = [cc.name[::-1] for cc in pipeline.ConditionCode]
    op_code_toks_rev = [op[::-1] for op in pipeline.OpCode.__members__]

    # gets the opcode
    op_code_parser = pp.oneOf(op_code_toks_rev).setName('mnemonic')
    op_code_parser.setParseAction(lambda result: pipeline.OpCode[result[0][::-1]])  # revrse the string so it's the correct way around

    # combines condition code and opcode parsing
    cond_code_parser = pp.Optional(
        pp.Optional(
            pp.oneOf(cond_code_toks_rev).setName('condition code')
            , default='LA'  # AL backwards
        ).setParseAction(
            lambda result: pipeline.ConditionCode[result[0][::-1]]
        ) + pp.FollowedBy(
            pp.oneOf('B LB').setName('branch instruction') + pp.stringEnd() # B or BL, since they're the only conditional instructions
        ) 
    )
    cond_code_parser.setParseAction(lambda result: None if not result else result[0])  # revrse the string so it's the correct way around

    mnemonic_parser = cond_code_parser('cond') + op_code_parser('opcode')

    return mnemonic_parser.parseString(mnemonic).asDict()

# syntax for parsing registers
gp_reg_parser = pp.Suppress(pp.CaselessLiteral('r')) + pp.oneOf([str(i) for i in range(EISA.NUM_GP_REGS)])
gp_reg_parser.setParseAction(lambda result: int(result[0]))

# syntax for parsing special registers
spec_reg_parser = pp.oneOf([sr.name for sr in pipeline.SpecialRegister])
spec_reg_parser.setParseAction(lambda result: pipeline.SpecialRegister[result[0]])

# combine both register syntaxes
reg_parser = gp_reg_parser | spec_reg_parser
reg_parser.setName('register')

# syntax for parsing literals (binary, hexadecimal, and decimal)
bin_parser = pp.Combine('0b' + pp.Word('01'))       # 0b00000000 indicates binary numbers
# bin_parser.setName('binary literal')
dec_parser = pp.Word(pp.nums)                       #   00000000 indicates decimal numbers
dec_parser.setName('decimal literal')
hex_parser = pp.Combine('0x' + pp.Word(pp.hexnums)) # 0x00000000 indicates hexadecimal numbers
hex_parser.setName('hexadecimal literal')

literal_parser = (bin_parser | hex_parser | dec_parser)
literal_parser.setName('literal')
literal_parser.setParseAction(lambda num_str: int(num_str[0], 0))  # will autimatically convert to a number

# tells the parser to not include commas in the final output
comma = pp.Suppress(',')
comma.setName(',')

comment = ';' + pp.restOfLine

def parse_ALU_args(opcode: pipeline.OpCode, args: str) -> Dict[str, int]:
    # determines whether op1 is a literal or register
    is_lit = pp.FollowedBy(literal_parser).setParseAction(lambda: True)
    is_reg = pp.FollowedBy(reg_parser).setParseAction(lambda: False)
    lit_or_reg = (is_lit ^ is_reg)('lit')
    lit_or_reg.setParseAction(lambda result: result[0])

    def op1_parse_action(result: pp.ParseResults):
        # print(f'op1: {result}')
        if opcode is pipeline.OpCode.MOV or opcode is pipeline.OpCode.NOT:
            raise pp.ParseException
        else:
            return result[0]
    
    # op1 parsing
    def MOV_NOT_op1_parse_action(result):
        # print(f'MOV: {result} {opcode is pipeline.OpCode.MOV}')
        # print(f'NOT: {result} {opcode is pipeline.OpCode.NOT}')
        
        if opcode is pipeline.OpCode.MOV:
            # handles NOT
            return pipeline.SpecialRegister.zr
        elif opcode is pipeline.OpCode.NOT:
            # handles MOV
            return -1 & EISA.ADDRESS_MASK

    MOV_NOT_op1_parser = whitespace[...].setParseAction(MOV_NOT_op1_parse_action)
    
    op1_parser = (
        whitespace[...].setParseAction(MOV_NOT_op1_parse_action).addCondition(lambda: opcode is pipeline.OpCode.MOV or opcode is pipeline.OpCode.NOT) | 
        (reg_parser + comma).setParseAction(op1_parse_action)
    )('op1')
    op1_parser.setParseAction(lambda result: result[0])

    # op2 parsing
    op2_parser = reg_parser.setResultsName('op2') 
    op2_parser.setParseAction(lambda result: result[0])    

    # dest parsing
    def dest_parse_action(result: pp.ParseResults):
        # print(f'dest: {result} {opcode}')
        if opcode is not pipeline.OpCode.CMP:
            return result[0]
        else:
             raise pp.ParseException
    
    dest_parser = (~whitespace).addCondition(lambda: opcode is pipeline.OpCode.CMP) | (reg_parser + comma).setParseAction(dest_parse_action)('dest') 

    alu_arg_parser = dest_parser + op1_parser + lit_or_reg + (op2_parser | literal_parser.copy()('literal')) + pp.stringEnd()

    return alu_arg_parser.parseString(args).asDict()

# region debugging

# print('testing special ALU ops')
# print('testing MOV')
# print(parse_ALU_args(pipeline.OpCode.MOV, 'r0, r1'))
# print(parse_ALU_args(pipeline.OpCode.MOV, 'r0, 10'))
# print(parse_ALU_args(pipeline.OpCode.MOV, 'r0, 0b10'))
# print(parse_ALU_args(pipeline.OpCode.MOV, 'r0, 0x10'))
# print('testing NOT')
# print(parse_ALU_args(pipeline.OpCode.NOT, 'r1, r1'))
# print(parse_ALU_args(pipeline.OpCode.NOT, 'r1, 10'))
# print(parse_ALU_args(pipeline.OpCode.NOT, 'r1, 0b10'))
# print(parse_ALU_args(pipeline.OpCode.NOT, 'r1, 0x10'))
# print('testing CMP')
# print(parse_ALU_args(pipeline.OpCode.CMP, 'r2, r1'))
# print(parse_ALU_args(pipeline.OpCode.CMP, 'r2, 10'))
# print(parse_ALU_args(pipeline.OpCode.CMP, 'r2, 0b10'))
# print(parse_ALU_args(pipeline.OpCode.CMP, 'r2, 0x10'))
# print('testing regular ALU ops')
# print('testing ADD')
# print(parse_ALU_args(pipeline.OpCode.ADD, 'r0, r1, r1'))
# print(parse_ALU_args(pipeline.OpCode.ADD, 'r0, r1, 10'))
# print(parse_ALU_args(pipeline.OpCode.ADD, 'r0, r1, 0b10'))
# print(parse_ALU_args(pipeline.OpCode.ADD, 'r0, r1, 0x10'))
# print('testing XOR')
# print(parse_ALU_args(pipeline.OpCode.XOR, 'r0, r1, r1'))
# print(parse_ALU_args(pipeline.OpCode.XOR, 'r0, r1, 10'))
# print(parse_ALU_args(pipeline.OpCode.XOR, 'r0, r1, 0b10'))
# print(parse_ALU_args(pipeline.OpCode.XOR, 'r0, r1, 0x10'))

# endregion debugging

# syntax for an immediate memory access
immediate_parser = pp.Combine(
    pp.Suppress('#').setName('#') + 
    literal_parser
).setResultsName('immediate')
immediate_parser.setParseAction(lambda result: int(result[0]))

# syntax for a register memory access (as opposed to an immediate)
reg_mem_access_parser = \
    pp.Suppress('[').setName('[') + \
    reg_parser('base').setParseAction(lambda result: result[0]) + \
    (
            (comma + immediate_parser) |
            (~(comma + immediate_parser)).setParseAction(lambda x: 0)
    ).setParseAction(lambda tok: tok[0]).setResultsName('offset') + \
    pp.Suppress(']').setName(']')

# checks if there is an immediate or a register
is_imm = pp.FollowedBy(immediate_parser).setParseAction(lambda x: True)
is_reg = pp.FollowedBy(reg_mem_access_parser).setParseAction(lambda x: False)
imm_or_reg = (is_imm ^ is_reg).setParseAction(lambda tok: tok[0])

# [immediate] or [[reg]<, [immediate]>]
mem_access_syntax = \
    imm_or_reg.setResultsName('imm') + \
    (
            immediate_parser | \
            reg_mem_access_parser
    )
def parse_MEM_args(opcode: pipeline.OpCode, args: str) -> Dict[str, int]:
    # evaluates the src/dest register for memory acces
    if opcode is pipeline.OpCode.LDR:
        reg_name ='dest'
    elif opcode is pipeline.OpCode.STR:
        reg_name = 'src'
    else:
        raise pp.ParseFatalException


    mem_arg_parser = reg_parser(reg_name).setParseAction(lambda result: result[0]) + comma + mem_access_syntax

    return mem_arg_parser.parseString(args).asDict()

def parse_B_args(opcode: pipeline.OpCode, args: str) -> Dict[str, int]:
    return mem_access_syntax.parseString(args).asDict()

def parse_STK_args(opcode: pipeline.OpCode, args: str) -> Dict[str, int]:
    if opcode is pipeline.OpCode.PUSH:
        reg_name = 'src'
    elif opcode is pipeline.OpCode.POP:
        reg_name = 'dest'
    else:
        raise pp.ParseFatalException
    
    stk_arg_parser = reg_parser(reg_name).setParseAction(lambda result: result[0])

    return stk_arg_parser.parseString(args).asDict()

def parse_line(line: str) -> Dict[str, int]:
    # handle blank lines and comments
    everything = ... + pp.LineEnd()
    everything.ignore(comment)

    parsed_line, *_ = everything.parseString(line).asList() 

    if not parsed_line:
        # the line is empty and can be ignored
        return {}

    # separate the args from the mnemonic
    mnemonic, args = (line.split(' ', maxsplit=1) + [None])[:2]  
    # the weirdness with + [None] is so we can still unpack the variables 
    # even if the string can't be split such as when parsing END or NOOP instructions

    mnemonic_dict = parse_mnemonic(mnemonic)

    opcode = mnemonic_dict['opcode']

    # OpCodes 1-12 correspond to ALU ops
    if opcode in list(pipeline.OpCode)[1:13]:  
        # parse ALU args
        arg_dict = parse_ALU_args(opcode, args)
    elif opcode in [pipeline.OpCode.LDR, pipeline.OpCode.STR]:
        # parse LDR/STR args
        arg_dict = parse_MEM_args(opcode, args)
    elif opcode in [pipeline.OpCode.B, pipeline.OpCode.BL]:
        # parse Branch args
        arg_dict = parse_B_args(opcode, args)
    elif opcode in [pipeline.OpCode.NOOP, pipeline.OpCode.END]:
        # parse NOOP args (there are none)
        arg_dict = {}
    elif opcode in [pipeline.OpCode.PUSH, pipeline.OpCode.POP]:
        arg_dict = parse_STK_args(opcode, args)
    else:
        # we missed something, uh oh
        raise pp.ParseFatalException(msg=f'\'{opcode}\' not recognized')

    return mnemonic_dict | arg_dict

    
# region debugging

# print(parse_ALU_args(pipeline.OpCode.ADD, 'r0, r1, r15'))
# print(parse_ALU_args(pipeline.OpCode.ADD, 'r0, r1, 0b1111'))
# print(parse_ALU_args(pipeline.OpCode.ADD, 'r0, r1, 0xf'))
# print(parse_ALU_args(pipeline.OpCode.ADD, 'r0, r1, 15'))
# print(parse_ALU_args(pipeline.OpCode.CMP, 'r2, r16'))
# print(parse_ALU_args(pipeline.OpCode.CMP, 'r2, 16'))
# print(parse_ALU_args(pipeline.OpCode.CMP, 'r0, r1'))
# print(parse_MEM_args(pipeline.OpCode.LDR, 'r0, [r1]'))
# print(parse_MEM_args(pipeline.OpCode.LDR, 'r0, [r1, #10]'))
# print(parse_MEM_args(pipeline.OpCode.LDR, 'r0, [r1, #0x10]'))
# print(parse_MEM_args(pipeline.OpCode.LDR, 'r0, [r1, #0b10]'))
# print(parse_MEM_args(pipeline.OpCode.LDR, 'r0, #10'))
# print(parse_MEM_args(pipeline.OpCode.STR, 'r2, [r1]'))
# print(parse_MEM_args(pipeline.OpCode.STR, 'r2, [r1, #10]'))
# print(parse_MEM_args(pipeline.OpCode.STR, 'r2, #10'))
# print(parse_B_args(pipeline.OpCode.B, '[r1]'))
# print(parse_B_args(pipeline.OpCode.B, '[r1, #10]'))
# print(parse_B_args(pipeline.OpCode.B, '#10'))
# print(parse_B_args(pipeline.OpCode.BL, '[r1]'))
# print(parse_B_args(pipeline.OpCode.BL, '[r1, #10]'))
# print(parse_B_args(pipeline.OpCode.BL, '#10'))

# print(parse_line('ADD r0, r1, r15'))
# print(parse_line('ADD r0, r1, 0b1111'))
# print(parse_line('ADD r0, r1, 0xf'))
# print(parse_line('ADD r0, r1, 15'))
# print(parse_line('CMP r2, r16'))
# print(parse_line('CMP r2, 16'))
# print(parse_line('CMP r0, r1'))
# print(parse_line('LDR r0, [r1]'))
# print(parse_line('LDR r0, [r1, #10]'))
# print(parse_line('LDR r0, [r1, #0x10]'))
# print(parse_line('LDR r0, [r1, #0b10]'))
# print(parse_line('LDR r0, #10'))
# print(parse_line('STR r2, [r1]'))
# print(parse_line('STR r2, [r1, #10]'))
# print(parse_line('STR r2, #10'))
# print(parse_line('B [r1]'))
# print(parse_line('B [r1, #10]'))
# print(parse_line('B #10'))
# print(parse_line('BL [r1]'))
# print(parse_line('BL [r1, #10]'))
# print(parse_line('BL #10'))
# print(parse_line('BLT [r1]'))
# print(parse_line('BLT [r1, #10]'))
# print(parse_line('BLT #10'))
# print(parse_line('BLLT [r1]'))
# print(parse_line('BLLT [r1, #10]'))
# print(parse_line('BLLT #10'))
# print(parse_line('BLEQ [r1]'))
# print(parse_line('BLEQ [r1, #10]'))
# print(parse_line('BLEQ #10'))
# print(parse_line('    ; line with space and comment'))
# print(parse_line('; line with only comment'))
# print(parse_line('    '))
# print(parse_line('  '))
# print(parse_line('PUSH r10'))
# print(parse_line('POP r10'))

# endregion debugging

if __name__ == '__main__':
    arg_parse = ArgumentParser()
    arg_parse.add_argument('source', type=str)
    arg_parse.add_argument('-o', type=str, metavar='destination', dest='destination')

    args = arg_parse.parse_args()

    dest = args.destination
    if dest is not None:
        out_file = open(dest, 'w+')
    else:
        out_file = sys.stdout

    with open(args.source, 'r') as in_file:
        for line in in_file:
            print(f'\nparsing line \'{line.rstrip()}\'')

            # parse the line
            parsed = parse_line(line)

            if parsed:  # only parse lines with things in it
                # get the instruction encoding
                cur_encoding = pipeline.Instructions[parsed['opcode']].encoding

                # pass the results to the encoding
                parsed_dict = dict(parsed)
                print(parsed_dict)
                result = cur_encoding(val=parsed_dict)

                print(f'{result._bits:032b}', file=out_file)

    #cprint(f'compiled {args.source} to {"stdout" if dest is None else dest}', color='green')
