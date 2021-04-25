from __future__ import annotations
# from queue import *
from collections import deque
from typing import Dict, Type, Union, Callable, List, Optional, Any
from eisa import EISA
from bit_vectors import BitVector
from eisa import EISA
from memory_subsystem import MemorySubsystem, PipelineStall
# from clock import Clock
# from clock import sleep
from functools import reduce
from threading import Lock
import enum


class Queue(deque):
    """Custom implementation of a FIFO queue with push and pop functions since Python is stupid
    """

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
    """Exception raised when attempting to access a field of an instruction that has not been decoded
    """
    message: str

    def __init__(self, message: str = 'Instruction has not been decoded yet'):
        self.message = message

    def __str__(self):
        return self.message


class PipeLine:
    """The pipeline for the simulation
    """

    # TODO - Implement branch squashing
    # _clock: Clock

    _memory: MemorySubsystem
    _pipeline: list[Instruction]
    _pipeline_lock: Lock

    _stalled_fetch = False
    _stalled_memory = False
    _dependency_stall = False
    _start_stall = False
    _stall_finished = False
    _fetch_isWaiting = False

    _cycles: int

    # N, Z, C, V flags
    condition_flags: Dict[str, bool]

    # region registers
    # general purpose registers
    _registers: list[int]  # TODO refactor '_registers' to 'registers'
    _active_registers: list[bool]

    # AES registers
    # TODO

    # Hash registers
    # TODO

    # special registers
    # program counter
    _pc: int  # TODO refactor '_pc' to 'pc' to make it a public variable
    # link register
    LR: int
    # Stack pointer
    SP: int
    # ALU register
    AR: int  # TODO implement the ALU register with dependencies, rather than using the 'computed' field in 'Instruction'

    # Has to be size 2
    _fd_reg: list[Instruction]  # Fetch/Decode reg
    _de_reg: list[Instruction]  # Decode/Execute reg
    _em_reg: list[Instruction]  # Execute/Memory reg
    _mw_reg: list[Instruction]  # Memory/Writeback reg

    # endregion registers

    def __init__(self, pc: int, registers: list[int], memory: MemorySubsystem):
        """creates an instance of a pipeline

        Parameters
        ----------
        pc : int
            the initial value of the program counter
        registers : list[int]
            the initial values of all the registers
        memory : MemorySubsystem
            a reference to the memory subsystem that the pipeline will read from/write to
        """
        # self._clock = Clock()
        self._registers = registers
        self._active_registers = [False for i in range(len(registers))]

        self._pc = pc
        self.LR = 0
        self.SP = 255

        self._memory = memory

        self._pipeline = [Instruction(self) for i in range(5)]
        self._pipeline_lock = Lock()

        self._stalled_fetch = False
        self._stalled_memory = False
        self._dependency_stall = False
        self._start_stall = False
        self._stall_finished = False
        self._fetch_isWaiting = False

        self._is_finished = False

        self._fd_reg = [Instruction(self), Instruction(self)]
        self._de_reg = [Instruction(self), Instruction(self)]
        self._em_reg = [Instruction(self), Instruction(self)]
        self._mw_reg = [Instruction(self), Instruction(self)]
        self._cycles = 0
        self.condition_flags = {
            'n': False,
            'z': False,
            'c': False,
            'v': False
        }

    # region dependencies
    def check_active_dependency(self, reg_addr: Union[int, List[int]]) -> bool:
        """function that will tell the decode stage if a register is in use.
        If so the register should pass a NoOp forward until the register is released.

        Parameters
        ----------
        reg_addr : int or List[int]
            the register/list of registers to check the status of

        Returns
        -------
        bool
            True if the register is used by another instruction,
            False if the register can be used
        """

        # converts from an int to a list 
        if isinstance(reg_addr, int):
            reg_addr_list = [reg_addr]
        else:
            reg_addr_list = reg_addr

        if len(reg_addr_list) != 0:
            for reg in reg_addr_list:
                if self._active_registers[reg]:
                    return True

        return False

    def get_dependency(self, reg_addr: int) -> int:
        """function that will get the value stored in the dependent register so that it can be used in the execute stage

        Parameters
        ----------
        reg_addr : int
            the register to get the data from

        Returns
        -------
        int
            the data stored at the register
        """

        return self._registers[reg_addr]

    def claim_dependency(self, reg_addr: Union[int, List[int]]) -> None:
        """function that claims a register as a dependency so that it cannot be used by other instructions

        Parameters
        ----------
        reg_addr : int or List[int]
            the register/list of registers to claim
        """
        if isinstance(reg_addr, int):
            reg_addr_list = [reg_addr]
        else:
            reg_addr_list = reg_addr

        if reg_addr_list != []:
            for cur_reg_addr in reg_addr_list:
                if self._active_registers[cur_reg_addr]:
                    raise RuntimeError(
                        f'Cannot claim register {cur_reg_addr} as a dependency, it has already been claimed by another instruction')

                self._active_registers[cur_reg_addr] = True

    def free_dependency(self, reg_addr: Union[int, List[int]]) -> None:
        """function that frees a register so that it can be used by other instructions

        Parameters
        ----------
        reg_addr : int or List[int]
            the register/list of registers to free
        """
        if isinstance(reg_addr, int):
            reg_addr_list = [reg_addr]
        else:
            reg_addr_list = reg_addr

        if reg_addr_list != []:
            for cur_reg_addr in reg_addr_list:
                self._active_registers[cur_reg_addr] = False

    # endregion dependencies

    # Destination of new program counter
    def squash(self, newPC: int) -> None:
        """function that squashed the pipeline on a branch and updates the program counter

        Parameters
        ----------
        newPC : int
            the new value of the program counter
        """
        self._pipeline[0] = Instruction(self)
        self._pipeline[1] = Instruction(self)
        self._fd_reg = [Instruction(self), Instruction(self)]
        self._de_reg = [Instruction(self), Instruction(self)]
        self._pc = newPC - 1  # NOTE - Max added -1 here because fetch increments the PC at the end of the cycle, so
                              #   so the -1 prevents ending up 1 word past where we're supposed to branch to

        active_regs = [i for i in range(len(self._active_registers)) if self._active_registers[i]]

        self.free_dependency(active_regs)

    def stage_fetch(self) -> None:
        """function to run the fetch stage
        """

        instruction = Instruction(self)

        if self._fetch_isWaiting:
            instruction = self._pipeline[0]

        # Load instruction in MEMORY at the address the PC is pointing to
        if not self._is_finished and not self._fetch_isWaiting:
            try:
                instruction = Instruction(self, encoded=self._memory[self._pc])
            except PipelineStall:
                # instruction = Instruction() # send noop forward on a pipeline stall
                self._stalled_fetch = True
            else:
                self._stalled_fetch = False
                self._fetch_isWaiting = True

        self._pipeline[0] = instruction

        if not self._stalled_fetch and not self._stalled_memory and not self._dependency_stall and not self._is_finished:
            self._fd_reg[0] = instruction
            self._pc += 1
            self._fetch_isWaiting = False

    def stage_decode(self) -> None:
        """function to run the decode stage
        """
        # get fetched instruction
        instruction = self._fd_reg[1]

        if self._stalled_memory or self._dependency_stall:
            instruction = self._pipeline[1]

        self._pipeline[1] = instruction

        # Decode the instruction
        instruction.__class__ = Instructions[instruction.opcode] # TODO, this is probably a violation of the Geneva convention
        instruction.decode()

        # if the instruction is END, flag the pipeline to tell it to not load anymore instructions
        if instruction['opcode'] == 0b100000:
            self._de_reg[0] = instruction
            self._is_finished = True
            return

        if not self._stalled_memory:
            dependencies = instruction.dependencies()
            if self.check_active_dependency(dependencies):
                # waiting for another instruction to release the dependency
                self._de_reg[0] = Instruction(self)  # stall, pass forward NoOp
                self._dependency_stall = True
            else:
                # can proceed
                self.claim_dependency(dependencies)
                self._de_reg[0] = instruction
                self._dependency_stall = False

    def stage_execute(self) -> None:
        """function to run the execute stage
        """
        # get decoded instruction
        instruction = self._de_reg[1]

        if self._stalled_memory:
            instruction = self._pipeline[2]

        self._pipeline[2] = instruction

        # Execute depending on instruction
        # https://en.wikipedia.org/wiki/Classic_RISC_pipeline

        # run the execute stage
        instruction.execute_stage_func()

        # Push edited instruction into the adjacent queue
        self._em_reg[0] = instruction

    def stage_memory(self):
        """function to run the memory stage
        """
        # get executed instruction
        instruction = self._em_reg[1]

        if self._stalled_memory:
            instruction = self._pipeline[3]

        self._pipeline[3] = instruction

        # run the memory stage
        try:
            instruction.memory_stage_func()
        except PipelineStall:
            if not self._stalled_memory:
                self._start_stall = True
            # instruction = Instruction() # send a NOOP forward
            self._mw_reg[0] = Instruction(self)
        else:
            self._mw_reg[0] = instruction
            if self._stalled_memory:
                self._stall_finished = True

        # Push instruction into the adjacent queue
        # self._mw_reg[0] = instruction

    def stage_writeback(self):
        """function to run the writeback stage
        """
        # get memorized instruction
        instruction = self._mw_reg[1]

        self._pipeline[4] = instruction

        # run the memory stage
        instruction.writeback_stage_func()

        # free the dependencies
        self.free_dependency(instruction.dependencies())

    def cycle_stage_regs(self):
        """function to advance the instructions within the dual registers between each pipeline stage
        """
        self._mw_reg = [self._em_reg[1], self._mw_reg[0]]
        if not self._stalled_memory:
            self._em_reg = [self._de_reg[1], self._em_reg[0]]
            self._de_reg = [self._fd_reg[1], self._de_reg[0]]
            # if not self._stalled_memory and not self._dependency_stall:
            self._fd_reg = [Instruction(self), self._fd_reg[0]]

    def cycle_pipeline(self):
        """function to run a single cycle of the pipeline - NOT THREADSAFE -> Call cycle(int cycles) instead
        """
        # self._stalled_fetch = False
        # self._stalled_memory = False

        # self._mw_reg = [self._em_reg[1], self._mw_reg[0]]
        self.stage_writeback()
        self.stage_memory()
        # self._mw_reg = [self._em_reg[1], self._mw_reg[0]]

        # if not self._stalled_memory:
        self.stage_execute()
        # self._em_reg = [self._de_reg[1], self._em_reg[0]]

        self.stage_decode()
        # self._de_reg = [self._fd_reg[1], self._de_reg[0]]

        self.stage_fetch()

        # self._fd_reg = [Instruction(), self._fd_reg[0]]

        self.cycle_stage_regs()

        # Memory stall flags during cycles
        if self._start_stall:
            self._stalled_memory = True
            self._start_stall = False

        if self._stall_finished:
            self._stalled_memory = False
            self._stall_finished = False

        # if self._stalled_memory:
        #    self._stall_prior_stages = True

        self._cycles += 1
        # self.cycle_stage_regs()

    def cycle(self, cycle_count: int):
        """run the pipeline for a number of cycles

        Parameters
        ----------
        cycle_count : int
            the number of cycles to run for
        """

        # only allow the pipeline to be run in a single thread
        for i in range(cycle_count):
            self.cycle_pipeline()

    def __str__(self) -> str:
        """pipeline to string function

        Returns
        -------
        str
            string representation of the pipeline
        """
        nl = '\n'

        out = f"PC: {self._pc}\n"
        out += f"Regs: {self._registers}\n"
        for i in range(len(self._pipeline)):
            out += f"Stage {i}:\n {str(self._pipeline[i])}{nl}"

        return out


