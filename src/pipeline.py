from __future__ import annotations
#from queue import *
from collections import deque
from typing import Dict, Type, Union, Callable, List, Optional
from eisa import EISA
from bit_vectors import BitVector
from eisa import EISA
from memory_subsystem import MemorySubsystem, PipelineStall
from clock import Clock

class Queue(deque):

    def __init__(self, maxsize):
        super().__init__([], maxsize)

    def put(self, object):
        self.append(object)

    def get(self):
        return self.popleft()

    def peek(self):
        if len(self) == 0:
            return None
        return self[0]

class DecodeError(Exception):
    message: str
    def __init__(self, message: str='Instruction has not been decoded yet'):
        self.message = message

    def __str__(self):
        return self.message

class PipeLine:
    # TODO - Use dict later to get funcs associated with opcodes
    # TODO - Implement branching and branch squashing
    # TODO - implement no-ops and stalls

    _clock: Clock

    _memory: MemorySubsystem
    _pipeline: list[Instruction]
    
    _cycles: int
    
    # N, Z, C, V flags
    condition_flags: Dict[str, bool] 

    #region registers
    # general purpose registers
    _registers: list[int] # TODO refactor '_registers' to 'registers'

    # AES registers
        # TODO

    # Hash registers
        # TODO

    # special registers
    # program counter
    _pc: int # TODO refactor '_pc' to 'pc' to make it a public variable
    # link register
    lr: int
    # ALU register
    ar: int # TODO implement the ALU register with dependencies, rather than using the 'computed' field in 'Instruction'

    # Has to be size 2
    _fd_reg: list[Instruction] # Fetch/Decode reg
    _de_reg: list[Instruction] # Decode/Execute reg
    _em_reg: list[Instruction] # Execute/Memory reg
    _mw_reg: list[Instruction] # Memory/Writeback reg
    #endregion registers

    def __init__(self, pc: int, registers: list[int], memory: MemorySubsystem):
        self._clock = Clock()
        self._registers = registers
        self._pc = pc
        self._memory = memory
        self._pipeline = [Instruction() for i in range(5)]
        self._fd_reg = [Instruction(), Instruction()]
        self._de_reg = [Instruction(), Instruction()]
        self._em_reg = [Instruction(), Instruction()]
        self._mw_reg = [Instruction(), Instruction()]
        self._cycles = 0
        self._condition_flags = {
            'n': 0,
            'z': 0,
            'c': 0,
            'v': 0
        }

    # Destination of new program counter
    def squash(self, newPC: int):
        self._pipeline[0] = Instruction()
        self._pipeline[1] = Instruction()
        self._fd_reg = [Instruction(), Instruction()]
        self._de_reg = [Instruction(), Instruction()]
        self._pc = newPC
        self.cycle(2)

    def stage_fetch(self):
        # Load instruction in MEMORY at the address the PC is pointing to
        try:
            instruction = Instruction(self._memory[self._pc])
        except PipelineStall:
            instruction = Instruction() # send noop forward on a pipeline stall

        self._pipeline[0] = instruction

        # increment PC by 1 word
        self._pc += 1

        # push instruction into queue
        #self._pipeline[0] = instruction
        self._fd_reg[0] = instruction

    def stage_decode(self):

        # get fetched instruction
        instruction = self._fd_reg[1]

        self._pipeline[1] = instruction

        # Decode the instruction
        instruction.decode()

        self._scoreboard.enqueue_instruction(instruction)

    def stage_execute(self):

        # get decoded instruction
        instruction = self._scoreboard.get_next_valid_instruction()

        self._pipeline[2] = instruction

        # Execute depending on instruction
        # https://en.wikipedia.org/wiki/Classic_RISC_pipeline

        # get the instruction type of the instruction
        instruction_type = OpCode_InstructionType_lookup[instruction['opcode']]
        
        # run the execute stage
        instruction_type.execute_stage_func(instruction, self)

        # Push edited instruction into the adjacent queue
        self._em_reg[0] = instruction

    def stage_memory(self):

        # get executed instruction
        instruction = self._em_reg[1]

        # get the instruction type of the instruction
        instruction_type = OpCode_InstructionType_lookup[instruction['opcode']]
        
        # run the memory stage
        try:
            instruction_type.memory_stage_func(instruction, self)
        except PipelineStall:
            self._mw_reg = Instruction() # send a NOOP forward
        else:
            # Push edited instruction into the adjacent queue
            self._mw_reg[0] = instruction

    def stage_writeback(self):

        # get memorized instruction
        instruction = self._mw_reg[1]

        self._pipeline[4] = instruction

        # get the instruction type of the instruction
        instruction_type = OpCode_InstructionType_lookup[instruction['opcode']]
        
        # run the memory stage
        instruction_type.writeback_stage_func(instruction, self)

    def cycle_stage_regs(self):

        # TODO - Test whether putting no ops into 0th elements provides same results
        self._fd_reg = [Instruction(), self._fd_reg[0]]
        self._de_reg = [self._fd_reg[1], self._de_reg[0]]
        self._em_reg = [self._de_reg[1], self._em_reg[0]]
        self._mw_reg = [self._em_reg[1], self._mw_reg[0]]

    def cycle_pipeline(self):

        # TODO - Process one step in the pipeline

        '''
        self.stage_fetch()
        self.stage_decode()
        self.stage_execute()
        self.stage_memory()
        self.stage_writeback()
        self._cycles += 1
        self.cycle_stage_regs()
        '''
        self.stage_writeback()
        self.stage_memory()
        self.stage_execute()
        self.stage_decode()
        self.stage_fetch()
        if not(self._scoreboard._isempty):
            self._scoreboard.update_scoreboard(self._pipeline[4]._scoreboard_index)
        self._cycles += 1
        self.cycle_stage_regs()
        self._pc += 1

    def cycle(self, x):
        for i in range(x):
            self.cycle_pipeline()
            self._clock.wait(1, wait_event_name='pipeline cycle')

    def __str__(self):
        nl = '\n'

        out = f"PC: {self._pc}\n"

        out += f"Regs: {self._registers}\n"

        for i in range(len(self._pipeline)):
            out += f"Stage {i}:\n {str(self._pipeline[i])}{nl}"

        return out
        '''
        print(f"Fetch:{self._pipeline[0].opcode}->[{self.fd_reg[0]._opcode},{self.fd_reg[1]._opcode}]"
              f"->Decode:{self._pipeline[1].opcode}->[{self.de_reg[0]._opcode},{self.de_reg[1]._opcode}]"
              f"->Execute:{self._pipeline[2].opcode}->[{self.em_reg[0]._opcode},{self.em_reg[1]._opcode}]"
              f"->Memory:{self._pipeline[3].opcode}->[{self.mw_reg[0]._opcode},{self.mw_reg[1]._opcode}]"
              f"->Memory:{self._pipeline[4].opcode}")
        '''

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
    
    # TODO: Push, Pop, and all AES instructions
    #endregion Instruction Encodings

    mnemonic: str
    encoding: Type[BitVector]
        
    def __init__(self, mnemonic: str, e_func: Callable[[Instruction, PipeLine], None]=lambda*args: None, m_func: Callable[[Instruction, PipeLine], None]=lambda *args: None, w_func: Callable[[Instruction, PipeLine], None]=lambda *args: None):
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

        self.encoding = ALU_InstructionType.ALU_Encoding
        self._ALU_func = ALU_func
    # TODO you can just override the function execute/memory/writeback_func, 
    # you don't need to pass it in the constructor you dumdum
    def _e_func(self, instruction: Instruction, pipeline: PipeLine) -> None:
        instruction.computed = self._ALU_func(instruction['op1'], instruction['op2'])

    def _m_func(self, instruction: Instruction, pipeline: PipeLine) -> None:
        pass # TODO implement what should be done at the memory stage

    def _w_func(self, instruction: Instruction, pipeline: PipeLine) -> None:
        pipeline._registers[instruction['dest']] = instruction.computed

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

        pipeline.condition_flags['n'] = bool(res & (0b1 << (EISA.WORD_SIZE - 1))) # gets the sign bit (bit 31)
        pipeline.condition_flags['z'] = res == 0
        pipeline.condition_flags['c'] = res >= EISA.WORD_SPACE
        
        # I know this isn't very ~boolean zen~ but it's more readable so stfu
        signed_overflow = False
        if res <= -2**(EISA.WORD_SIZE - 1): # less than the minimum signed value
            signed_overflow = True
        elif res >= 2**(EISA.WORD_SIZE - 1):
            signed_overflow = True

        pipeline.condition_flags['v'] = signed_overflow

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
                         
            # perform the other behavior (ie. update the link register)
            on_branch()

            # calculate the new target address
            target_address = 0b0
            if instruction['imm']: # immediate value used, PC relative
                target_address = instruction['offset'] + pipeline._pc
            else: # no immediate, register indirect used
                base_reg = instruction['base']
                target_address = instruction['offset'] + pipeline._registers[base_reg]

            # squash the pipeline
            pipeline.squash(target_address)

        def m_func(instruction: Instruction, pipeline: PipeLine):
            pass
        def w_func(instruction: Instruction, pipeline: PipeLine):
            pass
        super().__init__(mnemonic, e_func, m_func, w_func)

