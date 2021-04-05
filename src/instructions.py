from __future__ import annotations

from typing import Type, Union, Callable, List
from bit_vectors import BitVector
from eisa import EISA
from pipeline import PipeLine


# dictionary mapping the opcode number to an instruction type
# this is where each of the instruction types and their behaviors are defined


class DecodeError(Exception):
    message: str
    def __init__(self, message: str='Instruction has not been decoded yet'):
        self.message = message

    def __str__(self):
        return self.message

#region Instruction Types
class InstructionType:
    """Wrapper class for a generic instruction type (add, subtract, load, store, etc.), 
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
    .add_field('base', 10, 5)

    # LDR
    LDR_Encoding = MEM_Encoding.create_subtype('LDR_Encoding')
    LDR_Encoding.add_field('dest', 21, 5)

    # STR
    STR_Encoding = MEM_Encoding.create_subtype('STR_Encoding')
    STR_Encoding.add_field('src', 21, 5)
    
    # TODO: Push, Pop, and all AES instructions
    #endregion Instruction Encodings

    mnemonic: str
    encoding: Type[BitVector]
        
    def __init__(self, mnemonic: str, e_func: Callable[[Instruction, PipeLine], None]=lambda _: None, m_func: Callable[[Instruction, PipeLine], None]=lambda _: None, w_func: Callable[[Instruction, PipeLine], None]=lambda _: None):
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

    def execute_stage_func(self, instruction: Instruction, pipeline: PipeLine) -> None:
        self.execute_stage_cb(instruction, pipeline)

    def memory_stage_func(self, instruction: Instruction, pipeline: PipeLine) -> None:
        self.memory_stage_cb(instruction, pipeline)

    def writeback_stage_func(self, instruction: Instruction, pipeline: PipeLine) -> None:
        self.writeback_stage_cb(instruction, pipeline)

class ALU_InstructionType(InstructionType):
    """Wrapper class for the ALU instructions:
        ADD, SUB, CMP, MULT, DIV, MOD, LSL, LSR, ASR, AND, XOR, ORR, NOT
    """
    ALU_Encoding = InstructionType.Encoding.create_subtype('ALU_Encoding') 
    ALU_Encoding.add_field('immediate', 0, 15, overlap=True)\
    .add_field('op2', 10, 5, overlap=True)\
    .add_field('imm', 15, 1)\
    .add_field('op1', 16, 5)\
    .add_field('dest', 21, 5)

    def __init__(self, mnemonic: str, ALU_func: Callable[[int, int], int]):
        """creates a new ALU instruction type

        Parameters
        ----------
        mnemonic : str
            the mnemonic corresponding to the opcode
        ALU_func : Callable[[int, int], int]
            the ALU operation to be performed in the execute stage
        """

        super().__init__(mnemonic, self._e_func, self._m_func, self._w_func)

        self.encoding = InstructionType.Encoding
        self._ALU_func = ALU_func

    def _e_func(self, instruction: Instruction, pipeline: Pipeline) -> None:
        instruction.computed = self._ALU_func(instruction['op1'], instruction['op2'])

    def _m_func(self, instruction: Instruction, pipeline: Pipeline) -> None:
        pass # TODO implement what should be done at the memory stage

    def _w_func(self, instruction: Instruction, pipeline: Pipeline) -> None:
        pass # TODO implement what sbould be done at the writeback stage

class CMP_InstructionType(ALU_InstructionType):
    """wrapper class for the CMP instruction
    """
    
    def __init__(self, mnemonic: str, CMP_func: Callable[[int, int], int]):
        self.mnemonic = mnemonic
        self._CMP_func = CMP_func

    def _e_func(self, instruction: Instruction, pipeline: PipeLine) -> None:
        res = self._CMP_func(instruction['op1'], instruction['op2'])

        # unsigned 32 bit number, stores negative numbers in 2's complement form
        # u32_res = (res + 2**(EISA.WORD_SIZE - 1)) & (2**(EISA.WORD_SIZE - 1) - 1) | (int(res < 0) << (EISA.WORD_SIZE - 1))

        pipeline['n'] = bool(res & (0b1 << (EISA.WORD_SIZE - 1))) # gets the sign bit (bit 31)
        pipeline['z'] = res == 0
        pipeline['c'] = res >= EISA.WORD_SPACE
        
        # I know this isn't very ~boolean zen~ but it's more readable so stfu
        signed_overflow = False
        if res <= -2**(EISA.WORD_SIZE - 1): # less than the minimum signed value
            signed_overflow = True
        elif res >= 2**(EISA.WORD_SIZE - 1):
            signed_overflow = True

        pipeline['v'] = signed_overflow

class B_InstructionType(InstructionType):
    """wrapper class for the branch instructions:
        B{cond}, BL{cond}
    """
    # B, BL
    B_Encoding = InstructionType.Encoding.create_subtype('B_Encoding')
    B_Encoding.add_field('offset', 0, 10)\
    .add_field('base', 10, 5)\
    .add_field('imm', 15, 1)\
    .add_field('V', 22, 1)\
    .add_field('C', 23, 1)\
    .add_field('Z', 24, 1)\
    .add_field('N', 25, 1)

    def __init__(self, mnemonic: str, on_branch: Callable[[], None]=lambda: None):
        """creates a new branch instruction type

        Parameters
        ----------
        mnemonic : str
            the mnemonic corresponding to the opcode
        on_branch : Callable[[], None]
            callback determining what happens when a branch occurs, 
            i.e. whether the link register should be updated
        """
        # TODO: define behavior for branch instruction
        def e_func(instruction: Instruction, pipeline: PipeLine):
            take_branch = instruction['n'] == pipeline.condition_flags['n'] and \
                          instruction['z'] == pipeline.condition_flags['z'] and \
                          instruction['c'] == pipeline.condition_flags['c'] and \
                          instruction['v'] == pipeline.condition_flags['v']
                         
            # squash the pipeline
            pipeline.squash()

            # perform the other behavior (ie. update the link register)
            on_branch()

            # calculate the new target address
            target_address = 0b0
            if instruction['imm']: # immediate value used, PC relative
                target_address = instruction['offset'] + pipeline._pc
            else: # no immediate, register indirect used
                base_reg = instruction['base']
                target_address = instruction['offset'] + pipeline._registers[base_reg]

            # update the program counter
            pipeline._pc = target_address

        def m_func(instruction: Instruction):
            pass
        def w_func(instruction: Instruction):
            pass
        super().__init__(mnemonic, e_func, m_func, w_func)
#endregion Instruction Types

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

    # value assigned by scoreboard indicating what row this instruction is present in
    #   in the scoreboard
    _scoreboard_index: int

    _pipeline: PipeLine
    def __init__(self, encoded: int):
        """creates a new instance of an instruction

        Parameters
        ----------
        encoded : int
            the encoded bits corresponding to the instruction
        """
        self._scoreboard_index = -1
        
        self._encoded = encoded
        self._decoded = None

        self.output = None
        self.inputs = None

        # init values required by ui.py
        self._opcode = -1
        self._regA = -1
        self._regB = -1
        self._regC = -1
        self._opA = -1
        self._opB = -1
        self._opC = -1
        self.computed = -1
        

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

OpCode_InstructionType_lookup: List[InstructionType] = [
    InstructionType('NOOP'),
    ALU_InstructionType('ADD', lambda op1, op2: op1 + op2),
    ALU_InstructionType('SUB', lambda op1, op2: op1 - op2),
    CMP_InstructionType('CMP', lambda op1, op2: op1 - op2),
    ALU_InstructionType('MULT', lambda op1, op2: op1 * op2),
    ALU_InstructionType('DIV', lambda op1, op2: op1 // op2),
    ALU_InstructionType('MOD', lambda op1, op2: op1 % op2),
    ALU_InstructionType('LSL', lambda op1, op2: op1 << op2),
    ALU_InstructionType('LSR', lambda op1, op2: (op1 & EISA.WORD_MASK) >> op2),
    ALU_InstructionType('ASR', lambda op1, op2: op1 >> op2),
    ALU_InstructionType('AND', lambda op1, op2: op1 & op2),
    ALU_InstructionType('XOR', lambda op1, op2: op1 ^ op2),
    ALU_InstructionType('ORR', lambda op1, op2: op1 | op2),
    # TODO implement the rest of the instructions, implemented as NOOPs currently
    InstructionType('LDR'),
    InstructionType('STR'),
    InstructionType('PUSH'),
    InstructionType('POP'),
    InstructionType('MOVAK'),
    InstructionType('LDRAK'),
    InstructionType('STRAK'),
    InstructionType('PUSAK'),
    InstructionType('POPAK'),
    InstructionType('AESE'),
    InstructionType('AESD'),
    InstructionType('AESMC'),
    InstructionType('AESIC'),
    InstructionType('AESSR'),
    InstructionType('AESIR'),
    InstructionType('AESGE'),
    InstructionType('AESDE'),
    B_InstructionType('B'),
    InstructionType('BL'), # TODO implement
    InstructionType('END')
]