class OpCode(enum.IntEnum):
    NOOP  = 0b000000
    ADD   = 0b000001
    MOV   = 0b000001  # MOV is an alias for ADD 0
    SUB   = 0b000010
    CMP   = 0b000011
    MULT  = 0b000100
    DIV   = 0b000101
    MOD   = 0b000110
    LSL   = 0b000111
    LSR   = 0b001000
    ASR   = 0b001001
    AND   = 0b001010
    XOR   = 0b001011
    NOT   = 0b001011  # NOT is an alias for XOR 1
    ORR   = 0b001100
    LDR   = 0b001101
    STR   = 0b001110
    PUSH  = 0b001111
    POP   = 0b010000
    MOVAK = 0b010001
    LDRAK = 0b010010
    STRAK = 0b010011
    PUSAK = 0b010100
    POPAK = 0b010101
    AESE  = 0b010110
    AESD  = 0b010111
    AESMC = 0b011000
    AESIC = 0b011001
    AESSR = 0b011010
    AESIR = 0b011011
    AESGE = 0b011100
    AESDE = 0b011101
    B     = 0b011110
    BL    = 0b011111
    END   = 0b100000

    def __contains__(self, item):
        return item in self._member_names_
# endregion Instruction Types

@enum.unique
class ConditionCode(enum.IntEnum):
    EQ = 0b0000 # EQ meaning Equal with Zero flag set.
    NE = 0b0001 # NE meaning Not equal with the Zero clear.
    CS = 0b0010 # CS meaning Carry set or HS meaning unsigned higher or same with Carry set.
    CC = 0b0011 # CC meaning Carry clear or LO meaning unsigned lower with Carry clear.
    MI = 0b0100 # MI meaning Minus or negative with the Negative flag set.
    PL = 0b0101 # PL meaning Plus (including zero) with the Negative flag clear.
    VS = 0b0110 # VS meaning Overflow with the Overflow flag set.
    VC = 0b0111 # VC meaning No overflow with the Overflow clear.
    HI = 0b1000 # HI meaning an Unsigned higher with Carry set AND Zero clear.
    LS = 0b1001 # LS meaning Unsigned lower or same with Carry clear AND Zero set.
    GE = 0b1010 # GE meaning Signed greater than or equal with Negative equal to Overflow.
    LT = 0b1011 # LT meaning Signed less than with Negative not equal to Overflow.
    GT = 0b1100 # GT meaning Signed greater than with Zero clear AND Negative equal to Overflow.
    LE = 0b1101 # LE meaning Signed less than or equal with Zero set AND Negative not equal to Overflow.
    AL = 0b1110 # AL meaning Always. If there is no conditional part in assembler this encoding is used.
    # NV = 0b1111 # NV meaning Never; this is historical and deprecated, but for ARMv3 it meant never. Ie a nop. For newer ARMs (ARMv5+), this extends the op-code range.