class MEM_InstructionType(InstructionType):
    # LDR, STR
    MEM_Encoding = InstructionType.Encoding.create_subtype('MEM_Encoding')
    MEM_Encoding.add_field('offset', 0, 10)\
    .add_field('base', 10, 5)

class LDR_InstructionType(MEM_InstructionType):
    # LDR
    LDR_Encoding = MEM_InstructionType.MEM_Encoding.create_subtype('LDR_Encoding')
    LDR_Encoding.add_field('literal', 0, 15, overlap=True)\
                .add_field('lit', 15, 1)\
                .add_field('dest', 21, 5)

    def __init__(self, mnemonic: str):
        self.mnemonic = mnemonic

    def memory_stage_func(self, instruction: Instruction, pipeline: PipeLine) -> None:
        if instruction['l'] == 1: # contains a literal value
            instruction.computed = instruction['literal']
        else: # uses register direct + offset
            # calculate the address
            base_addr_reg = instruction['base']
            src_addr = pipeline._registers[base_addr_reg] + instruction['offset']

            # read from that address
            instruction.computed = pipeline._memory[src_addr]

    def writeback_stage_func(self, instruction: Instruction, pipeline: PipeLine) -> None:
        pipeline._registers[instruction['dest']] = instruction.computed

class STR_InstructionType(MEM_InstructionType):
    # STR
    STR_Encoding = MEM_InstructionType.MEM_Encoding.create_subtype('STR_Encoding')
    STR_Encoding.add_field('src', 21, 5)

    def __init__(self, mnemonic: str):
        self.mnemonic = mnemonic

    def memory_stage_func(self, instruction: Instruction, pipeline: PipeLine) -> None:
        # calculate the address
        base_addr_reg = instruction['base']
        dest_addr = pipeline._registers[base_addr_reg] + instruction['offset']

        # get the value to write
        src_val = pipeline._registers[instruction['src']]

        # write to that address
        pipeline._memory[dest_addr] = src_val


