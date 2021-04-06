from __future__ import annotations
from queue import *
from typing import Dict, Type, Union, Callable, List, Optional
from memory_subsystem import MemorySubsystem
from eisa import EISA
from bit_vectors import BitVector
from eisa import EISA

class DecodeError(Exception):
    message: str
    def __init__(self, message: str='Instruction has not been decoded yet'):
        self.message = message

    def __str__(self):
        return self.message

class func_unit():
    # Relevant instruction
    _instruction: Instruction

    # Register source 1 for this instruction
    _src1: int

    # Flag indicating whether src1 is valid
    _src1_valid: int

    # Register source 2 for this instruction
    _src2: int

    # Flag indicating whether src2 is valid
    _src2_valid: int

    # Func number (row)
    _scoreboard_row: int

    # Register marked as the destination for this instruction
    _destination: int

    # Flag indicating whether the destination register is in-use
    _destination_pending: int

    # Flag indicating whether the active list needs to be empty for this
    #   instruction to execute
    _no_active_exec: int

    def __init__(self, instruction: Instruction, scoreboard_row: int):

        opcode = instruction._opcode

        self._instruction = instruction
        self._instruction._scoreboard_index = scoreboard_row

        # ALU Ops
        if opcode > 0 or opcode < 0b001101:
            # OpCode_InstructionType_lookup["""opcode number"""].execute/memory/writeback_stage_func

            self._destination = instruction._opA
            self._src1 = instruction._opB
            self._src2 = instruction._opC
            self._no_active_exec = 0

        # ***NAIVE*** Assuming otherwise it's a load, store, or branch for demo 4/5/2021
        # TODO - Implement a proper opcode switch statement

        # NOTE: For loads and stores, we are assuming that the memory is superfluous to dependencies.
        # TODO - Write unit test to ensure that memory is superfluous to dependencies

        # Load Op
        elif opcode == 0b001101:

            self._destination = instruction._opA
            self._src1 = -1
            self._src2 = -1
            self._no_active_exec = 0

        # Store Op
        elif opcode == 0b001110:

            self._src1 = instruction._opA
            self._src2 = -1
            self._destination = -1
            self._no_active_exec = 0

        # Branches, END Ops --> Ensure that active list is empty before these execute
        elif opcode >= 0b011110:

            self._src1 = -1
            self._src2 = -1
            self._destination = -1
            self._no_active_exec = 1

        else:

            raise Exception("Invalid Opcode Incurred on Scoreboard")

        def valid_to_execute():

            return self._src1_valid and self._src2_valid

        '''
        # checks if the instruction has a source field
        try:
            instruction['src']
        except KeyError:
            pass # does not have 'src'
        else:
            pass # has 'src'

        # checks if the instruction has a destination field
        try:
            instruction['dest']
        except KeyError:
            pass # does not have 'dest'
        else:
            pass # has 'dest'
        '''