# TODO refactor InstructionType into the Instruction class
class Instruction:
    """class for an instance of an instruction, 
    containing the raw encoded bits of the instruction, 
    as well as helper functions for processing the instruction at the different pipeline stages
    """
    # region instance vars
    # Result for addition instructions, or loaded value if a load instruction
    computed: int  # will be none unless set by the pipeline
    opcode: int

    # Determine whether opB is immediate
    # Currently obsolete
    _immediate: int

    _encoded: int
    _decoded: BitVector  # will be none, until the instruction has been decoded

    # values for dependencies, defaults to None if there are no dependencies
    output_reg: int  # register that the instruction writes to
    input_regs: List[int]  # list of registers that the instruction reads from

    _pipeline: PipeLine
    # endregion instance vars

    def __init__(self, pipeline: PipeLine, encoded: Optional[int] = None, fields: Optional[Dict[str, int]] = None):
        """creates a new instance of an instruction

        Parameters
        ----------
        pipeline: PipeLine
            a reference to the pipeline which the instruction will be handled by
        encoded : Optionals[int]
            the encoded bits corresponding to the instruction
            will default to 0b0 (No Op) if value is not assigned
        fields: Optional[Dict[str, int]]
            the fields which will attempt to be assigned
        """

        self._scoreboard_index = -1

        self._pipeline = pipeline

        self._encoded = 0b0 if encoded is None else encoded  # sets instruction to NOOP if encoded value is not specified
        self._decoded = None  # type: ignore

        # calculate the opcode
        self.opcode = type(self).encoding(self._encoded)['opcode']

        # the instruction's dependencies
        self.output_reg = None  # type: ignore
        self.input_regs = []  # type: ignore
        self.computed = None  # type: ignore

    def decode(self) -> None:
        """helper function which decodes the instruction
        """

        # parse the rest of the encoded information according to the specific encoding pattern of the instruction type
        self._decoded = type(self).encoding(self._encoded)

        # update the instruction's output dependencies
        self.output_reg = self.try_get('dest')

        # update the instruction's input dependencies
        self.input_regs.append(src) if (src := self.try_get(
            'src')) is not None else None  # append src t~o input_regs if the field exists
        op1 = self.try_get('op1')
        op2 = self.try_get('op2')
        self.input_regs.append(op2) if op2 is not None else None
        self.input_regs.append(op1) if op1 is not None else None


    def dependencies(self) -> List[int]:
        """returns a list instance containing all of the instruction's depenedencies, both input and output dependencies

        Returns
        -------
        List[int]
            the list of registers that the instruction will read/write 
        """

        d_regs = self.input_regs.copy()
        d_regs.append(self.output_reg) if self.output_reg is not None else None

        return list(set(d_regs))

    def try_get(self, field: str) -> int:
        """tries to get the value from the specified field

        Parameters
        ----------
        field : str
            the target field

        Returns
        -------
        int
            the value of the field if the instruction was found
        None
            if the instruction was not found
        """
        try:
            return self[field]
        except KeyError:
            return None  # type: ignore

    def __str__(self) -> str:
        out = ''
        nl = '\n'
        if self._decoded is None:
            out = f'raw bits: {self._encoded:0{2 + 32}b}{nl}instruction has not been decoded yet'
        else:
            out = str(self._decoded)

        return out

    def __getitem__(self, field: str) -> int:
        """gets the value of the specified field

        Parameters
        ----------
        field : str
            the field name

        Raises
        ------
        DecodeError
            if a field access is being attempted before the instruction has been decoded

        Returns
        -------
        int
            the value of the field, or None if the field does not exist (possibly because the instruction has not been decoded yet)
        """

        # Commented the error out for easier use with UI
        if self._decoded is None:
            raise DecodeError(f'{self._encoded} has not been decoded yet')
        else:
            return self._decoded[field]

    def __setitem__(self, field: str, value: int) -> None:
        """sets the value of the specified field

        Parameters
        ----------
        field : str
            the field name
        value : int
            the value to assign

        Raises
        ------
        DecodeError
            if a field assignment is being attempted before the instruction has been decoded
        """
        if self._decoded is None:
            raise DecodeError
        else:
            self._decoded[field] = value

    def execute_stage_func(self) -> None:
        """the defines the behavior of the instruction in the execute stage

        Parameters
        ----------
        instruction : Instruction
            reference to the instruction's values
        pipeline : PipeLine
            reference to the pipeline that the instruction is from
        """
        pass

    def memory_stage_func(self) -> None:
        """the defines the behavior of the instruction in the memory stage

        Parameters
        ----------
        instruction : Instruction
            reference to the instruction's values
        pipeline : PipeLine
            reference to the pipeline that the instruction is from
        """
        pass

    def writeback_stage_func(self) -> None:
        """the defines the behavior of the instruction in the writeback stage

        Parameters
        ----------
        instruction : Instruction
            reference to the instruction's values
        pipeline : PipeLine
            reference to the pipeline that the instruction is from
        """
        pass
     
    # region class vars
    mnemonic: str = ''

    encoding = BitVector.create_subtype('InstructionEncoding', 32)
    encoding.add_field('opcode', 26, 6)
    # endregion class vars

    @classmethod
    def create_instruction(cls, mnemonic: str):
        return type(f'{mnemonic}_Instruction', (cls,), {'mnemonic': mnemonic})
 
