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

if __name__ == '__main__':
    unittest.main()
