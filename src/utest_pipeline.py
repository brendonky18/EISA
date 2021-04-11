import unittest

from clock import *
from eisa import EISA
from memory_subsystem import MemorySubsystem
from pipeline import *


class UnittestPipeline(unittest.TestCase):

    # Add 2 registers together. Confirm that the result is stored
    #   into another register
    def test_addition_simple(self):

        mem_sub = MemorySubsystem(EISA.ADDRESS_SIZE, 4, 1, 1, 8, 2, 2)

        Clock.start()

        my_pipe = PipeLine(0, [1 for i in range(EISA.NUM_GP_REGS)], mem_sub)

        my_pipe._registers[31] = 10
        my_pipe._registers[4] = 30

        # Opcode: 000001 (ADD/MOV)
        # Destination: 00011 (Register 3)
        # Operand 1: 11111 (Register 31)
        # Immediate Flg: 0
        # Operand 2: 00100 (Register 4)
        # PADDING: 0000000000 (Bits 9 - 0 are Irrelevant)
        instruction = OpCode_InstructionType_lookup[0b000001].encoding()
        instruction['opcode'] = 0b000001
        instruction['dest'] = 0b00011
        instruction['op1'] = 0b11111
        instruction['op2'] = 0b00100
        instruction['imm'] = False

        try:
            my_pipe._memory[0] = instruction._bits  # 0b00000100011111110001000000000000
        except PipelineStall:
            # Ensure that the stall thread rejoins prior to running the test
            sleep(2)
            pass

        # A single add instruction should take no more than 5 cycles to fully execute,
        #   however, the instruction takes 6 cycles to fully exit the pipeline, which we
        #   are not verifying.
        #my_pipe.cycle(7)

        # Instruction takes 6 cycles.
        # 2 cycles for fetch to read from memory
        # 4 cycles to get through all stages

        '''
        my_pipe.cycle_pipeline()
        my_pipe.cycle_pipeline()
        my_pipe.cycle_pipeline()
        my_pipe.cycle_pipeline()
        my_pipe.cycle_pipeline()
        my_pipe.cycle_pipeline()
        my_pipe.cycle_pipeline()
        '''

        # my_pipe.cycle(8)
        #Clock.step(7)

        my_pipe.cycle(7)
        #my_pipe.cycle_pipeline()


        # my_pipe.cycle(6)
        # my_pipe.cycle_pipeline()

        Clock.stop()

        # Assert that the values in register 31 and register 4 equal the value in register 3
        # NOTE: REMEMBER REGISTERS ARE ALREADY 0 INDEXED - We refer to the first register as the 0th register
        self.assertEqual(my_pipe._registers[31] + my_pipe._registers[4], my_pipe._registers[3])
        '''
        while my_pipe._registers[31] + my_pipe._registers[4] is not my_pipe._registers[3]:
            try:
                self.assertEqual(my_pipe._registers[31] + my_pipe._registers[4], my_pipe._registers[3])
                break
            except AssertionError:
                pass
        '''

    # Load two operands from memory (on a cache hit). Confirm the cycles are correct and
    #   the registers contain the correct value
    def test_load_2_operands(self):
        mem_sub = MemorySubsystem(EISA.ADDRESS_SIZE, 4, 1, 1, 8, 2, 2)

        Clock.start()

        my_pipe = PipeLine(0, [1 for i in range(EISA.NUM_GP_REGS)], mem_sub)

        # Opcode: 001101 (LOAD)
        instruction = OpCode_InstructionType_lookup[0b001101].encoding()
        instruction['dest'] = 3
        instruction['lit'] = False
        instruction['base'] = 31
        try:
            my_pipe._memory[0] = instruction._bits
        except PipelineStall:
            pass

        # Set memory address 31 to a value of 72
        try:
            my_pipe._memory[31] = 72
        except PipelineStall:
            pass

        # A single load instruction should take no more than 5 cycles to fully execute,
        #   however, the instruction takes 6 cycles to fully exit the pipeline, which we
        #   are not verifying.
        my_pipe.cycle(7)

        Clock.stop()

        # Assert that the value in register 3 is the value read from the value stored at address
        #   31 in memory
        A = None
        while A is None:
            try:
                A = my_pipe._memory[31]
            except PipelineStall:
                pass

        self.assertEqual(A, my_pipe._registers[3])

    def test_store_simple(self):
        mem_sub = MemorySubsystem(EISA.ADDRESS_SIZE, 4, 1, 1, 8, 2, 2)

        Clock.start()

        my_pipe = PipeLine(0, [1 for i in range(EISA.NUM_GP_REGS)], mem_sub)

        # Opcode: 001110 (STR)
        # Src: 00011 (Register 3)
        # PADDING: 00000 (Bits 20-16 are Irrelevant)
        # Literal Flg: 0
        # Base/Literal: 11111 (Address 31)
        # Offset/Literal: 0000000000 (Offset 0)

        instruction = OpCode_InstructionType_lookup[0b001110].encoding()
        instruction['src'] = 0b00011
        instruction['base'] = 0b11111
        instruction['offset'] = 0

        try:
            my_pipe._memory[0] = instruction._bits  # 0b00111000011111110000000000000000
        except PipelineStall:
            pass

        my_pipe._registers[31] = 31
        try:
            my_pipe._memory[31] = 72
        except PipelineStall:
            pass

        # A single store instruction should take no more than 5 cycles to fully execute,
        #   however, the instruction takes 6 cycles to fully exit the pipeline, which we
        #   are not verifying.
        my_pipe.cycle(7)

        Clock.stop()

        self.assertEqual(my_pipe._registers[3], my_pipe._memory[31])

    def test_load_store_alu(self):

        mem_sub = MemorySubsystem(EISA.ADDRESS_SIZE, 4, 1, 1, 8, 2, 2)

        Clock.start()

        my_pipe = PipeLine(0, [i for i in range(EISA.NUM_GP_REGS)], mem_sub)

        # Load value into reg 31 from address 4 + 0 offset

        # Opcode: 001101 (LOAD)
        instruction = OpCode_InstructionType_lookup[0b001101].encoding()
        instruction['dest'] = 31
        instruction['base'] = 4
        instruction['lit'] = False
        instruction['offset'] = 0
        try:
            my_pipe._memory[0] = instruction._bits
        except PipelineStall:
            pass

        # Add value in reg 31 with value in reg 4, store in reg 3

        # Opcode: 000001 (ADD)
        instruction = OpCode_InstructionType_lookup[0b000001].encoding()
        instruction['dest'] = 3
        instruction['op1'] = 31
        instruction['imm'] = False
        instruction['op2'] = 4
        try:
            my_pipe._memory[1] = instruction._bits
        except PipelineStall:
            pass

        # Gets value to store from reg 3 (11111) (the value stored is 555)

        # Attempts to store @ address 5 (00101) with offset 0 (00000)

        # Opcode: 001110 (STR)
        instruction = OpCode_InstructionType_lookup[0b001110].encoding()
        instruction['base'] = 3
        instruction['offset'] = 0
        instruction['op1'] = 31
        instruction['imm'] = False
        instruction['op2'] = 4
        try:
            my_pipe._memory[2] = instruction._bits
        except PipelineStall:
            pass

        # Value to be loaded in reg 31

        try:
            my_pipe._memory[4] = 555
        except PipelineStall:
            pass

        # Value in reg 4 to add to the value stored in reg 31

        my_pipe._registers[4] = 30

        # Num instructions + num stages + 1

        cycleCounter = 0

        Clock.stop()

        self.assertEqual(555, my_pipe._registers[31])

        self.assertEqual(585, my_pipe._registers[3])

        self.assertEqual(585, my_pipe._memory[5])


if __name__ == '__main__':
    # Clock.start()
    unittest.main()
    # Clock.stop()