class ALU_Instruction(Instruction):
    encoding = Instruction.encoding.create_subtype('InstructionEncoding', 32)
    encoding \
        .add_field('immediate', 0, 15, overlap=True) \
        .add_field('op2', 10, 5, overlap=True) \
        .add_field('imm', 15, 1) \
        .add_field('op1', 16, 5) \
        .add_field('dest', 21, 5)

    @staticmethod 
    def _ALU_func(x: int, y: int) -> int:
        raise NotImplementedError

    @classmethod
    def create_instruction(cls, mnemonic: str, ALU_func: Callable[[int, int], int]): # type: ignore
        return type(f'{mnemonic}_Instruction', (cls,), {
            'mnemonic': mnemonic,
            '_ALU_func': ALU_func
        })

    def execute_stage_func(self) -> None:
        """get's the two operands and performs the ALU operation
        """
        val1 = self._pipeline.get_dependency(self['op1'])

        if self['imm']:
            # immediate value used
            val2 = self['immediate']
        else:
            # register direct
            val2 = self._pipeline.get_dependency(self['op2'])

        self.computed = type(self)._ALU_func(val1, val2)

    def writeback_stage_func(self) -> None:
        """write's the computed result to the destination register  
        """
        self._pipeline._registers[self['dest']] = self.computed

