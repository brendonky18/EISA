from __future__ import annotations
# from queue import *
from collections import deque
from typing import Dict, Type, Union, Callable, List, Optional
from eisa import EISA
from bit_vectors import BitVector
from eisa import EISA
from memory_subsystem import MemorySubsystem, PipelineStall
# from clock import Clock
# from clock import sleep
from functools import reduce
from threading import Lock


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
    lr: int
    # ALU register
    ar: int  # TODO implement the ALU register with dependencies, rather than using the 'computed' field in 'Instruction'

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

        self._memory = memory

        self._pipeline = [Instruction() for i in range(5)]
        self._pipeline_lock = Lock()

        self._stalled_fetch = False
        self._stalled_memory = False

        self._is_finished = False

        self._fd_reg = [Instruction(), Instruction()]
        self._de_reg = [Instruction(), Instruction()]
        self._em_reg = [Instruction(), Instruction()]
        self._mw_reg = [Instruction(), Instruction()]
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
        self._pipeline[0] = Instruction()
        self._pipeline[1] = Instruction()
        self._fd_reg = [Instruction(), Instruction()]
        self._de_reg = [Instruction(), Instruction()]
        self._pc = newPC

        active_regs = [i for i in range(len(self._active_registers)) if self._active_registers[i]]

        self.free_dependency(active_regs)

    def stage_fetch(self) -> None:
        """function to run the fetch stage
        """

        # TODO - Make it so that fetch retains the stalled instruction in pipeline[0]
        #   (i.e.) prevent noops from showing up in pipeline[0]

        instruction = Instruction()

        # Load instruction in MEMORY at the address the PC is pointing to
        if not self._is_finished and not self._stalled_memory:
            try:
                instruction = Instruction(self._memory[self._pc])
            except PipelineStall:
                self._stalled_fetch = True
                # instruction = Instruction() # send noop forward on a pipeline stall
            else:
                self._stalled_fetch |= False

        self._pipeline[0] = instruction

        self._fd_reg[0] = instruction

        if not self._stalled_fetch:
            self._pc += 1

    def stage_decode(self) -> None:
        """function to run the decode stage
        """
        # get fetched instruction
        instruction = self._fd_reg[1]

        self._pipeline[1] = instruction

        # Decode the instruction
        instruction.decode()

        # if the instruction is END, flag the pipeline to tell it to not load anymore instructions
        if instruction['opcode'] == 0b100000:
            self._de_reg[0] = instruction
            self._is_finished = True
            return

        if self._de_reg[0].opcode == 0:  # TODO

            # I put this if-statement in because instructions were being overwritten in the
            # 0th slot of the de reg. For some reason, instructions sometimes get stuck
            # in de_reg[0], and don't get cycled into de_reg[1], thus any op that gets
            # passed forward from decode to execute got overwritten randomly. Need to
            # fix this at some point, because there's likely a larger underlying issue
            # here, but I am leaving it as is for now to work on the UI.

            dependencies = instruction.dependencies()
            if self.check_active_dependency(dependencies):
                # waiting for another instruction to release the dependency
                self._de_reg[0] = Instruction()  # stall, pass forward NoOp
            else:
                # can proceed
                self.claim_dependency(dependencies)
                self._de_reg[0] = instruction

    def stage_execute(self) -> None:
        """function to run the execute stage
        """
        # get decoded instruction
        instruction = self._de_reg[1]

        self._pipeline[2] = instruction

        # Execute depending on instruction
        # https://en.wikipedia.org/wiki/Classic_RISC_pipeline

        # get the instruction type of the instruction
        instruction_type = OpCode_InstructionType_lookup[instruction.opcode]

        # run the execute stage
        instruction_type.execute_stage_func(instruction, self)

        # Push edited instruction into the adjacent queue

        self._em_reg[0] = instruction

    def stage_memory(self):
        """function to run the memory stage
        """
        # get executed instruction
        instruction = self._em_reg[1]

        self._pipeline[3] = instruction

        # get the instruction type of the instruction
        instruction_type = OpCode_InstructionType_lookup[instruction.opcode]

        # run the memory stage
        try:
            instruction_type.memory_stage_func(instruction, self)
        except PipelineStall:
            self._stalled_memory = True
            # instruction = Instruction() # send a NOOP forward
            self._mw_reg[0] = Instruction()
        else:
            self._mw_reg[0] = instruction

            self._stalled_memory |= False

        # Push instruction into the adjacent queue
        # self._mw_reg[0] = instruction

    def stage_writeback(self):
        """function to run the writeback stage
        """
        # get memorized instruction
        instruction = self._mw_reg[1]

        self._pipeline[4] = instruction

        # get the instruction type of the instruction
        instruction_type = OpCode_InstructionType_lookup[instruction.opcode]

        # run the memory stage
        instruction_type.writeback_stage_func(instruction, self)

        # free the dependencies
        self.free_dependency(instruction.dependencies())

    def cycle_stage_regs(self):
        """function to advance the instructions within the dual registers between each pipeline stage
        """
        # TODO - Test whether putting no ops into 0th elements provides same results
        self._mw_reg = [self._em_reg[1], self._mw_reg[0]]
        if not self._stalled_memory:
            self._em_reg = [self._de_reg[1], self._em_reg[0]]
            self._de_reg = [self._fd_reg[1], self._de_reg[0]]
            self._fd_reg = [Instruction(), self._fd_reg[0]]

    def cycle_pipeline(self):
        """function to run a single cycle of the pipeline - NOT THREADSAFE -> Call cycle(int cycles) instead
        """
        self._stalled_fetch = False
        self._stalled_memory = False

        # self._mw_reg = [self._em_reg[1], self._mw_reg[0]]
        self.stage_writeback()
        self.stage_memory()
        self._mw_reg = [self._em_reg[1], self._mw_reg[0]]

        if not self._stalled_memory:
            self.stage_execute()
            self._em_reg = [self._de_reg[1], self._em_reg[0]]

            self.stage_decode()
            self._de_reg = [self._fd_reg[1], self._de_reg[0]]

            self.stage_fetch()
            self._fd_reg = [Instruction(), self._fd_reg[0]]

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

        '''
        with self._pipeline_lock:
            for i in range(cycle_count):
                self._clock.wait(
                    1, 
                    wait_event_name='pipeline cycle', 
                    wait_event = self.cycle_pipeline
                )
        '''
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


