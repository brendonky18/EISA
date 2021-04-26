from argparse import ArgumentParser
from parse import parse
import pyparsing as pp
import sys
from typing import List
import pipeline

class AssemblerError(RuntimeError):
    def __init__(self, symbol):
        super().__init__()
        self.message = f'Unexpected symbol \'{symbol}\' was encountered'

    def __str__(self):
        return self.message


def parse_line(line: str) -> pp.ParseResults:
    # region mnemonic parsing
    conditional_instructions = [pipeline.OpCode.B.name, pipeline.OpCode.BL.name]
    alias_instructions = [pipeline.OpCode.MOV.name, pipeline.OpCode.NOT.name]
    mnemonic_tokens = \
        pp.oneOf([op for op in pipeline.OpCode.__members__ if op not in conditional_instructions and op not in alias_instructions]) ^ \
        pp.oneOf(alias_instructions)
    conditional_mnemonic_tokens = pp.oneOf(conditional_instructions) # B and BL

    cur_instruction = pipeline.OpCode.NOOP

    def get_instruction(cond_token):
        global cur_instruction
        cur_instruction = pipeline.OpCode[cond_token[0]]
        return cur_instruction

    mnemonic_tokens.setParseAction(get_instruction)
    conditional_mnemonic_tokens.setParseAction(get_instruction)

    whitespace = pp.White()

    condition_tokens = pp.Optional(~whitespace + pp.oneOf([cond.name for cond in pipeline.ConditionCode]), default='AL') # GT, LT, EQ, etc.
    condition_tokens.setParseAction(lambda cond_token: pipeline.ConditionCode[cond_token[0]])

    conditional_opcode_syntax = \
        conditional_mnemonic_tokens('opcode') + \
        condition_tokens('cond') # BEQ, BLGT etc.
        
    
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


    #endregion mnemonic parsing

    # region instruction parsing
    comma = pp.Suppress(',') # ignore commas in the final output

    register_num = pp.oneOf(' '.join([str(i) for i in range(32)])) # 0-31, automatically converts to int
    register_tokens = pp.Combine(pp.Suppress('r') + register_num) # registers r0-r31
    register_tokens.setParseAction(lambda num_str: int(num_str[0])) # automatically converts to integer

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

    literal_syntax.setParseAction(lambda num_str: int(num_str[0], 0)) # will autimatically convert to a number
    
    # checks if there is an operand, or a literal
    is_op = pp.FollowedBy(register_tokens).setParseAction(lambda x: False)
    is_lit = pp.FollowedBy(literal_syntax ^ whitespace[...]).setParseAction(lambda x: True)
    lit_or_op = (is_lit ^ is_op)

    # region lit or op test
    # print(lit_or_op.parseString('r2'))
    # print(lit_or_op.parseString('0b1111'))
    # print(lit_or_op.parseString(''))
    # endregion lit or op test

    def calc_op2(x):
        global cur_instruction
        immediate = -1
        if cur_instruction == pipeline.OpCode.NOT:
            immediate = 1
        elif cur_instruction == pipeline.OpCode.MOV:
            immediate = 0
        else:
            raise pp.ParseFatalException(f'Opcode {cur_instruction} is not \'NOT\' or \'XOR\'')
        
        return immediate

    operand_2 = \
        lit_or_op('lit') + \
        (
            (comma + register_tokens('op2')) | 
            (comma + literal_syntax('literal')) |
            whitespace[...].setParseAction(calc_op2).setResultsName('literal')
        )

    # region op 2 test
    # print('op 2 test')
    # print(operand_2.parseString(', r2'))
    # print(operand_2.parseString(', 0b1111'))
    # cur_instruction = pipeline.OpCode.MOV
    # print(operand_2.parseString(''))
    # cur_instruction = pipeline.OpCode.NOT
    # print(operand_2.parseString(''))
    # endregion op 2 test


    # [dest], [op1], [op2] or [lit]
    ALU_syntax = \
        register_tokens('dest') + \
        comma + register_tokens('op1') + \
        operand_2
        

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

    # region CMP parsing
    CMP_syntax =  \
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
            immediate_syntax.setResultsName('immediate') | 
            reg_mem_access_syntax
        )

    # region MEM test
    # print('MEM test')
    # print(mem_access_syntax.parseString('#420'))
    # print(mem_access_syntax.parseString('#0xbeef'))
    # print(mem_access_syntax.parseString('#0b1111'))
    # print(mem_access_syntax.parseString('[r0]'))
    # print(mem_access_syntax.parseString('[r0, #420]'))
    # print(mem_access_syntax.parseString('[r0 , #69]'))
    # endregion MEM test
    # region LDR parsing
    LDR_syntax = \
        register_tokens.setResultsName('dest') + \
        mem_access_syntax
    # endregion LDR parsing

    # region STR parsing
    STR_syntax = \
        register_tokens.setResultsName('src') + \
        mem_access_syntax
    # endregion STR parsing
    
    MEM_syntax = \
        (LDR_syntax | STR_syntax) + \
        mem_access_syntax
    # endregion MEM parsing

    # region B parsing
    B_syntax = mem_access_syntax # the condition codes are handled by instruction_syntax
    # endregion B parsing

    instruction_syntax = \
        mnemonic_syntax + \
        (
            ALU_syntax |            # ALU
            # CMP_syntax |            # CMP
            MEM_syntax |            # Memory (LDR/STR)
            B_syntax                # B/BL
        )

    # region instruction test
    # print('Instruction test')
    # print(instruction_syntax.parseString('BL [r0]'))
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
    print(parse_line('NOT r2, r3 '))
    print(parse_line('NOT r2, r3 ')['opcode'])
    print(parse_line('NOT r2, r3 ')['dest'])
    print(parse_line('NOT r2, r3 ')['op1'])
    print(parse_line('NOT r2, r3 ')['lit'])
    print(parse_line('NOT r2, r3 ')['literal'])

    print(parse_line('MOV r2, r3 '))
    print(parse_line('MOV r2, r3 ')['opcode'])
    print(parse_line('MOV r2, r3 ')['dest'])
    print(parse_line('MOV r2, r3 ')['op1'])
    print(parse_line('MOV r2, r3 ')['lit'])
    print(parse_line('MOV r2, r3 ')['literal'])

    print(parse_line('ADD r2, r3, 0xC0FFEE '))
    print(parse_line('ADD r2, r3, 0xC0FFEE ')['opcode'])
    print(parse_line('ADD r2, r3, 0xC0FFEE ')['dest'])
    print(parse_line('ADD r2, r3, 0xC0FFEE ')['op1'])
    print(parse_line('ADD r2, r3, 0xC0FFEE ')['lit'])
    print(parse_line('ADD r2, r3, 0xC0FFEE ')['literal'])

    print(parse_line('ADD r2, r3, r4 '))
    print(parse_line('ADD r2, r3, r4 ')['opcode'])
    print(parse_line('ADD r2, r3, r4 ')['dest'])
    print(parse_line('ADD r2, r3, r4 ')['op1'])
    print(parse_line('ADD r2, r3, r4 ')['lit'])
    print(parse_line('ADD r2, r3, r4 ')['op2'])

    print(parse_line('BL [r4] '))
    print(parse_line('BL [r4] ')['opcode'])
    print(parse_line('BL [r4] ')['cond'])
    print(parse_line('BL [r4] ')['imm'])
    print(parse_line('BL [r4] ')['base'])
    print(parse_line('BL [r4] ')['offset'])

    # parse the line
    line = ''
    parsed = parse_line(line)

    # get the instruction encoding
    cur_encoding = pipeline.Instructions[parsed['opcode']].encoding

    # pass the results to the encoding
    result = cur_encoding(fields=dict(parsed))

