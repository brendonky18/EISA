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
        instruction = Instructions[OpCode.ADD].encoding()
        instruction['opcode'] = 0b000001
        instruction['dest'] = 0b00011
        instruction['op1'] = 0b11111
        instruction['op2'] = 0b00100
        instruction['imm'] = False

        # cook END instruction to signal pipeline to end
        end = Instructions[0b100000].encoding()

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
        instruction = Instructions[0b001101].encoding()
        instruction['opcode'] = 0b001101
        instruction['dest'] = 3
        instruction['lit'] = False
        instruction['base'] = 31
        instruction['offset'] = 0

        my_pipe._memory._RAM[0] = instruction._bits

        # cook END instruction to signal pipeline to end
        end = Instructions[0b100000].encoding()
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
        instruction = Instructions[0b001101].encoding()
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
        instruction2 = Instructions[0b001101].encoding()
        instruction2['opcode'] = 0b001101
        instruction2['dest'] = 4
        instruction2['lit'] = False
        instruction2['base'] = 30
        instruction2['offset'] = 0

        my_pipe._memory._RAM[1] = instruction2._bits

        my_pipe._memory._RAM[13] = 36
        my_pipe._registers[30] = 13

        # cook END instruction to signal pipeline to end
        end = Instructions[0b100000].encoding()
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

        instruction = Instructions[0b001110].encoding()
        instruction['opcode'] = 0b001110
        instruction['src'] = 3
        instruction['base'] = 31
        instruction['offset'] = 0

        my_pipe._memory._RAM[0] = instruction._bits  # Set the 0th word in memory to this instruction, such that it's
        # the first instruction the PC points to

        my_pipe._registers[31] = 18  # Storing to address 18 in memory

        my_pipe._registers[3] = 256  # storing value in register 3

        # cook END instruction to signal pipeline to end
        end = Instructions[0b100000].encoding()
        end['opcode'] = 0b100000
        my_pipe._memory._RAM[1] = end._bits  # END is stored at address (word) 1 in memory

        my_pipe.cycle(8)  # TODO - Why does store take less cycles than load???

        self.assertEqual(my_pipe._registers[3], my_pipe._memory._RAM[18])

    def test_load_add_store(self):

        # Registers in use: 3, 31, 4, 30, 24, 16
        # Memory in use: 0, 12, 1, 13, 2, 3, 4, 8

        mem_sub = MemorySubsystem(EISA.ADDRESS_SIZE, 4, 1, 1, 8, 2, 2)

        my_pipe = PipeLine(0, [1 for i in range(EISA.NUM_GP_REGS)], mem_sub)

        # Opcode: 001101 (LOAD)
        instruction = Instructions[0b001101].encoding()
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
        instruction2 = Instructions[0b001101].encoding()
        instruction2['opcode'] = 0b001101
        instruction2['dest'] = 4
        instruction2['lit'] = False
        instruction2['base'] = 30
        instruction2['offset'] = 0

        my_pipe._memory._RAM[1] = instruction2._bits

        my_pipe._memory._RAM[13] = 36
        my_pipe._registers[30] = 13

        # Opcode: 000001 (ADD/MOV)
        instruction3 = Instructions[0b000001].encoding()
        instruction3['opcode'] = 0b000001
        instruction3['dest'] = 24
        instruction3['op1'] = 4  # Destination of the first load
        instruction3['op2'] = 3  # Destination of the second load
        instruction3['imm'] = False

        my_pipe._memory._RAM[2] = instruction3._bits

        # Opcode: 001110 (STR) Src: 00011 (Register 3) PADDING: 00000 (Bits 20-16 are Irrelevant) Base/Literal: 11111
        # (Register 31) Offset/Literal: 0000000000 (Offset 0) TODO - is this a register number or a literal????
        #  Assuming reg num for now

        instruction4 = Instructions[0b001110].encoding()
        instruction4['opcode'] = 0b001110
        instruction4['src'] = 24  # Destination of the add op
        instruction4['base'] = 16  # Register holding the address we want to store the result (Register 16)
        instruction4['offset'] = 0

        my_pipe._memory._RAM[3] = instruction4._bits
        my_pipe._registers[16] = 8

        # cook END instruction to signal pipeline to end
        end = Instructions[0b100000].encoding()
        end['opcode'] = 0b100000
        my_pipe._memory._RAM[4] = end._bits  # END is stored at address (word) 1 in memory

        my_pipe.cycle(20)

        self.assertEqual(my_pipe._memory._RAM[12] + my_pipe._memory._RAM[13], my_pipe._memory._RAM[8])

    # Unconditional branch test
    # Equivalent to test_load_add_store with the exception that there is an unconditional branch following the two loads
    def test_unconditional_branching(self):

        # Registers in use: 3, 31, 4, 30, 24, 16, 12
        # Memory in use: 0, 12, 1, 13, 8, 30, 31, 32

        mem_sub = MemorySubsystem(EISA.ADDRESS_SIZE, 4, 1, 1, 8, 2, 2)

        my_pipe = PipeLine(0, [1 for i in range(EISA.NUM_GP_REGS)], mem_sub)

        # Opcode: 001101 (LOAD)
        instruction = Instructions[0b001101].encoding()
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
        instruction2 = Instructions[0b001101].encoding()
        instruction2['opcode'] = 0b001101
        instruction2['dest'] = 4
        instruction2['lit'] = False
        instruction2['base'] = 30
        instruction2['offset'] = 0

        my_pipe._memory._RAM[1] = instruction2._bits

        my_pipe._memory._RAM[13] = 36
        my_pipe._registers[30] = 13

        # Opcode: 011110 (B)
        instructionB = Instructions[0b011110].encoding()
        instructionB['opcode'] = 0b011110
        instructionB['cond'] = ConditionCode.EQ
        instructionB['imm'] = False
        instructionB['base'] = 12
        instructionB['offset'] = 0

        my_pipe._registers[12] = 30
        my_pipe._memory._RAM[2] = instructionB._bits

        # Opcode: 000001 (ADD/MOV)
        instruction3 = Instructions[0b000001].encoding()
        instruction3['opcode'] = 0b000001
        instruction3['dest'] = 24
        instruction3['op1'] = 4  # Destination of the first load
        instruction3['op2'] = 3  # Destination of the second load
        instruction3['imm'] = False

        my_pipe._memory._RAM[30] = instruction3._bits

        # Opcode: 001110 (STR) Src: 00011 (Register 3) PADDING: 00000 (Bits 20-16 are Irrelevant) Base/Literal: 11111
        # (Register 31) Offset/Literal: 0000000000 (Offset 0) TODO - is this a register number or a literal????
        #  Assuming reg num for now

        instruction4 = Instructions[0b001110].encoding()
        instruction4['opcode'] = 0b001110
        instruction4['src'] = 24  # Destination of the add op
        instruction4['base'] = 16  # Register holding the address we want to store the result (Register 16)
        instruction4['offset'] = 0

        my_pipe._memory._RAM[31] = instruction4._bits
        my_pipe._registers[16] = 8

        # cook END instruction to signal pipeline to end
        end = Instructions[0b100000].encoding()
        end['opcode'] = 0b100000
        my_pipe._memory._RAM[32] = end._bits  # END is stored at address (word) 1 in memory

        my_pipe.cycle(24)

        self.assertEqual(my_pipe._memory._RAM[12] + my_pipe._memory._RAM[13], my_pipe._memory._RAM[8])

    def test_branching_OOB(self):

        mem_sub = MemorySubsystem(EISA.ADDRESS_SIZE, 4, 1, 1, 8, 2, 2)

        my_pipe = PipeLine(0, [1 for i in range(EISA.NUM_GP_REGS)], mem_sub)

    def test_unconditional_looping(self):

        mem_sub = MemorySubsystem(EISA.ADDRESS_SIZE, 4, 1, 1, 8, 2, 2)

        my_pipe = PipeLine(0, [1 for i in range(EISA.NUM_GP_REGS)], mem_sub)

    def test_conditional_looping(self):

        mem_sub = MemorySubsystem(EISA.ADDRESS_SIZE, 4, 1, 1, 8, 2, 2)

        my_pipe = PipeLine(0, [1 for i in range(EISA.NUM_GP_REGS)], mem_sub)

        #  Conditional looping + branching test. Cleared as of 4/24
        my_pipe._registers[2] = 24  # Counter
        my_pipe._registers[0] = 20  # Condition to beat
        my_pipe._registers[1] = 1  # Amount to increment counter by
        my_pipe._registers[3] = 0  # Address to branch back to

        instruction1 = OpCode_InstructionType_lookup[0b001101].encoding()
        instruction1['opcode'] = 0b001101
        instruction1['dest'] = 25  # Load into register 25
        instruction1['base'] = 2  # Register 2 holds the memory address who's value loads into reg 25
        instruction1['offset'] = 0
        instruction1['lit'] = False

        instruction2 = OpCode_InstructionType_lookup[0b000001].encoding()
        instruction2['opcode'] = 0b0000001
        instruction2['dest'] = 31  # Put sum in reg 31
        instruction2['op1'] = 31  # Register 31 as op1
        instruction2['op2'] = 25  # Register 25 as op2
        instruction2['imm'] = False

        instruction3 = OpCode_InstructionType_lookup[0b000001].encoding()
        instruction3['opcode'] = 0b0000001
        instruction3['dest'] = 2  # Put sum in reg 2
        instruction3['op1'] = 2  # Register 2 as op1
        instruction3['op2'] = 1  # Register 1 as op1
        instruction3['imm'] = False

        # Opcode: 011110 (CMP)
        instructionC = OpCode_InstructionType_lookup[0b000011].encoding()
        instructionC['opcode'] = 0b000011
        instructionC['op1'] = 31  # Register 31 as op1
        instructionC['op2'] = 0  # Register 0 as op2
        instructionC['imm'] = False

        #  Add flag fields to branch instructions

        # .add_field('v', 22, 1)
        # .add_field('c', 23, 1)
        # .add_field('z', 24, 1)
        # .add_field('n', 25, 1)

        # Opcode: 011110 (B)
        instructionB = OpCode_InstructionType_lookup[0b011110].encoding()
        instructionB['opcode'] = 0b011110

        instructionB.add_field('z', 24, 1)
        instructionB['z'] = 1

        instructionB.add_field('or', 21, 1)
        instructionB['or'] = 1

        instructionB.add_field('n', 25, 1)
        instructionB['n'] = 1

        instructionB['imm'] = False
        instructionB['base'] = 3  # Register 3 has the address to branch back to
        instructionB['offset'] = 0

        instructionBLOCK = OpCode_InstructionType_lookup[0b0].encoding()
        instructionBLOCK['opcode'] = 0b0

        # cook END instruction to signal pipeline to end
        end = OpCode_InstructionType_lookup[0b100000].encoding()
        end['opcode'] = 0b100000

        my_pipe._memory._RAM[0] = instruction1._bits
        my_pipe._memory._RAM[1] = instruction2._bits
        my_pipe._memory._RAM[2] = instruction3._bits
        my_pipe._memory._RAM[3] = instructionC._bits
        my_pipe._memory._RAM[4] = instructionB._bits
        my_pipe._memory._RAM[5] = instructionBLOCK._bits
        my_pipe._memory._RAM[6] = end._bits

        my_pipe._memory._RAM[24] = 5
        my_pipe._memory._RAM[25] = 5
        my_pipe._memory._RAM[26] = 5
        my_pipe._memory._RAM[27] = 5
        my_pipe._memory._RAM[28] = 5
        my_pipe._memory._RAM[29] = 5

        my_pipe.cycle(77)

        self.assertEqual(25, my_pipe._registers[31])

    def test_unconditional_link(self):

        mem_sub = MemorySubsystem(EISA.ADDRESS_SIZE, 4, 1, 1, 8, 2, 2)

        my_pipe = PipeLine(0, [1 for i in range(EISA.NUM_GP_REGS)], mem_sub)

    def test_conditional_link(self):

        mem_sub = MemorySubsystem(EISA.ADDRESS_SIZE, 4, 1, 1, 8, 2, 2)

        my_pipe = PipeLine(0, [1 for i in range(EISA.NUM_GP_REGS)], mem_sub)

    def test_push_pop_sequential(self):
        mem_sub = MemorySubsystem(EISA.ADDRESS_SIZE, 4, 1, 1, 8, 2, 2)

        my_pipe = PipeLine(0, [i for i in range(EISA.NUM_GP_REGS)], mem_sub)

        # MOV - Copy R[29] into R[30]
        instruction1 = Instruction[0b000001].encoding()
        instruction1['opcode'] = 0b0000001
        instruction1['dest'] = 30  # Register 30
        instruction1['op1'] = 29  # Register 29
        instruction1['op2'] = 0  # IMM 0
        instruction1['imm'] = True

        # SUB - Reset R[31] to 0
        instruction2 = Instruction[0b000010].encoding()
        instruction2['opcode'] = 0b0000010
        instruction2['dest'] = 31  # Register 31
        instruction2['op1'] = 31  # Register 31
        instruction2['op2'] = 31  # IMM 31
        instruction2['imm'] = True

        # PUSH - Push R[0] to stack
        instruction3 = Instruction[0b001111].encoding()
        instruction3['opcode'] = 0b001111
        instruction3['src'] = 0 # R[0]

        # PUSH - Push R[1] to stack
        instruction4 = Instruction[0b001111].encoding()
        instruction4['opcode'] = 0b001111
        instruction4['src'] = 1  # R[1]

        # PUSH - Push R[2] to stack
        instruction5 = Instruction[0b001111].encoding()
        instruction5['opcode'] = 0b001111
        instruction5['src'] = 2  # R[2]

        # PUSH - Push R[3] to stack
        instruction6 = Instruction[0b001111].encoding()
        instruction6['opcode'] = 0b001111
        instruction6['src'] = 3  # R[3]

        # PUSH - Push R[4] to stack
        instruction7 = Instruction[0b001111].encoding()
        instruction7['opcode'] = 0b001111
        instruction7['src'] = 4  # R[4]

        # POP - Pop R[4] from stack into R[4]
        instruction8 = Instruction[0b010000].encoding()
        instruction8['opcode'] = 0b010000
        instruction8['dest'] = 4  # R[4]

        # POP - Pop R[3] from stack into R[3]
        instruction9 = Instruction[0b010000].encoding()
        instruction9['opcode'] = 0b010000
        instruction9['dest'] = 3  # R[3]

        # POP - Pop R[2] from stack into R[2]
        instruction10 = Instruction[0b010000].encoding()
        instruction10['opcode'] = 0b010000
        instruction10['dest'] = 2  # R[2]

        # POP - Pop R[1] from stack into R[1]
        instruction11 = Instruction[0b010000].encoding()
        instruction11['opcode'] = 0b010000
        instruction11['dest'] = 1  # R[1]

        # POP - Pop R[0] from stack into R[0]
        instruction12 = Instruction[0b010000].encoding()
        instruction12['opcode'] = 0b010000
        instruction12['dest'] = 0  # R[0]

        # END
        instruction13 = Instruction[0b100000].encoding()

        my_pipe._memory._RAM[0] = instruction1._bits
        my_pipe._memory._RAM[1] = instruction2._bits
        my_pipe._memory._RAM[2] = instruction3._bits
        my_pipe._memory._RAM[3] = instruction4._bits
        my_pipe._memory._RAM[4] = instruction5._bits
        my_pipe._memory._RAM[5] = instruction6._bits
        my_pipe._memory._RAM[6] = instruction7._bits
        my_pipe._memory._RAM[7] = instruction8._bits
        my_pipe._memory._RAM[8] = instruction9._bits
        my_pipe._memory._RAM[9] = instruction10._bits
        my_pipe._memory._RAM[10] = instruction11._bits
        my_pipe._memory._RAM[11] = instruction12._bits
        my_pipe._memory._RAM[12] = instruction13._bits



        for i in range(5):
            self.assertEqual(my_pipe._registers[i],i)

        #for i in range(5):
        #    self.assertEqual(my_pipe._registers[i], 0)






if __name__ == '__main__':
    unittest.main()
