from argparse import ArgumentParser
from parse import parse
import pyparsing as pp
import sys
import os
from typing import List
import pipeline


class AssemblerError(RuntimeError):
    def __init__(self, symbol):
        super().__init__()
        self.message = f"Unexpected symbol \'{symbol}\' was encountered"

    def __str__(self):
        return self.message


MOV_dest = -1
cur_instruction = pipeline.OpCode.NOOP


def parse_line(line: str) -> pp.ParseResults:
    # region mnemonic parsing
    conditional_instructions = [pipeline.OpCode.B.name, pipeline.OpCode.BL.name]
    alias_instructions = [pipeline.OpCode.MOV.name, pipeline.OpCode.NOT.name]
    mnemonic_tokens = \
        pp.oneOf([op for op in pipeline.OpCode.__members__ if
                  op not in conditional_instructions and op not in alias_instructions]) ^ \
        pp.oneOf(alias_instructions)
    conditional_mnemonic_tokens = pp.oneOf(conditional_instructions)  # B and BL

    def get_instruction(cond_token):
        global cur_instruction
        cur_instruction = pipeline.OpCode[cond_token[0]]
        return cur_instruction

    mnemonic_tokens.setParseAction(get_instruction)
    conditional_mnemonic_tokens.setParseAction(get_instruction)

    whitespace = pp.White()

    condition_tokens = pp.Optional(~whitespace + pp.oneOf([cond.name for cond in pipeline.ConditionCode]),
                                   default='AL')  # GT, LT, EQ, etc.
    condition_tokens.setParseAction(lambda cond_token: pipeline.ConditionCode[cond_token[0]])

    conditional_opcode_syntax = \
        conditional_mnemonic_tokens('opcode') + \
        condition_tokens('cond')  # BEQ, BLGT etc.

    label_sytax = ~whitespace + pp.Word(pp.alphas) + ':'
    mnemonic_syntax = (mnemonic_tokens('opcode') ^ conditional_opcode_syntax)

    # region mnemonic testing
    # print(mnemonic_syntax.parseString('ADD'))
    # print(mnemonic_syntax.parseString('MOV'))
    # print(mnemonic_syntax.parseString('CMP'))
    # print(mnemonic_syntax.parseString('LDR'))
    # print(mnemonic_syntax.parseString('STR'))
    # print(mnemonic_syntax.parseString('B '))
    # print(mnemonic_syntax.parseString('BL'))
    # print(mnemonic_syntax.parseString('BAL'))
    # print(mnemonic_syntax.parseString('BGT'))
    # print(mnemonic_syntax.parseString('BLEQ'))
    # endregion mnemonic testing

    # endregion mnemonic parsing

    # region instruction parsing
    comma = pp.Suppress(',')  # ignore commas in the final output

    register_num = pp.oneOf(' '.join([str(i) for i in range(32)]))  # 0-31, automatically converts to int
    spec_regs = pp.oneOf([sr.name for sr in pipeline.SpecialRegister])  # the special registers: ZR, LR, SP, PC
    register_tokens = \
        pp.Combine(pp.Suppress(pp.CaselessLiteral('R')) + register_num).setParseAction(
            lambda num_str: int(num_str[0])) | \
        spec_regs.setParseAction(lambda reg_str: pipeline.SpecialRegister[reg_str[0]])

    # region register test
    # print('register test')
    # print('r0')
    # print('R0')
    # endregion register test

    # region ALU parsing

    # binary: 0b[01] 
    # decimal: [0d][0-9]
    # hexadecimal: 0x[0-f]
    bin_nums = pp.Word('01')
    dec_nums = pp.Word(pp.nums)
    hex_nums = pp.Word(pp.hexnums)
    literal_syntax = \
        pp.Combine('0b' + bin_nums) | \
        pp.Combine('0x' + hex_nums) | \
        pp.Combine(dec_nums)

    literal_syntax.setParseAction(lambda num_str: int(num_str[0], 0))  # will autimatically convert to a number

    # checks if there is an operand, or a literal
    is_op = pp.FollowedBy(register_tokens).setParseAction(lambda x: False)
    is_lit = pp.FollowedBy(literal_syntax).setParseAction(lambda x: True)
    lit_or_op = (is_lit ^ is_op)

    # region lit or op test
    # print(lit_or_op.parseString('r2'))
    # print(lit_or_op.parseString('0b1111'))
    # print(lit_or_op.parseString(''))
    # endregion lit or op test

    operand_2 = \
        lit_or_op('lit') + \
        (
                register_tokens('op2') |
                literal_syntax('literal')
        )

    # region op 2 test
    # print('op 2 test')
    # print(operand_2.parseString('r2'))
    # print(operand_2.parseString('0b1111'))
    # endregion op 2 test

    # [dest], [op1], [op2] or [lit]
    ALU_syntax = \
        register_tokens('dest') + \
        comma + register_tokens('op1') + \
        comma + operand_2

    # region ALU test
    # print('ALU test')
    # print(ALU_syntax.parseString('r0, r1, r2'))
    # print(ALU_syntax.parseString('r0, r1, 0b1111'))
    # print(ALU_syntax.parseString('r0, r1, 420'))
    # print(ALU_syntax.parseString('r0, r1, 0xDEAD'))
    # print(ALU_syntax.parseString('r0, r1, 0xbeef'))
    # cur_instruction = pipeline.OpCode.MOV
    # print(ALU_syntax.parseString('r0, r1'))
    # cur_instruction = pipeline.OpCode.NOT
    # print(ALU_syntax.parseString('r0, r1'))
    # endregion ALU test

    # region MOV parsing
    # MOV [dest] [op2]
    # op1 is implicitly assumed to be dest

    MOV_syntax = \
        register_tokens('dest') + \
        (whitespace[...] + pp.FollowedBy(comma + operand_2)).setParseAction(
            lambda: pipeline.SpecialRegister.zr).setResultsName('op1') + \
        comma + operand_2

    # region MOV test
    # print('MOV test')
    # res = MOV_syntax.parseString('r2, r4')
    # print(res)
    # print(f"dest: {res['dest']}")
    # print(f"op1: {res['op1']}")
    # print(f"lit: {res['lit']}")
    # print(f"op2: {res['op2']}")

    # res = MOV_syntax.parseString('r2, 0xbeef')
    # print(res)
    # print(f"dest: {res['dest']}")
    # print(f"op1: {res['op1']}")
    # print(f"lit: {res['lit']}")
    # print(f"literal: {res['literal']}")
    # endregion MOV test
    # endregion MOV parsing

    # region NOT parsing
    # NOT [dest] [op1]
    # op2 is implicitly assumed to be 0b1111111...
    NOT_syntax = \
        register_tokens('dest') + \
        comma + register_tokens('op1') + \
        pp.FollowedBy(whitespace[...]).setResultsName('lit').setParseAction(lambda: False) + \
        pp.FollowedBy(~operand_2).setResultsName('literal').setParseAction(lambda: -1 & 2 ** 32 - 1)

    # region NOT test
    # print('NOT test')
    # print(NOT_syntax.parseString('r0, r1'))
    # endregion NOT test
    # endregion NOT parsing

    # region CMP parsing
    CMP_syntax = \
        register_tokens('op1') + \
        comma + lit_or_op('lit') + \
        (
                register_tokens('op2') ^
                literal_syntax('literal')
        )

    # region CMP test
    # print('CMP test')
    # print(CMP_syntax.parseString('r1, r2'))
    # print(CMP_syntax.parseString('r1, 0b1111'))
    # print(CMP_syntax.parseString('r1, 420'))
    # print(CMP_syntax.parseString('r1, 0xDEAD'))
    # print(CMP_syntax.parseString('r1, 0xbeef'))
    # endregion CMP test
    # endregion CMP parsing
    # endregion ALU parsing

    # region MEM parsing
    # #[lit]
    immediate_syntax = pp.Combine(pp.Suppress('#') + literal_syntax)
    immediate_syntax.setParseAction(lambda x: int(x[0]))

    # syntax for a register memory access (as opposed to an immediate)
    reg_mem_access_syntax = \
        pp.Suppress('[') + \
        register_tokens.setResultsName('base') + \
        (
                (comma + immediate_syntax) |
                (~(comma + immediate_syntax)).setParseAction(lambda x: 0)
        ).setParseAction(lambda tok: tok[0]).setResultsName('offset') + \
        pp.Suppress(']')

    # checks if there is an immediate or a register
    is_imm = pp.FollowedBy(immediate_syntax).setParseAction(lambda x: True)
    is_reg = pp.FollowedBy(reg_mem_access_syntax).setParseAction(lambda x: False)
    imm_or_reg = (is_imm ^ is_reg).setParseAction(lambda tok: tok[0])

    # [immediate] or [[reg]<, [immediate]>]
    mem_access_syntax = \
        imm_or_reg.setResultsName('imm') + \
        (
                immediate_syntax.setResultsName('immediate') | \
                reg_mem_access_syntax
        )

    # region MEM access test
    # print('MEM access test')
    # print(mem_access_syntax.parseString('#420'))
    # print(mem_access_syntax.parseString('#0xbeef'))
    # print(mem_access_syntax.parseString('#0b1111'))
    # print(mem_access_syntax.parseString('[R0]'))
    # print(mem_access_syntax.parseString('[R0, #420]'))
    # print(mem_access_syntax.parseString('[R0 , #69]'))
    # endregion MEM access test
    # region LDR parsing
    LDR_syntax = \
        register_tokens.setResultsName('dest') + \
        comma + mem_access_syntax
    LDR_syntax.addCondition(lambda: cur_instruction == pipeline.OpCode.LDR)
    # region LDR test
    cur_instruction = pipeline.OpCode.LDR
    # print('LDR test')
    # print(LDR_syntax.parseString('R0, #2'))
    # endregion LDR test

    # endregion LDR parsing

    # region STR parsing
    STR_syntax = \
        register_tokens.setResultsName('src') + \
        comma + mem_access_syntax
    STR_syntax.addCondition(lambda: cur_instruction == pipeline.OpCode.STR)
    # endregion STR parsing

    MEM_syntax = \
        (LDR_syntax ^ STR_syntax)

    # region MEM test
    # print('MEM test')
    cur_instruction = pipeline.OpCode.STR
    # print(MEM_syntax.parseString('r0, #6'))
    # endregion MEM test
    # endregion MEM parsing

    # region B parsing
    B_syntax = mem_access_syntax  # the condition codes are handled by instruction_syntax

    # endregion B parsing

    # region NOOP parsing
    def check_NOOP():
        return cur_instruction == pipeline.OpCode.NOOP or cur_instruction == pipeline.OpCode.END

    NOOP_syntax = whitespace[...] | ~whitespace

    # region NOOP test
    # print('NOOP test')
    # cur_instruction = pipeline.OpCode.END
    # print(NOOP_syntax.parseString(''))
    # cur_instruction = pipeline.OpCode.NOOP
    # print(NOOP_syntax.parseString(''))
    # endregion NOOP test
    # endregion NOOP parsing

    instruction_syntax = \
        mnemonic_syntax + \
        (
                CMP_syntax ^  # CMP
                MOV_syntax ^  # MOV
                NOT_syntax ^  # NOT
                ALU_syntax ^  # ALU
                MEM_syntax ^  # Memory (LDR/STR)
                B_syntax ^  # B/BL
                NOOP_syntax
        )

    # region instruction test
    # print('Instruction test')
    
    # print(instruction_syntax.parseString('CMP r1, r2'))
    # print(instruction_syntax.parseString('CMP r1, 0xbeef'))
    # print(instruction_syntax.parseString('MOV r1, r2'))
    # print(instruction_syntax.parseString('MOV r1, 0xbeef'))
    # print(instruction_syntax.parseString('NOT r1, r2'))
    # print(instruction_syntax.parseString('LDR r1, [r2]'))
    # print(instruction_syntax.parseString('STR r3, #4'))

    # parsed = instruction_syntax.parseString('END')
    # parsed_dict = dict(parsed)
    # print(parsed_dict)
    # result = pipeline.NOOP_Instruction.encoding(val=parsed_dict)
    # print(f'{result._bits:032b}')

    # parsed = instruction_syntax.parseString('NOOP')
    # parsed_dict = dict(parsed)
    # print(parsed_dict)
    # result = pipeline.NOOP_Instruction.encoding(val=parsed_dict)
    # print(f'{result._bits:032b}')
    # endregion instruction test

    # endregion instruction parsing

    return instruction_syntax.parseString(line)