class ScoreBoard():
    # Functional units
    func_units: list[func_unit]

    waiting: Queue

    # Index of the next available scoreboard row
    _function_index: int

    # Flag indicating empty (1 = empty, 0 = not empty)
    _isempty: int

    # Index of the last valid instruction executed on the scoreboard
    _last_valid: int

    # Current list of active instructions
    active: list[Instruction]

    # Int for each register indicating the scoreboard row that plans to output to said corresponding register
    rrd: list[int]

    # Number of instruction queue entires, scoreboard rows, number of registers in pipeline
    def __init__(self, iq_size: int, s_rows: int, rrd_size: int):

        self.waiting = Queue(iq_size)
        self.active = [Instruction() for i in range(s_rows)] # changed from list of None, to list of NoOps, I don't think that breaks anything
        self.func_units = [None for i in range(s_rows)] # type: ignore
        self.rrd = [-1 for i in range(rrd_size)]
        self._function_index = 0
        self._isempty = 1

    # Enqueue an instruction to be placed on the scoreboard
    def enqueue_instruction(self, instruction: Instruction):

        incoming_unit = func_unit(instruction, self._function_index)

        # whether if scoreboard is empty and 
        # the instruction is NOT an instruction that requires the active instruction list to be empty
        # meaning branch/end
        if self._isempty and not isinstance(OpCode_InstructionType_lookup[instruction['opcode']], B_InstructionType):
            self.put(incoming_unit)
        else:
            self.waiting.put(incoming_unit)

        self._function_index += 1

    # Place a func unit directly on the scoreboard
    def put(self, incoming_unit: func_unit):

        self.func_units[self._function_index] = incoming_unit
        self.active[self._function_index] = incoming_unit._instruction

        if incoming_unit._destination != -1:
            self.rrd[incoming_unit._destination] = self._function_index

        # Set valid bits
        if self.rrd[incoming_unit._src1] > -1:

            self.rrd._src1_valid = 0 # FIXME rrd is a list of integers, what is this trying to do?

        else:

            self.rrd._src1_valid = 1

        if self.rdd[incoming_unit._src2] > -1:

            self.rrd._src2_valid = 0

        else:

            self.rrd._src2_valid = 1

        self._isempty = 0

    # Determine if the next in line instruction is prepared to be
    #   placed on the scoreboard
    def advance_instruction_queue(self):

        # Peek top element of instruction queue
        peeked = self.waiting[0]

        if peeked._no_active_exec and self._isempty:

            self.put(self.waiting.get())

        elif self.func_units[peeked._scoreboard_row] == -1 and self.rrd[peeked._destination] == -1:

            self.put(self.waiting.get())

        else:

            return

    def remove(self, scoreboard_index: int):

        toRemove = self._func_units[scoreboard_index]

        self.rrd[toRemove._destination] = -1

        self._func_units[scoreboard_index] = -1

    def update_scoreboard(self, scoreboard_index: int):

        self.remove(scoreboard_index)
        self.advance_instruction_queue()

    # Return the next valid instruction on the scoreboard
    #   If there is none, return a NOOP (stall)
    def get_next_valid_instruction(self):

        # Just return a NOOP if the scoreboard is empty.
        #   Advancing the queue is an abuse of code in the simulator
        if self._isempty:
            return Instruction(-1)

        while self.func_units[self._last_valid] != -1:
            self._last_valid += 1

        return self.func_units[self._last_valid]._instruction

    # TODO - Write a unit test to determine whether squashing entire scoreboard
    #   is dependency-safe
    def squash_scoreboard(self):

        waiting_len = len(self.waiting)
        row_len = len(self.active)

        self.waiting = Queue(waiting_len)
        self.active = [None for i in range(row_len)]
        self.func_units = [None for i in range(row_len)]
        self.rrd = [-1 for i in range(EISA.NUM_GP_REGS)]
        self._function_index = 0
        self._isempty = 1

class PipeLine:
    # TODO - Use dict later to get funcs associated with opcodes
    # TODO - Implement branching and branch squashing
    # TODO - implement no-ops and stalls

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

    # Begion Scoreboard

    # Scoreboard rows object


    _scoreboard: ScoreBoard


    def __init__(self, pc: int, registers: list[int], memory: MemorySubsystem):
        self._registers = registers
        self._pc = pc
        self._memory = memory
        self._pipeline = [Instruction(-1) for i in range(5)]
        self._fd_reg = [Instruction(-1), Instruction(-1)]
        self._de_reg = [Instruction(-1), Instruction(-1)]
        self._em_reg = [Instruction(-1), Instruction(-1)]
        self._mw_reg = [Instruction(-1), Instruction(-1)]
        self._cycles = 0
        self._condition_flags = {
            'n': 0,
            'z': 0,
            'c': 0,
            'v': 0
        }
        self._scoreboard = ScoreBoard(EISA.NUM_INSTR_Q_ROWS, EISA.NUM_SCOREBOARD_ROWS, EISA.NUM_GP_REGS)

    # Destination of new program counter
    def squash(self, newPC: int):
        self._scoreboard.squash_scoreboard()
        self._pipeline[0] = Instruction()
        self._pipeline[1] = Instruction()
        self._fd_reg = [Instruction(), Instruction()]
        self._de_reg = [Instruction(), Instruction()]
        self._pc = newPC
        self.cycle(2)

    def stage_fetch(self):
        # Load instruction in MEMORY at the address the PC is pointing to
        instruction = Instruction(self._memory[self._pc])
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
        instruction_type.memory_stage_func(instruction, self)

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
        self._fd_reg = [Instruction(-1), self._fd_reg[0]]
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
        self._scoreboard.update_scoreboard(self._pipeline[4]._scoreboard_index)
        self._cycles += 1
        self.cycle_stage_regs()
        print(str(self))


    def cycle(self, x):
        for i in range(x):
            self.cycle_pipeline()

    def __str__(self):

        out = "******BEGIN PIPELINE*******\n"

        out += f"Regs: {self._registers}\n"

        for i in range(len(self._pipeline)):
            out += f"Stage {i}:\n {str(self._pipeline[i])}"

        out += "*******END PIPELINE*******\n"

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

        def m_func(instruction: Instruction, pipeline: PipeLine):
            pass
        def w_func(instruction: Instruction, pipeline: PipeLine):
            pass
        super().__init__(mnemonic, e_func, m_func, w_func)

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
        self._decoded = OpCode_InstructionType_lookup[self._opcode]

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