# region Instruction Types
class InstructionType:
    """Wrapper class for a generic instruction type (add, subtract, load, store, etc.), 
    it's associated encoding, 
    and function calls within the various pipeline stages
    """

    # region Instruction Encodings
    # NOOP
    Encoding = BitVector.create_subtype('InstructionEncoding', 32)
    Encoding.add_field('opcode', 26, 6)

    # TODO: Push, Pop, and all AES instructions
    # endregion Instruction Encodings

    mnemonic: str
    encoding: Type[BitVector]

    def __init__(self, mnemonic: str):
        """creates a new InstructionType

        Parameters
        ----------
        mnemonic : str
        """
        self.mnemonic = mnemonic
        self.encoding = InstructionType.Encoding

    def execute_stage_func(self, instruction: Instruction, pipeline: PipeLine) -> None:
        """the defines the behavior of the instruction in the execute stage

        Parameters
        ----------
        instruction : Instruction
            reference to the instruction's values
        pipeline : PipeLine
            reference to the pipeline that the instruction is from
        """
        pass

    def memory_stage_func(self, instruction: Instruction, pipeline: PipeLine) -> None:
        """the defines the behavior of the instruction in the memory stage

        Parameters
        ----------
        instruction : Instruction
            reference to the instruction's values
        pipeline : PipeLine
            reference to the pipeline that the instruction is from
        """
        pass

    def writeback_stage_func(self, instruction: Instruction, pipeline: PipeLine) -> None:
        """the defines the behavior of the instruction in the writeback stage

        Parameters
        ----------
        instruction : Instruction
            reference to the instruction's values
        pipeline : PipeLine
            reference to the pipeline that the instruction is from
        """
        pass


class ALU_InstructionType(InstructionType):
    """Wrapper class for the ALU instructions:
        ADD, SUB, CMP, MULT, DIV, MOD, LSL, LSR, ASR, AND, XOR, ORR, NOT
    """
    ALU_Encoding = InstructionType.Encoding.create_subtype('ALU_Encoding')
    ALU_Encoding.add_field('immediate', 0, 15, overlap=True) \
        .add_field('op2', 10, 5, overlap=True) \
        .add_field('imm', 15, 1) \
        .add_field('op1', 16, 5) \
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

        super().__init__(mnemonic)

        self.encoding = ALU_InstructionType.ALU_Encoding
        self._ALU_func = ALU_func

    def execute_stage_func(self, instruction: Instruction, pipeline: PipeLine) -> None:
        """get's the two operands and performs the ALU operation
        """
        val1 = pipeline.get_dependency(instruction['op1'])

        if instruction['imm']:
            # immediate value used
            val2 = instruction['immediate']
        else:
            # register direct
            val2 = pipeline.get_dependency(instruction['op2'])

        instruction.computed = self._ALU_func(val1, val2)

    def writeback_stage_func(self, instruction: Instruction, pipeline: PipeLine) -> None:
        """write's the computed result to the destination register  
        """
        pipeline._registers[instruction['dest']] = instruction.computed


