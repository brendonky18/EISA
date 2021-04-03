from enum import Enum
from bit_vectors import BitVector
from typing import Type

class OpCodes(Enum):
    NOOP     = 0b000000
    LSL      = 0b000001
    LSR      = 0b000010
    ASR      = 0b000011
    MOV      = 0b000100
    ADD      = 0b000101
    SUB      = 0b000110
    CMP      = 0b000111
    MULT     = 0b001000
    DIV      = 0b001001
    MOD      = 0b001010
    AND      = 0b001011
    XOR      = 0b001100
    ORR      = 0b001101
    MVN      = 0b001110
    LDR      = 0b001111
    STR      = 0b010000
    PUSH     = 0b010001
    POP      = 0b010010
    MOVAK    = 0b010011
    LDRAK    = 0b010100
    STRAK    = 0b010101
    PUSAK    = 0b010110
    POPAK    = 0b010111
    AESE     = 0b011000
    AESD     = 0b011001
    AESMC    = 0b011010
    AESIC    = 0b011011
    AESSR    = 0b011100
    AESIR    = 0b011101
    AESGE    = 0b011110
    AESDE    = 0b011111
    B        = 0b100000
    BL       = 0b100001
    END      = 0b100010

    @staticmethod
    def format(opcode: OpCodes):
        # NOOP
        BVInstruction = BitVector.create_subtype('BVInstruction', 32)
        BVInstruction.add_field('opcode', 26, 6)
        
        # ADD, SUB, CMP, MULT, DIV, MOD, LSL, LSR, ASR, AND, XOR, ORR, MVN
        ALUInstruction = BVInstruction.create_subtype('ALUInstruction') 
        ALUInstruction.add_field('immediate', 0, 10)\
        .add_field('op2', 10, 5)\
        .add_field('imm', 15, 1)\
        .add_field('op1', 16, 5)\
        .add_field('dest', 21, 5)

        # MOV
        MOVInstruction = ALUInstruction.create_subtype('MOVInstruction')
        MOVInstruction.rename_field('op1', 'src')\
        .remove_field('imm')\
        .remove_field('op2')\
        .remove_field('immediate')

        # LDR, STR
        MEMInstruction = BVInstruction.create_subtype('MEMInstruction')
        MEMInstruction.add_field('offset', 0, 10)\
        .add_field('reg', 10, 5)

        # LDR
        LDRInstruction = BVInstruction.create_subtype('LDRInstruction')
        LDRInstruction.add_field('dest', 21, 5)

        # STR
        STRInstruction = BVInstruction.create_subtype('STRInstruction')
        STRInstruction.add_field('src', 21, 5)

        # B, BL
        BInstruction = BVInstruction.create_subtype('BInstruction')
        BInstruction.add_field('offset', 0, 10)\
        .add_field('reg', 10, 5)\
        .add_field('imm', 15, 1)\
        .add_field('V', 22, 1)\
        .add_field('C', 23, 1)\
        .add_field('Z', 24, 1)\
        .add_field('N', 25, 1)
        
        # TODO: Push, Pop, and all AES instructions

        format_map = {
            OpCodes.NOOP  : BVInstruction,      
            OpCodes.MOV   : MOVInstruction,  
            OpCodes.ADD   : ALUInstruction,  
            OpCodes.SUB   : ALUInstruction,  
            OpCodes.CMP   : ALUInstruction,  
            OpCodes.MULT  : ALUInstruction,      
            OpCodes.DIV   : ALUInstruction,  
            OpCodes.MOD   : ALUInstruction,  
            OpCodes.LSL   : ALUInstruction,  
            OpCodes.LSR   : ALUInstruction,  
            OpCodes.ASR   : ALUInstruction,  
            OpCodes.AND   : ALUInstruction,  
            OpCodes.XOR   : ALUInstruction,  
            OpCodes.ORR   : ALUInstruction,  
            OpCodes.MVN   : ALUInstruction,  
            OpCodes.LDR   : LDRInstruction,  
            OpCodes.STR   : STRInstruction,  
            OpCodes.PUSH  : None,      
            OpCodes.POP   : None,  
            OpCodes.MOVAK : None,      
            OpCodes.LDRAK : None,      
            OpCodes.STRAK : None,      
            OpCodes.PUSAK : None,      
            OpCodes.POPAK : None,      
            OpCodes.AESE  : None,      
            OpCodes.AESD  : None,      
            OpCodes.AESMC : None,      
            OpCodes.AESIC : None,      
            OpCodes.AESSR : None,      
            OpCodes.AESIR : None,      
            OpCodes.AESGE : None,      
            OpCodes.AESDE : None,      
            OpCodes.B     : BInstruction,  
            OpCodes.BL    : BInstruction
        }

        return format_map[opcode]


class Instruction:
    # Register addresses (raw values provided to instruction)
    _regA: int # Param 1 of instruction
    _regB: int # Param 2 of instruction
    _regC: int # Param 3 of instruction (most likely immediate value)

    # Operands (values loaded assuming register addresses in regA,regB,regC)
    # If regA-regC are not register addresses, ignore these vars
    _opA: int # Value retrieved from reg A
    _opB: int # Value retrieved from reg B
    _opC: int # Value retrieved from reg C

    # Result for addition instructions, or loaded value if a load instruction
    _computed: None

    # Determine whether opB is immediate
    # Currently obsolete
    _immediate: int

    _encoded: BitVector

    _opcode: OpCodes
    def __init__(self, encoded: int):
        self._encoded = BitVector()
        self._computed = None
        self._immediate = 0
        self._opcode = OpCodes.NOOP
        self._regA = -1
        self._regB = -1
        self._regC = -1

    def decode(self):
        if self._opcode == OpCodes.NOOP:
            return
        
        self._opcode = self._encoded = OpCodes.format(self._opcode)
        # self._regA = (self._encoded >> 2 * EISA.GP_NUM_FIELD_BITS) & EISA.GP_REGS_BITS
        # self._regB = (self._encoded >> EISA.GP_NUM_FIELD_BITS) & EISA.GP_REGS_BITS
        # self._regC = self._encoded & EISA.GP_REGS_BITS
        # self._immediate = (self._encoded >> 15) & 1

    def __str__(self):
        encoded_string = format(self._encoded, "#034b")[2:]
        out = "BEGIN INSTRUCTION\n"
        out += f"Encoded: {encoded_string}\n"
        out += f"Opcode: {self._opcode}\n"
        out += f"Param 1: {encoded_string[17:22]}:{self._regA}\n"
        out += f"Param 2: {encoded_string[22:27]}:{self._regB}\n"
        out += f"Param 3: {encoded_string[27:]}:{self._regC}\n"
        out += "END INSTRUCTION\n"
        return out
