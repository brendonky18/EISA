from __future__ import annotations
from enum import Enum
from bit_vectors import BitVector
from typing import Type, Union, Dict, Callable, List
from eisa import EISA

class InstructionType:
    """Wrapper class for an instruction type (add, subtract, load, store, etc.), 
    it's associated encoding, 
    and function calls within the various pipeline stages
    """

    #region Instruction Encodings
    # NOOP
    Encoding = BitVector.create_subtype('InstructionEncoding', 32)
    Encoding.add_field('opcode', 26, 6)
    
    # LDR, STR
    MEM_Encoding = Encoding.create_subtype('MEM_Encoding')
    MEM_Encoding.add_field('offset', 0, 10)\
    .add_field('reg', 10, 5)

    # LDR
    LDR_Encoding = MEM_Encoding.create_subtype('LDR_Encoding')
    LDR_Encoding.add_field('dest', 21, 5)

    # STR
    STR_Encoding = MEM_Encoding.create_subtype('STR_Encoding')
    STR_Encoding.add_field('src', 21, 5)

    # B, BL
    B_Encoding = MEM_Encoding.create_subtype('B_Encoding')
    B_Encoding.add_field('offset', 0, 10)\
    .add_field('reg', 10, 5)\
    .add_field('imm', 15, 1)\
    .add_field('V', 22, 1)\
    .add_field('C', 23, 1)\
    .add_field('Z', 24, 1)\
    .add_field('N', 25, 1)
    
    # TODO: Push, Pop, and all AES instructions
    #endregion Instruction Encodings

    mnemonic: str
    encoding: Type[BitVector]
        
    def __init__(self, mnemonic: str, e_func: Callable[[Instruction], None], m_func: Callable[[Instruction], None], w_func: Callable[[Instruction], None]):
        """creates a new InstructionType

        Parameters
        ----------
        mnemonic : str
            the mnemonic correspondin to the opcode
        e_func : Callable[[Instruction], None]
            the function to be called an instruction of this type reaches the execute stage
        m_func : Callable[[Instruction], None]
            the function to be called an instruction of this type reaches the memory
        w_func : Callable[[Instruction], None]
            the function to be called when an instruction of this type reaches the writeback stage
        """
        self.mnemonic = mnemonic
        self.encoding = InstructionType.Encoding
        self.execute_stage_cb = e_func
        self.memory_stage_cb = m_func
        self.writeback_stage_cb = w_func

    def execute_stage_func(self, instruction: Instruction) -> None:
        self.execute_stage_cb(instruction)
        

    def memory_stage_func(self, instruction: Instruction) -> None:
        self.memory_stage_cb(instruction)

    def writeback_stage_func(self, instruction: Instruction) -> None:
        self.writeback_stage_cb(instruction)

class ALU_InstructionType(InstructionType):
    # ADD, SUB, CMP, MULT, DIV, MOD, LSL, LSR, ASR, AND, XOR, ORR, NOT
    ALU_Encoding = InstructionType.Encoding.create_subtype('ALU_Encoding') 
    ALU_Encoding.add_field('immediate', 0, 15, overlap=True)\
    .add_field('op2', 10, 5, overlap=True)\
    .add_field('imm', 15, 1)\
    .add_field('op1', 16, 5)\
    .add_field('dest', 21, 5)

    def __init__(self, mnemonic: str, e_func_cb: Callable[[int, int], int]):
        def e_func(instruction: Instruction) -> None:
            instruction.computed = e_func_cb(instruction['op1'], instruction['op2'])

        def m_func(instruction: Instruction) -> None:
            pass # TODO implement what should be done at the memory stage

        def w_func(instruction: Instruction) -> None:
            pass # TODO implement what sbould be done at the writeback stage

        super().__init__(mnemonic, e_func, m_func, w_func)

        self.encoding = InstructionType.Encoding

# dictionary mapping the opcode number to an instruction type
# this is where each of the instruction types and their behaviors are defined
OpCode_InstructionType_lookup: List[InstructionType] = [
    InstructionType('NOOP', lambda _: None, lambda _: None, lambda _: None),
    ALU_InstructionType('ADD', lambda op1, op2: op1 + op2),
    ALU_InstructionType('SUB', lambda op1, op2: op1 - op2),
    ALU_InstructionType('MULT', lambda op1, op2: op1 * op2),
    ALU_InstructionType('DIV', lambda op1, op2: op1 // op2),
    ALU_InstructionType('MOD', lambda op1, op2: op1 % op2),
    ALU_InstructionType('LSL', lambda op1, op2: op1 << op2),
    ALU_InstructionType('LSR', lambda op1, op2: (op1 & EISA.WORD_MASK) >> op2),
    ALU_InstructionType('ASR', lambda op1, op2: op1 >> op2),
    ALU_InstructionType('AND', lambda op1, op2: op1 & op2),
    ALU_InstructionType('XOR', lambda op1, op2: op1 ^ op2),
    ALU_InstructionType('ORR', lambda op1, op2: op1 | op2),
    # TODO implement the rest of the instructions
    #LDR
    #STR
    #PUSH
    #POP
    #MOVAK
    #LDRAK
    #STRAK
    #PUSAK
    #POPAK
    #AESE
    #AESD
    #AESMC
    #AESIC
    #AESSR
    #AESIR
    #AESGE
    #AESDE
    #CMP
    #B
    #BL
    #END
]

class DecodeError(Exception):
    message: str
    def __init__(self, message: str='Instruction has not been decoded yet'):
        self.message = message

    def __str__(self):
        return self.message

class Instruction:
    """class for an instance of an instruction, containing the raw encoded bits of the instruction, as well as helper functions for processing the instruction at the different pipeline stages
    """

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
    computed: Union[int, None] # will be none unless set by the pipeline

    # Determine whether opB is immediate
    # Currently obsolete
    _immediate: int

    _encoded: int
    _decoded: Union[BitVector, None] # will be none, until the instruction has been decoded

    # values for dependencies, defaults to None if there are no dependencies
    output: Union[int, None] # register that the instruction writes to
    inputs: Union[List[int], None] # list of registers that the instruction reads from

    _opcode: int
    _instruction_type: InstructionType
    def __init__(self, encoded: int):
        """creates a new instance of an instruction

        Parameters
        ----------
        encoded : int
            the encoded bits corresponding to the instruction
        """
        self._encoded = encoded
        self._decoded = None

        self.output = None
        self.inputs = None

    def decode(self):
        """helper function which decodes the instruction
        """

        # encodes the instruction in order to get the opcode
        self._decoded = InstructionType.Encoding(self._encoded)
        self._opcode = self._decoded['opcode']
                
        #  parse the rest of the encoded information according to the specific encoding pattern of the instruction type
        self._decoded = self._instruction_type.encoding(self._encoded)

        # TODO add function to update the instruction's dependencies 

    def __str__(self):
        out = ''
        nl = '\n'
        if self._decoded is None:
            out = f'raw bits: {self._encoded:0{2+32}b}{nl}instruction has not been decoded yet'
        else:
            out = str(self._decoded)

        return out

    def __getitem__(self, field: str) -> int:
        """gets the value of the specified field

        Parameters
        ----------
        field : str
            the field name

        Returns
        -------
        int, None
            the value of the field, or None if the field does not exist (possibly because the instruction has not been decoded yet)
        """
        if self._decoded is None:
            raise DecodeError
        else:
            return self._decoded[field]

    def __setitem__(self, field: str, value: int) -> None:
        if self._decoded is None:
            raise DecodeError
        else:
            self._decoded[field] = value