class CMP_Instruction(ALU_Instruction):
    encoding = ALU_Instruction.encoding.create_subtype('CMP_Encoding')
    encoding.remove_field('dest')

    @staticmethod
    def _CMP_func(x: int, y: int) -> int:
        raise NotImplementedError

    @classmethod
    def create_instruction(cls, mnemonic: str, CMP_func: Callable[[int, int], int]): # type: ignore
        return type(f'{mnemonic}_Instruction', (cls,), {
            'mnemonic': mnemonic,
            '_CMP_func': CMP_func
        })

    def execute_stage_func(self) -> None:
        """performs the specified ALU operation, and uses the result to set the pipeline's condition flags
        """
        res = type(self)._CMP_func(self['op1'], self['op2'])

        self._pipeline.condition_flags['n'] = bool(res & (0b1 << (EISA.WORD_SIZE - 1)))  # gets the sign bit (bit 31)
        self._pipeline.condition_flags['z'] = res == 0
        self._pipeline.condition_flags['c'] = res >= EISA.WORD_SPACE

        # I know this isn't very ~boolean zen~ but it's more readable so stfu
        signed_overflow = False
        if res <= -2 ** (EISA.WORD_SIZE - 1):  # less than the minimum signed value
            signed_overflow = True
        elif res >= 2 ** (EISA.WORD_SIZE - 1):  # greater than the maximum signed value
            signed_overflow = True

        self._pipeline.condition_flags['v'] = signed_overflow

    # override inherited function because CMP does not writeback it's result
    def writeback_stage_func(self) -> None:
        pass

