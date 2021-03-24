from memory_subsystem import MemorySubsystem
from eisa import EISA

class PipeLine:

    #Use dict later to get funcs associated with opcodes

    _memory: MemorySubsystem
    _pc: None
    _registers: None
    _pipeline: list

    def __init__(self, pc: int, registers: list[int], cache_size: int, ram_size: int):
        self.registers = registers
        self.pc = pc
        self.memory = MemorySubsystem(cache_size, ram_size)

    def stage_fetch(self):

        # Load instruction in MEMORY at the address the PC is pointing to
        incoming_instruction = self.memory[self.pc]

        # increment PC by instruction size
        self.pc += 1



    def stage_decode(self):

        # Decode the instruction

        # Access regfile to read the registers

        # Put outputs of GP regs into two temp regs (for use later)

        # Sign extend the lower 16 bits of the instr. reg and store
        #   into temp Imm reg

        pass

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

class Instruction:

    # Operation
    _opcode: int

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
        self.opA = (self.encoded >> 2*EISA.GP_REGS_BITS) & EISA.GP_REGS_BITS
        self.opB = (self.encoded >> 5*EISA.GP_REGS_BITS) & EISA.GP_REGS_BITS
        self.opC = self.encoded & EISA.GP_REGS_BITS
        self.immediate = (self.encoded >> 14) & 1





