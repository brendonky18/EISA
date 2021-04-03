import unittest
from pipeline import *
from eisa import EISA
from clock import *
from memory_subsystem import MemorySubsystem


class UnittestPipeline(unittest.TestCase):
    

    # Add 2 registers together. Confirm that the result is stored
    #   into another register
    def test_addition_simple(self):

        mem_sub = MemorySubsystem(EISA.ADDRESS_SIZE, 4, 1, 1, 8, 2, 2)

        Clock.start()

        my_pipe = PipeLine(0, [1 for i in range(EISA.NUM_GP_REGS)], mem_sub)

        my_pipe._registers[31] = 10
        my_pipe._registers[4] = 30

        my_pipe._memory[0] = 0b00001100000000000111110010000011
        my_pipe.cycle(5)

        Clock.stop()

        self.assertEqual(40, my_pipe._registers[3])

    def test_load_2_operands(self):
        mem_sub = MemorySubsystem(EISA.ADDRESS_SIZE, 4, 1, 1, 8, 2, 2)

        Clock.start()

        my_pipe = PipeLine(0, [1 for i in range(EISA.NUM_GP_REGS)], mem_sub)

        my_pipe._memory[0] = 0b01000100000000000111110010000000

        my_pipe._memory[4] = 555

        my_pipe.cycle(5)

        print(my_pipe._registers)

        Clock.stop()

        self.assertEqual(555, my_pipe._registers[31])

    def test_store_simple(self):
        mem_sub = MemorySubsystem(EISA.ADDRESS_SIZE, 4, 1, 1, 8, 2, 2)

        Clock.start()

        my_pipe = PipeLine(0, [1 for i in range(EISA.NUM_GP_REGS)], mem_sub)

        # Gets value to store from reg 31 (11111) (the value stored is 555)

        # Attempts to store @ address 4 (00100) with offset 0 (00000)

        my_pipe._memory[0] = 0b01000000000000000111110010000000

        my_pipe._registers[31] = 555

        my_pipe.cycle(6)

        retrieved = my_pipe._memory[4]

        Clock.stop()

        self.assertEqual(555, retrieved)

    def test_load_store_alu(self):

        mem_sub = MemorySubsystem(EISA.ADDRESS_SIZE, 4, 1, 1, 8, 2, 2)

        Clock.start()

        my_pipe = PipeLine(0, [i for i in range(EISA.NUM_GP_REGS)], mem_sub)

        # Load value into reg 31 from address 4 + 0 offset

        my_pipe._memory[0] = 0b01000100000000000111110010000000

        # Add value in reg 31 with value in reg 4, store in reg 3

        my_pipe._memory[1] = 0b00001100000000000111110010000011

        # Gets value to store from reg 3 (11111) (the value stored is 555)

        # Attempts to store @ address 5 (00101) with offset 0 (00000)

        my_pipe._memory[2] = 0b01000000000000000111110010100000

        my_pipe._memory[3] = 0b10001100000000000000000000000000

        # Value to be loaded in reg 31

        my_pipe._memory[4] = 555

        # Value in reg 4 to add to the value stored in reg 31

        my_pipe._registers[4] = 30

        # Num instructions + num stages + 1

        cycleCounter = 0

        while my_pipe._pipeline[4]._opcode != 0b100011:

            print(my_pipe._pipeline[4]._opcode)

            cycleCounter+=1
            my_pipe.cycle_pipeline()

        Clock.stop()

        print(cycleCounter)

        self.assertEqual(555, my_pipe._registers[31])

        print(my_pipe._registers)

        self.assertEqual(585, my_pipe._registers[3])

        self.assertEqual(585, my_pipe._memory[5])




if __name__ == '__main__':
    unittest.main()