class B_Instruction(Instruction):
    """wrapper class for the branch instructions:
        B{cond}, BL{cond}
    """
    # B, BL
    encoding = Instruction.encoding.create_subtype('B_Encoding')
    encoding \
        .add_field('immediate', 0, 15, overlap=True) \
        .add_field('offset', 0, 10, overlap=True) \
        .add_field('base', 10, 5, overlap=True) \
        .add_field('imm', 15, 1) \
        .add_field('cond', 22, 4) 

    @staticmethod
    def _on_branch():
        raise NotImplementedError

    @classmethod
    def create_instruction(cls, mnemonic: str, on_branch: Callable[[], None] = lambda: None):
        """creates a new branch instruction type

        Parameters
        ----------
        mnemonic : str
            the mnemonic corresponding to the opcode
        on_branch : Callable[[], None]
            callback determining what happens when a branch occurs, 
            i.e. whether the link register should be updated
        """
        return type(f'{mnemonic}_Instruction', (cls,), {
            'mnemonic': mnemonic,
            '_on_branch': on_branch
        })

    def execute_stage_func(self):
        """compares the branch's condition code to that of the pipeline to determine if the branch should be taken.
        Squashes the pipeline if the branch is taken
        """

        # defines all the different ways of evaluating the different condition codes
        # too bad python doesn't have switch statements
        eval_branch: Dict[ConditionCode, Callable[[], bool]] = {
            ConditionCode.EQ: lambda: self._pipeline.condition_flags['Z'] == 1,
            ConditionCode.NE: lambda: self._pipeline.condition_flags['Z'] == 0,
            ConditionCode.CS: lambda: self._pipeline.condition_flags['C'] == 1,
            ConditionCode.CC: lambda: self._pipeline.condition_flags['C'] == 0,
            ConditionCode.MI: lambda: self._pipeline.condition_flags['N'] == 1,
            ConditionCode.PL: lambda: self._pipeline.condition_flags['N'] == 0,
            ConditionCode.VS: lambda: self._pipeline.condition_flags['V'] == 1,
            ConditionCode.VC: lambda: self._pipeline.condition_flags['V'] == 0,
            ConditionCode.HI: lambda: self._pipeline.condition_flags['C'] == 1 and self._pipeline.condition_flags['Z'] == 0,
            ConditionCode.LS: lambda: self._pipeline.condition_flags['C'] == 0 or  self._pipeline.condition_flags['Z'] == 1,
            ConditionCode.GE: lambda: self._pipeline.condition_flags['N'] == self._pipeline.condition_flags['V'],
            ConditionCode.LT: lambda: self._pipeline.condition_flags['N'] != self._pipeline.condition_flags['V'],
            ConditionCode.GT: lambda: self._pipeline.condition_flags['Z'] == 0 and self._pipeline.condition_flags['N'] == self._pipeline.condition_flags['V'],
            ConditionCode.LE: lambda: self._pipeline.condition_flags['Z'] == 1 or  self._pipeline.condition_flags['N'] != self._pipeline.condition_flags['V'],
            ConditionCode.AL: lambda: True
        }

        if eval_branch[ConditionCode(self['cond'])]:
            # perform the other behavior (ie. update the link register)
            type(self)._on_branch()

            # calculate the target address for the new program counter
            target_address = 0b0
            if self['imm']:  # immediate value used, PC relative
                target_address = self['offset'] + pipeline._pc
            else:  # no immediate, register indirect used
                base_reg = self['base']
                target_address = self['offset'] + self._pipeline.get_dependency(base_reg)

            # squash the pipeline
            self._pipeline.squash(target_address)

