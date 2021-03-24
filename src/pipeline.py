from memory_subsystem import MemorySubsystem
from eisa import EISA
from queue import *

class Instruction:
    # Operation
    _opcode: int

    # Register addresses
    _regA: int
    _regB: int
    _regC: int

    # Operands
    _opA: int
    _opB: int
    _opC: int

    # Result if the instruction is a computation. None for loads and stores
    _computed: int

    # Determine whether opB is immediate
    _immediate: int

    # Raw instructions
    _encoded = int

    def __init__(self, encoded: int):
        self.encoded = encoded

    def decode(self):
        self.opcode = self.encoded >> 28
        self.regA = (self.encoded >> 2 * EISA.GP_REGS_BITS) & EISA.GP_REGS_BITS
        self.regB = (self.encoded >> 5 * EISA.GP_REGS_BITS) & EISA.GP_REGS_BITS
        self.regC = self.encoded & EISA.GP_REGS_BITS
        self.immediate = (self.encoded >> 14) & 1

class PipeLine:
    # TODO - Use dict later to get funcs associated with opcodes

    _memory: MemorySubsystem
    _pc: None
    _registers: None
    _pipeline: list[Instruction]

    _fd_reg: Queue[Instruction]
    _de_reg: Queue[Instruction]
    _em_reg: Queue[Instruction]
    _mw_reg: Queue[Instruction]

    def __init__(self, pc: int, registers: list[int], cache_size: int, ram_size: int):
        self.registers = registers
        self.pc = pc
        self.memory = MemorySubsystem(cache_size, ram_size)
        self.pipeline = [None for i in range(5)]

    def stage_fetch(self):
        # Load instruction in MEMORY at the address the PC is pointing to
        incoming_instruction = self.memory[self.pc]

        # increment PC by 1 word
        self.pc += 1

        # push instruction into queue
        self.pipeline[0] = incoming_instruction
        self.fd_reg.put(incoming_instruction)

    def stage_decode(self):

        # get fetched instruction
        instruction = self.fd_reg.get()

        # Decode the instruction
        instruction.decode()

        # Access regfile to read the registers
        opA = self.registers[instruction.regA]
        opB = self.registers[instruction.regB]

        # Put outputs of GP regs into two temp regs (for use later)
        #   Storing them inside the instruction itself
        instruction.opA = opA
        instruction.opB = opB

        # TODO? - Sign extend the lower 16 bits of the instr. reg and store
        #   into temp Imm reg

    def stage_execute(self):
        # Execute depending on instruction
        # https://en.wikipedia.org/wiki/Classic_RISC_pipeline

        # 1) Memory reference. Obtain values located at referred addr
        #   (2-cycle latency)

        # 2) Reg-Reg. Add, subtract, compare, and logical operations.
        #   (1-cycle latency). Dictated by opcode

        pass

    def stage_memory(self):
        # Update PC

        # If instruction is a load, data return from memory and are placed in the LMD reg

        # If the instruction is a store, then the data from reg B is written into memory

        # Address used is the one computed during the prior cycle and stored in the ALU output reg

        pass

    def stage_writeback(self):
        # Write the result into the reg file, whether it comes from the memory system (LMD reg) or
        #   the ALU (ALUOutput).

        pass

    def cycle_pipeline(self):

        # TODO - Process one step in the pipeline

        pass