if __name__ == '__main__':
    # print(parse_line('B [r0]'))
    # print(parse_line('B [r0, #0xC0FFEE]'))
    # print(parse_line('BEQ [r0, #0xC0FFEE]'))
    # print(parse_line('B #0xC0FFEE'))
    # print(parse_line('CMP r0, 0xDEAD'))
    # print(parse_line('CMP r2, r3'))

    # print(parse_line('NOT r2, r3 '))
    # print(parse_line('NOT r2, r3 ')['opcode'])
    # print(parse_line('NOT r2, r3 ')['dest'])
    # print(parse_line('NOT r2, r3 ')['op1'])
    # print(parse_line('NOT r2, r3 ')['lit'])
    # print(parse_line('NOT r2, r3 ')['literal'])

    # print(parse_line('MOV r2, r3 '))
    # print(parse_line('MOV r2, r3 ')['opcode'])
    # print(parse_line('MOV r2, r3 ')['dest'])
    # print(parse_line('MOV r2, r3 ')['op1'])
    # print(parse_line('MOV r2, r3 ')['lit'])
    # print(parse_line('MOV r2, r3 ')['literal'])

    # print(parse_line('ADD r2, r3, 0xC0FFEE '))
    # print(parse_line('ADD r2, r3, 0xC0FFEE ')['opcode'])
    # print(parse_line('ADD r2, r3, 0xC0FFEE ')['dest'])
    # print(parse_line('ADD r2, r3, 0xC0FFEE ')['op1'])
    # print(parse_line('ADD r2, r3, 0xC0FFEE ')['lit'])
    # print(parse_line('ADD r2, r3, 0xC0FFEE ')['literal'])

    # print(parse_line('ADD r2, r3, r4 '))
    # print(parse_line('ADD r2, r3, r4 ')['opcode'])
    # print(parse_line('ADD r2, r3, r4 ')['dest'])
    # print(parse_line('ADD r2, r3, r4 ')['op1'])
    # print(parse_line('ADD r2, r3, r4 ')['lit'])
    # print(parse_line('ADD r2, r3, r4 ')['op2'])

    # print(parse_line('BL [r4] '))
    # print(parse_line('BL [r4] ')['opcode'])
    # print(parse_line('BL [r4] ')['cond'])
    # print(parse_line('BL [r4] ')['imm'])
    # print(parse_line('BL [r4] ')['base'])
    # print(parse_line('BL [r4] ')['offset'])

    parsed = parse_line('STR R0, #6')
    print(parsed)
    print(parsed['opcode'])
    print(parsed['src'])
    print(parsed['imm'])
    print(parsed['immediate'])
    pipeline.STR_Instruction.encoding.encode(dict(parsed))
    print(encoded)

    # parse_line('')

    # arg_parse = ArgumentParser()
    # arg_parse.add_argument('source', type=str)
    # arg_parse.add_argument('-o', type=str, metavar='destination', dest='destination')

    # args = arg_parse.parse_args()

    # dest = args.destination
    # if dest is not None:
    #     out_file = open(dest, 'w+')
    # else:
    #     out_file = sys.stdout

    # with open(args.source, 'r') as in_file:
    #     for line in in_file:
    #         # parse the line
    #         parsed = parse_line(line)

    #         # get the instruction encoding
    #         cur_encoding = pipeline.Instructions[parsed['opcode']].encoding

    #         # pass the results to the encoding
    #         parsed_dict = dict(parsed)
    #         result = cur_encoding(val=parsed_dict)

    #         print(f'{result._bits:032b}', file=out_file)

    # print(f'compiled {args.source} to {"stdout" if dest is None else dest}')