# dictionary mapping the opcode number to an instruction type
# this is where each of the instruction types and their behaviors are defined
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
    computed: int # will be none unless set by the pipeline

    # Determine whether opB is immediate
    # Currently obsolete
    _immediate: int

    _encoded: int
    _decoded: BitVector # will be none, until the instruction has been decoded

    # values for dependencies, defaults to None if there are no dependencies
    output: int # register that the instruction writes to
    inputs: List[int] # list of registers that the instruction reads from

    # value assigned by scoreboard indicating what row this instruction is present in
    #   in the scoreboard
    _scoreboard_index: int

    _pipeline: PipeLine
    def __init__(self, encoded: Optional[int]=None):
        """creates a new instance of an instruction

        Parameters
        ----------
        encoded : Optionals[int]
            the encoded bits corresponding to the instruction
            will default to 0b0 (No Op) if value is not assigned
        """
        self._scoreboard_index = -1
        
        self._encoded = 0b0 if encoded is None else encoded # sets instruction to NOOP if encoded value is not specified
        self._decoded = None # type: ignore

        self.output = None # type: ignore
        self.inputs = None # type: ignore

    def decode(self):
        """helper function which decodes the instruction
        """

        # encodes the instruction in order to get the opcode
        self._decoded = InstructionType.Encoding(self._encoded)
                
        #  parse the rest of the encoded information according to the specific encoding pattern of the instruction type
        self._decoded = OpCode_InstructionType_lookup[self._decoded['opcode']]

        # TODO add function to update the instruction's dependencies 

    def try_get(self, field: str):
        try:
            return self[field]
        except KeyError:
            return -1

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

        
        if InstructionType.Encoding(self._encoded)['opcode'] == 0b0: # ignore that noops are not decoded
            return 0
        elif self._decoded is None: 
            raise DecodeError(f'{self._encoded} has not been decoded yet')
        else:
            return self._decoded[field]

    def __setitem__(self, field: str, value: int) -> None:
        if self._decoded is None:
            raise DecodeError
        else:
            self._decoded[field] = value
