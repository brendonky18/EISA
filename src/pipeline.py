from memory_subsystem import MemorySubsystem
from eisa import EISA
from queue import *

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
        self.opcode = self.encoded >> 28
        self.regA = (self.encoded >> 2 * EISA.GP_REGS_BITS) & EISA.GP_REGS_BITS
        self.regB = (self.encoded >> 5 * EISA.GP_REGS_BITS) & EISA.GP_REGS_BITS
        self.regC = self.encoded & EISA.GP_REGS_BITS
        self.immediate = (self.encoded >> 14) & 1

class PipeLine:
    # TODO - Use dict later to get funcs associated with opcodes
    # TODO - Implement branching and branch squashing
    # TODO - implement no-ops and stalls

    _memory: MemorySubsystem
    _pc: None
    _registers: None
    _pipeline: list[Instruction]

    _fd_reg: Queue[Instruction]
    _de_reg: Queue[Instruction]
    _em_reg: Queue[Instruction]
    _mw_reg: Queue[Instruction]

    _cycles: int

    def __init__(self, pc: int, registers: list[int], cache_size: int, ram_size: int):
        self.registers = registers
        self.pc = pc
        self.memory = MemorySubsystem(cache_size, ram_size)
        self.pipeline = [None for i in range(5)]
        self._fd_reg = Queue()
        self._de_reg = Queue()
        self._em_reg = Queue()
        self._mw_reg = Queue()
        self.cycles = 0

    def stage_fetch(self):
        # Load instruction in MEMORY at the address the PC is pointing to
        instruction = self.memory[self.pc]
        self.pipeline[0] = instruction

        # increment PC by 1 word
        self.pc += 1

        # push instruction into queue
        self.pipeline[0] = instruction
        self.fd_reg.put(instruction)

    def stage_decode(self):

        # get fetched instruction
        instruction = self.fd_reg.get()
        self.pipeline[1] = instruction

        # Decode the instruction
        instruction.decode()

        # Access regfile to read the registers
        opA = self.registers[instruction.regA]
        opC = self.registers[instruction.regC]

        # Determine if second operand is immediate or not
        if instruction.immediate:
            opB = instruction.regB
        else:
            opB = self.registers[instruction.regB]

        # Put outputs of GP regs into two temp regs (for use later)
        #   Storing them inside the instruction itself
        instruction.opA = opA
        instruction.opB = opB
        instruction.opC = opC

        # TODO? - Sign extend the lower 16 bits of the instr. reg and store
        #   into temp Imm reg

        # Push edited instruction into the adjacent queue
        self.de_reg.put(instruction)

    def stage_execute(self):

        # get decoded instruction
        instruction = self.de_reg.get()
        self.pipeline[2] = instruction

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
        self.em_reg.put(instruction)

    def stage_memory(self):

        # get executed instruction
        instruction = self.em_reg.get()
        self.pipeline[3] = instruction

        # If instruction is a load, data return from memory and are placed in the LMD reg
        if instruction.opcode == 0b010001:

            # Load value obtained from address Rn + Rt in memory into instruction
            instruction.computed = self.memory[instruction.regB + instruction.regC]

        # If the instruction is a store, then the data from reg B is written into memory
        elif instruction.opcode == 0b010000:

            # Store value in register Rm into MEMORY address Rn + Rt
            # Address used is the one computed during the prior cycle and stored in the ALU output reg
            self.memory[instruction.opB + instruction.opC] = instruction.opA

        # Push edited instruction into the adjacent queue
        self.mw_reg.put(instruction)

    def stage_writeback(self):

        # get memorized instruction
        instruction = self.mw_reg.get()
        self.pipeline[4] = instruction

        # Write the result into the reg file, whether it comes from the memory system (LMD reg) or
        #   the ALU (ALUOutput).
        if instruction.computed is not None:
            if instruction.opcode == 0b000011:
                self.registers[instruction.regC] = instruction.computed
            elif instruction.opcode == 0b010001:
                self.registers[instruction.regA] = instruction.computed

    def cycle_pipeline(self):

        # TODO - Process one step in the pipeline
        self.stage_fetch()
        self.stage_decode()
        self.stage_execute()
        self.stage_memory()
        self.stage_writeback()
        self.cycles += 1

    def __str__(self):

        print(f"Fetch:{self.pipeline[0].opcode}->[{self.fd_reg[0].opcode},{self.fd_reg[1].opcode}]"
              f"->Decode:{self.pipeline[1].opcode}->[{self.de_reg[0].opcode},{self.de_reg[1].opcode}]"
              f"->Execute:{self.pipeline[2].opcode}->[{self.em_reg[0].opcode},{self.em_reg[1].opcode}]"
              f"->Memory:{self.pipeline[3].opcode}->[{self.mw_reg[0].opcode},{self.mw_reg[1].opcode}]"
              f"->Memory:{self.pipeline[4].opcode}")


