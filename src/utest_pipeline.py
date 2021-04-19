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

        # cook END instruction to signal pipeline to end
        end = OpCode_InstructionType_lookup[0b100000].encoding()

        # cook the pipe's memory
        my_pipe._memory._RAM[0] = instruction._bits
        my_pipe._memory._RAM[1] = end._bits

        my_pipe.cycle(7)

        # Assert that the values in register 31 and register 4 equal the value in register 3
        # NOTE: REMEMBER REGISTERS ARE ALREADY 0 INDEXED - We refer to the first register as the 0th register
        self.assertEqual(my_pipe._registers[31] + my_pipe._registers[4], my_pipe._registers[3])

    # Load two operands from memory (on a cache hit). Confirm the cycles are correct and
    #   the registers contain the correct value
    def test_load_1_operand(self):
        mem_sub = MemorySubsystem(EISA.ADDRESS_SIZE, 4, 1, 1, 8, 2, 2)

        my_pipe = PipeLine(0, [1 for i in range(EISA.NUM_GP_REGS)], mem_sub)

        # Opcode: 001101 (LOAD)
        instruction = OpCode_InstructionType_lookup[0b001101].encoding()
        instruction['opcode'] = 0b001101
        instruction['dest'] = 3
        instruction['lit'] = False
        instruction['base'] = 31
        instruction['offset'] = 0

        my_pipe._memory._RAM[0] = instruction._bits

        # cook END instruction to signal pipeline to end
        end = OpCode_InstructionType_lookup[0b100000].encoding()
        end['opcode'] = 0b100000
        my_pipe._memory._RAM[1] = end._bits

        my_pipe._memory._RAM[12] = 72
        my_pipe._registers[31] = 12

        my_pipe.cycle(9)

        self.assertEqual(my_pipe._memory._RAM[12], my_pipe._registers[3])

    def test_load_2_operands(self):
        mem_sub = MemorySubsystem(EISA.ADDRESS_SIZE, 4, 1, 1, 8, 2, 2)

        my_pipe = PipeLine(0, [1 for i in range(EISA.NUM_GP_REGS)], mem_sub)

        # Opcode: 001101 (LOAD)
        instruction = OpCode_InstructionType_lookup[0b001101].encoding()
        instruction['opcode'] = 0b001101
        instruction['dest'] = 3
        instruction['lit'] = False
        instruction['base'] = 31

        # TODO - is the offset being treated as a register number or a literal?
        instruction['offset'] = 0

        my_pipe._memory._RAM[0] = instruction._bits

        my_pipe._memory._RAM[12] = 72
        my_pipe._registers[31] = 12

        # Opcode: 001101 (LOAD)
        instruction2 = OpCode_InstructionType_lookup[0b001101].encoding()
        instruction2['opcode'] = 0b001101
        instruction2['dest'] = 4
        instruction2['lit'] = False
        instruction2['base'] = 30
        instruction2['offset'] = 0

        my_pipe._memory._RAM[1] = instruction2._bits

        my_pipe._memory._RAM[13] = 36
        my_pipe._registers[30] = 13

        # cook END instruction to signal pipeline to end
        end = OpCode_InstructionType_lookup[0b100000].encoding()
        end['opcode'] = 0b100000
        my_pipe._memory._RAM[2] = end._bits

        my_pipe.cycle(13)

        self.assertEqual(my_pipe._memory._RAM[12], my_pipe._registers[3])
        self.assertEqual(my_pipe._memory._RAM[13], my_pipe._registers[4])

    def test_store_simple(self):
        mem_sub = MemorySubsystem(EISA.ADDRESS_SIZE, 4, 1, 1, 8, 2, 2)

        my_pipe = PipeLine(0, [1 for i in range(EISA.NUM_GP_REGS)], mem_sub)

        # Opcode: 001110 (STR) Src: 00011 (Register 3) PADDING: 00000 (Bits 20-16 are Irrelevant) Base/Literal: 11111
        # (Register 31) Offset/Literal: 0000000000 (Offset 0) TODO - is this a register number or a literal????
        #  Assuming reg num for now

        instruction = OpCode_InstructionType_lookup[0b001110].encoding()
        instruction['opcode'] = 0b001110
        instruction['src'] = 3
        instruction['base'] = 31
        instruction['offset'] = 0

        my_pipe._memory._RAM[0] = instruction._bits  # Set the 0th word in memory to this instruction, such that it's
        # the first instruction the PC points to

        my_pipe._registers[31] = 18  # Storing to address 18 in memory

        my_pipe._registers[3] = 256  # storing value in register 3

        # cook END instruction to signal pipeline to end
        end = OpCode_InstructionType_lookup[0b100000].encoding()
        end['opcode'] = 0b100000
        my_pipe._memory._RAM[1] = end._bits  # END is stored at address (word) 1 in memory

        my_pipe.cycle(8)  # TODO - Why does store take less cycles than load???

        self.assertEqual(my_pipe._registers[3], my_pipe._memory._RAM[18])

    def test_load_add_store(self):
        mem_sub = MemorySubsystem(EISA.ADDRESS_SIZE, 4, 1, 1, 8, 2, 2)

        my_pipe = PipeLine(0, [1 for i in range(EISA.NUM_GP_REGS)], mem_sub)

        # Opcode: 001101 (LOAD)
        instruction = OpCode_InstructionType_lookup[0b001101].encoding()
        instruction['opcode'] = 0b001101
        instruction['dest'] = 3
        instruction['lit'] = False
        instruction['base'] = 31

        # TODO - is the offset being treated as a register number or a literal?
        instruction['offset'] = 0

        my_pipe._memory._RAM[0] = instruction._bits

        my_pipe._memory._RAM[12] = 72
        my_pipe._registers[31] = 12

        # Opcode: 001101 (LOAD)
        instruction2 = OpCode_InstructionType_lookup[0b001101].encoding()
        instruction2['opcode'] = 0b001101
        instruction2['dest'] = 4
        instruction2['lit'] = False
        instruction2['base'] = 30
        instruction2['offset'] = 0

        my_pipe._memory._RAM[1] = instruction2._bits

        my_pipe._memory._RAM[13] = 36
        my_pipe._registers[30] = 13

        # Opcode: 000001 (ADD/MOV)
        instruction3 = OpCode_InstructionType_lookup[0b000001].encoding()
        instruction3['opcode'] = 0b000001
        instruction3['dest'] = 24
        instruction3['op1'] = 4  # Destination of the first load
        instruction3['op2'] = 3  # Destination of the second load
        instruction3['imm'] = False

        my_pipe._memory._RAM[2] = instruction3._bits

        # Opcode: 001110 (STR) Src: 00011 (Register 3) PADDING: 00000 (Bits 20-16 are Irrelevant) Base/Literal: 11111
        # (Register 31) Offset/Literal: 0000000000 (Offset 0) TODO - is this a register number or a literal????
        #  Assuming reg num for now

        instruction4 = OpCode_InstructionType_lookup[0b001110].encoding()
        instruction4['opcode'] = 0b001110
        instruction4['src'] = 24  # Destination of the add op
        instruction4['base'] = 16  # Register holding the address we want to store the result (Register 16)
        instruction4['offset'] = 0

        my_pipe._memory._RAM[3] = instruction4._bits
        my_pipe._registers[16] = 8

        # cook END instruction to signal pipeline to end
        end = OpCode_InstructionType_lookup[0b100000].encoding()
        end['opcode'] = 0b100000
        my_pipe._memory._RAM[4] = end._bits  # END is stored at address (word) 1 in memory

        # my_pipe.cycle(20)  # TODO - Acceptable number of cycles... I guess...
        my_pipe.cycle_pipeline()
        my_pipe.cycle_pipeline()
        my_pipe.cycle_pipeline()
        my_pipe.cycle_pipeline()
        my_pipe.cycle_pipeline()
        my_pipe.cycle_pipeline()
        my_pipe.cycle_pipeline()
        my_pipe.cycle_pipeline()
        my_pipe.cycle_pipeline()
        my_pipe.cycle_pipeline()
        my_pipe.cycle_pipeline()
        my_pipe.cycle_pipeline()
        my_pipe.cycle_pipeline()
        my_pipe.cycle_pipeline()
        my_pipe.cycle_pipeline()
        my_pipe.cycle_pipeline()
        my_pipe.cycle_pipeline()
        my_pipe.cycle_pipeline()
        my_pipe.cycle_pipeline()
        my_pipe.cycle_pipeline()

        self.assertEqual(my_pipe._memory._RAM[12] + my_pipe._memory._RAM[13], my_pipe._memory._RAM[8])


if __name__ == '__main__':
    unittest.main()