class CMP_InstructionType(ALU_InstructionType):
    """wrapper class for the CMP instruction
    """

    CMP_Encoding = ALU_InstructionType.ALU_Encoding.create_subtype('CMP_Encoding')
    CMP_Encoding.remove_field('dest')

    def __init__(self, mnemonic: str, CMP_func: Callable[[int, int], int]):
        self.mnemonic = mnemonic
        self._CMP_func = CMP_func
        self.encoding = CMP_InstructionType.CMP_Encoding

    def execute_stage_func(self, instruction: Instruction, pipeline: PipeLine) -> None:
        """performs the specified ALU operation, and uses the result to set the pipeline's condition flags
        """
        res = self._CMP_func(instruction['op1'], instruction['op2'])

        pipeline.condition_flags['n'] = bool(res & (0b1 << (EISA.WORD_SIZE - 1)))  # gets the sign bit (bit 31)
        pipeline.condition_flags['z'] = res == 0
        pipeline.condition_flags['c'] = res >= EISA.WORD_SPACE

        # I know this isn't very ~boolean zen~ but it's more readable so stfu
        signed_overflow = False
        if res <= -2 ** (EISA.WORD_SIZE - 1):  # less than the minimum signed value
            signed_overflow = True
        elif res >= 2 ** (EISA.WORD_SIZE - 1):  # greater than the maximum signed value
            signed_overflow = True

        pipeline.condition_flags['v'] = signed_overflow

    # override inherited function because CMP does not writeback it's result
    def writeback_stage_func(self, instruction: Instruction, pipeline: PipeLine) -> None:
        pass


class B_InstructionType(InstructionType):
    """wrapper class for the branch instructions:
        B{cond}, BL{cond}
    """
    # B, BL
    B_Encoding = InstructionType.Encoding.create_subtype('B_Encoding')
    B_Encoding.add_field('immediate', 0, 15, overlap=True) \
        .add_field('offset', 0, 10, overlap=True) \
        .add_field('base', 10, 5, overlap=True) \
        .add_field('imm', 15, 1) \
        .add_field('v', 22, 1) \
        .add_field('c', 23, 1) \
        .add_field('z', 24, 1) \
        .add_field('n', 25, 1)

    on_branch: Callable[[B_InstructionType], None]

    def __init__(self, mnemonic: str, on_branch: Callable[[], None] = lambda: None):
        """creates a new branch instruction type

        Parameters
        ----------
        mnemonic : str
            the mnemonic corresponding to the opcode
        on_branch : Callable[[], None]
            callback determining what happens when a branch occurs, 
            i.e. whether the link register should be updated
        """

        super().__init__(mnemonic)
        self.on_branch = on_branch  # type: ignore
        #  mypy just doesn't like assigning to Callable but it's fine
        self.encoding = B_InstructionType.B_Encoding

    def execute_stage_func(self, instruction: Instruction, pipeline: PipeLine):
        """compares the branch's condition code to that of the pipeline to determine if the branch should be taken.
        Squashes the pipeline if the branch is taken
        """
        take_branch = instruction['n'] == pipeline.condition_flags['n'] and \
                      instruction['z'] == pipeline.condition_flags['z'] and \
                      instruction['c'] == pipeline.condition_flags['c'] and \
                      instruction['v'] == pipeline.condition_flags['v']

        # perform the other behavior (ie. update the link register)
        self.on_branch()

        # calculate the target address for the new program counter
        target_address = 0b0
        if instruction['imm']:  # immediate value used, PC relative
            target_address = instruction['offset'] + pipeline._pc
        else:  # no immediate, register indirect used
            base_reg = instruction['base']
            target_address = instruction['offset'] + pipeline.get_dependency(base_reg)

        # squash the pipeline
        pipeline.squash(target_address)


