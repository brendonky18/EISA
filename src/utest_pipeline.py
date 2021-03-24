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
        my_pipe = PipeLine(0, [1 for i in range(EISA.NUM_GP_REGS)], mem_sub)

        my_pipe.registers[31] = 10
        my_pipe.registers[4] = 30

        my_pipe.memory[0] = 0b00001100000000000111110010000011
        my_pipe.cycle(5)

        self.assertEqual(40, my_pipe.registers[3])

    def test_load_2_operands(self):
        mem_sub = MemorySubsystem(EISA.ADDRESS_SIZE, 4, 1, 1, 8, 2, 2)
        my_pipe = PipeLine(0, [1 for i in range(EISA.NUM_GP_REGS)], mem_sub)

        my_pipe.memory[0] = 0b01000100000000000111110010000000

        my_pipe.memory[4] = 555

        my_pipe.cycle(5)

        print(my_pipe.registers)

        self.assertEqual(555, my_pipe.registers[31])

    def test_store_simple(self):
        mem_sub = MemorySubsystem(EISA.ADDRESS_SIZE, 4, 1, 1, 8, 2, 2)
        my_pipe = PipeLine(0, [1 for i in range(EISA.NUM_GP_REGS)], mem_sub)


        my_pipe.memory[0] = 0b01000000000000000111110010000000

        my_pipe.registers[31] = 555

        my_pipe.cycle(5)

        retrieved = my_pipe.memory[4]

        print(my_pipe.registers)

        self.assertEqual(555, retrieved)


if __name__ == '__main__':
    Clock.start()
    unittest.main()
    Clock.stop()