class MEM_Instruction(Instruction):
    # LDR, STR
    encoding = Instruction.encoding.create_subtype('MEM_Encoding')
    encoding \
        .add_field('offset', 0, 10) \
        .add_field('base', 10, 5)

    @classmethod
    def create_instruction(cls, mnemonic: str):
        return type(f'{mnemonic}_Instruction', (cls,), {
            'mnemonic': mnemonic,
        })

class LDR_Instruction(MEM_Instruction):
    # LDR
    encoding = MEM_Instruction.encoding.create_subtype('LDR_Encoding')
    encoding \
        .add_field('literal', 0, 15, overlap=True) \
        .add_field('lit', 15, 1) \
        .add_field('dest', 21, 5)

    def memory_stage_func(self) -> None:
        """calculates the memory address from which a value should be loaded and 
        gets that value from memory
        """

        if self['lit'] == 1:  # contains a literal value
            self.computed = self['literal']
        else:  # uses register direct + offset
            # calculate the address
            base_addr_reg = self['base']
            src_addr = self._pipeline._registers[base_addr_reg] + self['offset']

            # read from that address
            self.computed = self._pipeline._memory[src_addr]

    def writeback_stage_func(self) -> None:
        """writes the value we got from memory into the specified register
        """
        self._pipeline._registers[self['dest']] = self.computed

class STR_Instruction(MEM_Instruction):
    # STR
    encoding = MEM_Instruction.encoding.create_subtype('STR_Encoding')
    encoding.add_field('src', 21, 5)

    def memory_stage_func(self) -> None:
        """calulates the memory address to which a value should be stored and
        loads that value into memory
        """

        # calculate the address
        base_addr_reg = self['base']
        dest_addr = self._pipeline._registers[base_addr_reg] + self['offset']

        # get the value to write
        src_val = self._pipeline._registers[self['src']]

        # write to that address
        self._pipeline._memory[dest_addr] = src_val

"""dictionary mapping the opcode number to an instruction type
this is where each of the instruction types and their behaviors are defined
"""
Instructions: List[Type[Instruction]] = [
    Instruction.create_instruction('NOOP'),
    ALU_Instruction.create_instruction('ADD', lambda op1, op2: op1 + op2),
    ALU_Instruction.create_instruction('SUB', lambda op1, op2: op1 - op2),
    CMP_Instruction.create_instruction('CMP', lambda op1, op2: op1 - op2),
    ALU_Instruction.create_instruction('MULT', lambda op1, op2: op1 * op2),
    ALU_Instruction.create_instruction('DIV', lambda op1, op2: op1 // op2),
    ALU_Instruction.create_instruction('MOD', lambda op1, op2: op1 % op2),
    ALU_Instruction.create_instruction('LSL', lambda op1, op2: op1 << op2),
    ALU_Instruction.create_instruction('LSR', lambda op1, op2: (op1 & EISA.WORD_MASK) >> op2),
    ALU_Instruction.create_instruction('ASR', lambda op1, op2: op1 >> op2),
    ALU_Instruction.create_instruction('AND', lambda op1, op2: op1 & op2),
    ALU_Instruction.create_instruction('XOR', lambda op1, op2: op1 ^ op2),
    ALU_Instruction.create_instruction('ORR', lambda op1, op2: op1 | op2),
    LDR_Instruction.create_instruction('LDR'),
    STR_Instruction.create_instruction('STR'),
    Instruction.create_instruction('PUSH'),# TODO implement the rest of the instructions, implemented as NOOPs currently
    Instruction.create_instruction('POP'),
    Instruction.create_instruction('MOVAK'),
    Instruction.create_instruction('LDRAK'),
    Instruction.create_instruction('STRAK'),
    Instruction.create_instruction('PUSAK'),
    Instruction.create_instruction('POPAK'),
    Instruction.create_instruction('AESE'),
    Instruction.create_instruction('AESD'),
    Instruction.create_instruction('AESMC'),
    Instruction.create_instruction('AESIC'),
    Instruction.create_instruction('AESSR'),
    Instruction.create_instruction('AESIR'),
    Instruction.create_instruction('AESGE'),
    Instruction.create_instruction('AESDE'),
    B_Instruction.create_instruction('B'),
    B_Instruction.create_instruction('BL'),  # TODO implement
    Instruction.create_instruction('END')
]