class MEM_InstructionType(InstructionType):
    # LDR, STR
    MEM_Encoding = InstructionType.Encoding.create_subtype('MEM_Encoding')
    MEM_Encoding.add_field('offset', 0, 10) \
        .add_field('base', 10, 5)

    def __init__(self, mnemonic: str):
        super().__init__(mnemonic)
        self.encoding = MEM_InstructionType.MEM_Encoding


class LDR_InstructionType(MEM_InstructionType):
    # LDR
    LDR_Encoding = MEM_InstructionType.MEM_Encoding.create_subtype('LDR_Encoding')
    LDR_Encoding.add_field('literal', 0, 15, overlap=True) \
        .add_field('lit', 15, 1) \
        .add_field('dest', 21, 5)

    def __init__(self, mnemonic: str):
        super().__init__(mnemonic)
        self.encoding = LDR_InstructionType.LDR_Encoding

    def memory_stage_func(self, instruction: Instruction, pipeline: PipeLine) -> None:
        """calculates the memory address from which a value should be loaded and 
        gets that value from memory
        """

        if instruction['lit'] == 1:  # contains a literal value
            instruction.computed = instruction['literal']
        else:  # uses register direct + offset
            # calculate the address
            base_addr_reg = instruction['base']
            src_addr = pipeline._registers[base_addr_reg] + instruction['offset']

            # read from that address
            instruction.computed = pipeline._memory[src_addr]

    def writeback_stage_func(self, instruction: Instruction, pipeline: PipeLine) -> None:
        """writes the value we got from memory into the specified register
        """
        pipeline._registers[instruction['dest']] = instruction.computed


class STR_InstructionType(MEM_InstructionType):
    # STR
    STR_Encoding = MEM_InstructionType.MEM_Encoding.create_subtype('STR_Encoding')
    STR_Encoding.add_field('src', 21, 5)

    def __init__(self, mnemonic: str):
        super().__init__(mnemonic)
        self.encoding = STR_InstructionType.STR_Encoding

    def memory_stage_func(self, instruction: Instruction, pipeline: PipeLine) -> None:
        """calulates the memory address to which a value should be stored and
        loads that value into memory
        """

        # calculate the address
        base_addr_reg = instruction['base']
        dest_addr = pipeline._registers[base_addr_reg] + instruction['offset']

        # get the value to write
        src_val = pipeline._registers[instruction['src']]

        # write to that address
        pipeline._memory[dest_addr] = src_val


# endregion Instruction Types

"""dictionary mapping the opcode number to an instruction type
this is where each of the instruction types and their behaviors are defined
"""
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
    LDR_InstructionType('LDR'),
    STR_InstructionType('STR'),
    # TODO implement the rest of the instructions, implemented as NOOPs currently
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
    B_InstructionType('BL'),  # TODO implement
    InstructionType('END')
]


class Instruction:
    """class for an instance of an instruction, containing the raw encoded bits of the instruction, as well as helper functions for processing the instruction at the different pipeline stages
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

    def __init__(self, encoded: Optional[int] = None):
        """creates a new instance of an instruction

        Parameters
        ----------
        encoded : Optionals[int]
            the encoded bits corresponding to the instruction
            will default to 0b0 (No Op) if value is not assigned
        """
        self._scoreboard_index = -1

        self._encoded = 0b0 if encoded is None else encoded  # sets instruction to NOOP if encoded value is not specified
        self._decoded = None  # type: ignore

        # calculate the opcode
        self.opcode = InstructionType.Encoding(self._encoded)['opcode']

        # the instruction's dependencies
        self.output_reg = None  # type: ignore
        self.input_regs = []  # type: ignore
        self.computed = None  # type: ignore

    def decode(self) -> None:
        """helper function which decodes the instruction
        """

        # parse the rest of the encoded information according to the specific encoding pattern of the instruction type
        instruction_encoding = OpCode_InstructionType_lookup[self.opcode].encoding
        self._decoded = instruction_encoding(self._encoded)

        # update the instruction's output dependencies
        self.output_reg = self.try_get('dest')

        # update the instruction's input dependencies
        self.input_regs.append(src) if (src := self.try_get(
            'src')) is not None else None  # append src to input_regs if the field exists
        self.input_regs.append(op1) if (op1 := self.try_get('op1')) is not None else None
        self.input_regs.append(op2) if (op2 := self.try_get('op2')) is not None else None

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
