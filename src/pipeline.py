from memory_subsystem import MemorySubsystem
from eisa import EISA
from queue import *
from typing import List

class Instruction:
    # Operation
    _opcode: int

    # Register addresses (raw values provided to instruction)
    _regA: int
    _regB: int
    _regC: int

    # Operands (values loaded assuming register addresses in regA,regB,regC)
    _opA: int
    _opB: int
    _opC: int

    # Result for addition instructions, or loaded value if a load instruction
    _computed: None

    # Determine whether opB is immediate
    _immediate: int

    # Raw instructions
    _encoded = int

    def __init__(self, encoded: int):
        self.encoded = encoded
        self.computed = None

    def decode(self):
        self.opcode = self.encoded >> 26
        self.regA = (self.encoded >> 2 * EISA.GP_NUM_FIELD_BITS) & EISA.GP_REGS_BITS
        self.regB = (self.encoded >> EISA.GP_NUM_FIELD_BITS) & EISA.GP_REGS_BITS
        self.regC = self.encoded & EISA.GP_REGS_BITS
        self.immediate = (self.encoded >> 15) & 1

class PipeLine:
    # TODO - Use dict later to get funcs associated with opcodes
    # TODO - Implement branching and branch squashing
    # TODO - implement no-ops and stalls

    _memory: MemorySubsystem
    _pc: int
    _registers: List[int]
    _pipeline: list[Instruction]

    _fd_reg: Queue[Instruction]
    _de_reg: Queue[Instruction]
    _em_reg: Queue[Instruction]
    _mw_reg: Queue[Instruction]

    _cycles: int

    def __init__(self, pc: int, registers: list[int], memory: MemorySubsystem):
        self._registers = registers
        self._pc = pc
        self._memory = memory
        self._pipeline = [None for i in range(5)]
        self._fd_reg = Queue()
        self._de_reg = Queue()
        self._em_reg = Queue()
        self._mw_reg = Queue()
        self.cycles = 0

    def stage_fetch(self):
        # Load instruction in MEMORY at the address the PC is pointing to
        instruction = Instruction(self._memory[self._pc])
        self._pipeline[0] = instruction

        # increment PC by 1 word
        self._pc += 1

        # push instruction into queue
        self._pipeline[0] = instruction
        self._fd_reg.put(instruction)

    def stage_decode(self):

        if self._fd_reg.qsize() < 2:
            return

        # get fetched instruction
        instruction = self._fd_reg.get()
        self._pipeline[1] = instruction

        # Decode the instruction
        instruction.decode()

        # Access regfile to read the registers
        opA = self._registers[instruction.regA]
        opC = self._registers[instruction.regC]

        # Determine if second operand is immediate or not
        if instruction.immediate:
            opB = instruction.regB
        else:
            opB = self._registers[instruction.regB]

        # Put outputs of GP regs into two temp regs (for use later)
        #   Storing them inside the instruction itself
        instruction.opA = opA
        instruction.opB = opB
        instruction.opC = opC

        # TODO? - Sign extend the lower 16 bits of the instr. reg and store
        #   into temp Imm reg

        # Push edited instruction into the adjacent queue
        self._de_reg.put(instruction)

    def stage_execute(self):

        if self._de_reg.qsize() < 2:
            return

        # get decoded instruction
        instruction = self._de_reg.get()
        self._pipeline[2] = instruction

        # Execute depending on instruction
        # https://en.wikipedia.org/wiki/Classic_RISC_pipeline

        # Addition
        if instruction.opcode == 0b000011:
            instruction.computed = instruction.opA + instruction.opB

        # 1) Memory reference. Obtain values located at referred addr
        #   (2-cycle latency)

        # 2) Reg-Reg. Add, subtract, compare, and logical operations.
        #   (1-cycle latency). Dictated by opcode

        # Push edited instruction into the adjacent queue
        self._em_reg.put(instruction)

    def stage_memory(self):

        if self._em_reg.qsize() < 2:
            return

        # get executed instruction
        instruction = self._em_reg.get()
        self._pipeline[3] = instruction

        # If instruction is a load, data return from memory and are placed in the LMD reg
        if instruction.opcode == 0b010001:

            # Load value obtained from address Rn + Rt in memory into instruction
            instruction.computed = self._memory[instruction.regB + instruction.regC]

        # If the instruction is a store, then the data from reg B is written into memory
        elif instruction.opcode == 0b010000:

            # Store value in register Rm into MEMORY address Rn + Rt
            # Address used is the one computed during the prior cycle and stored in the ALU output reg
            self._memory[instruction.regB + instruction.regC] = instruction.opA

        # Push edited instruction into the adjacent queue
        self._mw_reg.put(instruction)

    def stage_writeback(self):

        if self._mw_reg.qsize() < 2:
            return

        # get memorized instruction
        instruction = self._mw_reg.get()
        self._pipeline[4] = instruction

        # Write the result into the reg file, whether it comes from the memory system (LMD reg) or
        #   the ALU (ALUOutput).
        if instruction.computed is not None:
            if instruction.opcode == 0b000011:
                self._registers[instruction.regC] = instruction.computed
            elif instruction.opcode == 0b010001:
                self._registers[instruction.regA] = instruction.computed

    def cycle_pipeline(self):

        # TODO - Process one step in the pipeline
        self.stage_fetch()
        self.stage_decode()
        self.stage_execute()
        self.stage_memory()
        self.stage_writeback()
        self.cycles += 1

    def cycle(self, x):
        for i in range(x):
            self.cycle_pipeline()

    def __str__(self):

        print(f"Fetch:{self._pipeline[0].opcode}->[{self.fd_reg[0].opcode},{self.fd_reg[1].opcode}]"
              f"->Decode:{self._pipeline[1].opcode}->[{self.de_reg[0].opcode},{self.de_reg[1].opcode}]"
              f"->Execute:{self._pipeline[2].opcode}->[{self.em_reg[0].opcode},{self.em_reg[1].opcode}]"
              f"->Memory:{self._pipeline[3].opcode}->[{self.mw_reg[0].opcode},{self.mw_reg[1].opcode}]"
              f"->Memory:{self._pipeline[4].opcode}")


