import unittest

from numpy.random import default_rng

from clock import *
from eisa import EISA
from memory_subsystem import MemorySubsystem
from ui import EISADialog
from pipeline import *
import os

class pipeline_stress_test(unittest.TestCase):

    memory = MemorySubsystem(EISA.ADDRESS_SIZE, 4, 1, 1, 8, 2, 2)
    pipeline = PipeLine(0, [1 for i in range(EISA.NUM_GP_REGS)], memory)
    max_instructions = 20000
    exchange_array_size = 100

    def test_add_str(self):
        # Run the assembler with the dedicated files
        command = 'assembler.py ../asrc/test_add_str.asm -o ../asrc/test_add_str.out'
        os.system(command)

        # Check whether the output file exists and open it
        assembled_file = open('../asrc/test_add_str.out')

        # Open the verification file that the output should match
        verification_file = open('../asrc/test_add_str.expected')

        # Read in the lines for both files and strip the whitespace
        assembled_lines = [i.strip() for i in assembled_file.readlines()]
        verified_lines = [i.strip() for i in verification_file.readlines()]

        # Close filepointers
        assembled_file.close()
        verification_file.close()

        # Verify that they both have the same number of lines
        self.assertEqual(len(assembled_lines), len(verified_lines))

        # Compare each line, as the assembled lines should match the verified lines exactly
        for i in range(len(assembled_lines)):
            self.assertEqual(verified_lines[i], assembled_lines[i])

        #############################################################################
        ##### Now that the lines have been verified, load them into the pipeline#####
        #############################################################################

        # Loop over the assembled lines and convert them into ints by reading them as base 2,
        #   loading directly into ram
        for i in range(len(assembled_lines)):
            self.memory._RAM[i] = int(assembled_lines[i], 2)

        # Cycle until an END instruction is found in writeback
        #   If no END instruction is encounter within 20k cycles,
        #   report a failure.
        cycle_counter = 0
        while self.pipeline._pipeline[4].opcode != OpCode.END and cycle_counter <= self.max_instructions:
            self.pipeline.cycle_pipeline()
            cycle_counter += 1

        self.assertLessEqual(cycle_counter, self.max_instructions)

        # Verify arithmetic
        self.assertEqual(20, self.pipeline._registers[1])  # ADD R1, R1, #20
        self.assertEqual(30, self.pipeline._registers[2])  # ADD R2, R2, #30
        self.assertEqual(self.pipeline._registers[1] + self.pipeline._registers[2],
                         self.pipeline._registers[3])  # ADD R3, R1, R2
        self.assertEqual(self.pipeline._registers[3], self.memory._RAM[45])  # STR R3, #45

        # Done

    def test_load(self):
        # Run the assembler with the dedicated files
        command = 'assembler.py ../asrc/test_load.asm -o ../asrc/test_load.out'
        os.system(command)

        # Check whether the output file exists and open it
        assembled_file = open('../asrc/test_load.out')

        # Open the verification file that the output should match
        verification_file = open('../asrc/test_load.expected')

        # Read in the lines for both files and strip the whitespace
        assembled_lines = [i.strip() for i in assembled_file.readlines()]
        verified_lines = [i.strip() for i in verification_file.readlines()]

        # Close filepointers
        assembled_file.close()
        verification_file.close()

        # Verify that they both have the same number of lines
        self.assertEqual(len(assembled_lines), len(verified_lines))

        # Compare each line, as the assembled lines should match the verified lines exactly
        for i in range(len(assembled_lines)):
            self.assertEqual(verified_lines[i], assembled_lines[i])

        #############################################################################
        ##### Now that the lines have been verified, load them into the pipeline#####
        #############################################################################

        # Loop over the assembled lines and convert them into ints by reading them as base 2,
        #   loading directly into ram
        for i in range(len(assembled_lines)):
            self.memory._RAM[i] = int(assembled_lines[i], 2)

        # Cycle until an END instruction is found in writeback.
        #   If no END instruction is encounter within 20k cycles,
        #   report a failure.
        cycle_counter = 0
        while self.pipeline._pipeline[4].opcode != OpCode.END and cycle_counter <= self.max_instructions:
            self.pipeline.cycle_pipeline()
            cycle_counter += 1

        self.assertLessEqual(cycle_counter, self.max_instructions)

        # Verify arithmetic
        self.assertEqual(20, self.pipeline._registers[1])
        self.assertEqual(self.pipeline._registers[1], self.memory._RAM[45])
        self.assertEqual(self.pipeline._registers[2], self.memory._RAM[45])

        # Done

    def test_conditional_branch(self):
        # Run the assembler with the dedicated files
        command = 'assembler.py ../asrc/test_conditional_branch.asm -o ../asrc/test_conditional_branch.out'
        os.system(command)

        # Check whether the output file exists and open it
        assembled_file = open('../asrc/test_conditional_branch.out')

        # Open the verification file that the output should match
        verification_file = open('../asrc/test_conditional_branch.expected')

        # Read in the lines for both files and strip the whitespace
        assembled_lines = [i.strip() for i in assembled_file.readlines()]
        verified_lines = [i.strip() for i in verification_file.readlines()]

        # Close filepointers
        assembled_file.close()
        verification_file.close()

        # Verify that they both have the same number of lines
        self.assertEqual(len(assembled_lines), len(verified_lines))

        # Compare each line, as the assembled lines should match the verified lines exactly
        for i in range(len(assembled_lines)):
            self.assertEqual(verified_lines[i], assembled_lines[i])

        #############################################################################
        ##### Now that the lines have been verified, load them into the pipeline#####
        #############################################################################

        # Loop over the assembled lines and convert them into ints by reading them as base 2,
        #   loading directly into ram
        for i in range(len(assembled_lines)):
            self.memory._RAM[i] = int(assembled_lines[i], 2)

        # Cycle until an END instruction is found in writeback.
        #   If no END instruction is encounter within 20k cycles,
        #   report a failure.
        cycle_counter = 0
        while self.pipeline._pipeline[4].opcode != OpCode.END and cycle_counter <= self.max_instructions:
            self.pipeline.cycle_pipeline()
            cycle_counter += 1

        self.assertLessEqual(cycle_counter, self.max_instructions)

        # Verify arithmetic
        self.assertEqual(25, self.pipeline._registers[25])

        # Done

    def test_unconditional_branching(self):
        # Run the assembler with the dedicated files
        command = 'assembler.py ../asrc/test_unconditional_branching.asm -o ../asrc/test_unconditional_branching.out'
        os.system(command)

        # Check whether the output file exists and open it
        assembled_file = open('../asrc/test_unconditional_branching.out')

        # Open the verification file that the output should match
        verification_file = open('../asrc/test_unconditional_branching.expected')

        # Read in the lines for both files and strip the whitespace
        assembled_lines = [i.strip() for i in assembled_file.readlines()]
        verified_lines = [i.strip() for i in verification_file.readlines()]

        # Close filepointers
        assembled_file.close()
        verification_file.close()

        # Verify that they both have the same number of lines
        self.assertEqual(len(assembled_lines), len(verified_lines))

        # Compare each line, as the assembled lines should match the verified lines exactly
        for i in range(len(assembled_lines)):
            self.assertEqual(verified_lines[i], assembled_lines[i])

        #############################################################################
        ##### Now that the lines have been verified, load them into the pipeline#####
        #############################################################################

        # Loop over the assembled lines and convert them into ints by reading them as base 2,
        #   loading directly into ram
        for i in range(len(assembled_lines)):
            self.memory._RAM[i] = int(assembled_lines[i], 2)

        # Cycle until an END instruction is found in writeback.
        #   If no END instruction is encounter within 20k cycles,
        #   report a failure.
        cycle_counter = 0
        while self.pipeline._pipeline[4].opcode != OpCode.END and cycle_counter <= self.max_instructions:
            self.pipeline.cycle_pipeline()
            cycle_counter += 1
            if self.pipeline.cycle_pipeline()._pc == 10:
                self.assertEqual(253, self.pipeline.sp)  # Verify that the stack pointer changed after 2 pushes
                self.assertEqual(10, self.memory._RAM[255])  # Verify that the initial position of the stack pointer is
                                                             #   loaded with the correct value

        self.assertLessEqual(cycle_counter, self.max_instructions)

        # Verify arithmetic
        self.assertEqual(10, self.pipeline._registers[3])  # If this is 0, that means line 12 executed when it shouldn't have
        self.assertEqual(20, self.pipeline._registers[1])
        self.assertEqual(10, self.pipeline._registers[2])

        # Done

    def test_branching_and_link(self):
        # this test uses order of operations
        # if branch + link works, it should do R0 = ((10 * 2) + 5) * 2 = 50
        # if it just does branching it should do R0 = (10 * 2) = 10
        # if it does not branch it should do R0 = (10 + 5) * 2 = 30

        assembled_lines = verify_assembly('../asrc/test_branch_link', self)

        # write the program to RAM
        for i in range(len(assembled_lines)):
            self.memory._RAM[i] = int(assembled_lines[i], 2)

        # run the program
        cycle_counter = 0
        while self.pipeline._pipeline[4].opcode != OpCode.END and cycle_counter <= self.max_instructions:
            self.pipeline.cycle_pipeline()
            cycle_counter += 1

        self.assertEqual(50, self.memory._RAM[6])

    def test_exchange_sort_descending(self):
        """ Copied and edited from from ui.py (self.load_matrix_demo)"""

        # Filepath to exchange sort binary
        sort_fp = "../demos/exchange_sort.expected"

        # Try to open the filepath
        try:
            self.fp = open(sort_fp)
        except Exception as e:
            print(f"Failed to open {sort_fp}")
            return

        # Read binary lines from exchange_sort.expected
        with self.fp as f:
            content = f.readlines()
        program_lines = [x.strip() for x in content]  # Remove whitespace

        word_counter = 0  # Number of words that are instructions - 1
        array_size = self.exchange_array_size  # FIXME - How large is the array for the exchange sort demo?

        # Load binary lines into RAM as base 2 integers, converting them to base 10 (decimal) in the process
        for i in range(len(program_lines)):
            self.memory._RAM[i] = int(program_lines[i], 2)
            word_counter += 1  # Increment word counter to insert unsorted data IMMEDIATELY after the instructions

        # Insert 'array_size' random ints after the last instruction for the exchange sort
        #   Note - I put in a descending ordered list instead of random values
        for i in range(word_counter, array_size + word_counter):
            self.memory._RAM[i] = array_size - i

        """ Copied and edited from ui.py (self.cycle_ui) """
        #  Cycle the pipeline until either an END op is found in writeback or the cycle limit is reached
        while self.pipeline._pipeline[4].opcode != 32:
            self.pipeline.cycle_pipeline()
            if self.pipeline._cycles >= EISA.PROGRAM_MAX_CYCLE_LIMIT:
                print(f"Error: Exceeded maximum number of program cycles: {self.max_instructions}")
                break
        self.pipeline.cycle_pipeline()

        # Verify that each element in the array is less than or equal to its adjacent successor
        for i in range(word_counter, array_size + word_counter - 1):
            self.assertLessEqual(self.memory._RAM[i], self.memory._RAM[i+1])

    def test_exchange_sort_same_value(self):
        """ Copied and edited from from ui.py (self.load_matrix_demo)"""

        # Filepath to exchange sort binary
        sort_fp = "../demos/exchange_sort.expected"

        # Try to open the filepath
        try:
            self.fp = open(sort_fp)
        except Exception as e:
            print(f"Failed to open {sort_fp}")
            return

        # Read binary lines from exchange_sort.expected
        with self.fp as f:
            content = f.readlines()
        program_lines = [x.strip() for x in content]  # Remove whitespace

        word_counter = 0  # Number of words that are instructions - 1
        array_size = self.exchange_array_size  # FIXME - How large is the array for the exchange sort demo?

        # Load binary lines into RAM as base 2 integers, converting them to base 10 (decimal) in the process
        for i in range(len(program_lines)):
            self.memory._RAM[i] = int(program_lines[i], 2)
            word_counter += 1  # Increment word counter to insert unsorted data IMMEDIATELY after the instructions

        # Insert 'array_size' random ints after the last instruction for the exchange sort
        #   Note - this test uses values of all 1 for the array to see what happens when only duplicate values exist
        for i in range(word_counter, array_size + word_counter):
            self.memory._RAM[i] = 1

        """ Copied and edited from ui.py (self.cycle_ui) """
        #  Cycle the pipeline until either an END op is found in writeback or the cycle limit is reached
        while self.pipeline._pipeline[4].opcode != 32:
            self.pipeline.cycle_pipeline()
            if self.pipeline._cycles >= EISA.PROGRAM_MAX_CYCLE_LIMIT:
                print(f"Error: Exceeded maximum number of program cycles: {self.max_instructions}")
                break
        self.pipeline.cycle_pipeline()

        # Verify that each element in the array is less than or equal to its adjacent successor
        for i in range(word_counter, array_size + word_counter - 1):
            self.assertEqual(self.memory._RAM[i], self.memory._RAM[i+1])

    def test_exchange_sort_mixed(self):
        """ Copied and edited from from ui.py (self.load_matrix_demo)"""

        # Filepath to exchange sort binary
        sort_fp = "../demos/exchange_sort.expected"

        # Try to open the filepath
        try:
            self.fp = open(sort_fp)
        except Exception as e:
            print(f"Failed to open {sort_fp}")
            return

        # Read binary lines from exchange_sort.expected
        with self.fp as f:
            content = f.readlines()
        program_lines = [x.strip() for x in content]  # Remove whitespace

        word_counter = 0  # Number of words that are instructions - 1
        array_size = self.exchange_array_size  # FIXME - How large is the array for the exchange sort demo?

        # Load binary lines into RAM as base 2 integers, converting them to base 10 (decimal) in the process
        for i in range(len(program_lines)):
            self.memory._RAM[i] = int(program_lines[i], 2)
            word_counter += 1  # Increment word counter to insert unsorted data IMMEDIATELY after the instructions

        # Insert 'array_size' random ints after the last instruction for the exchange sort
        #   Note - this test mixes 1s and 0s randomly
        for i in range(word_counter, array_size + word_counter):
            rng = default_rng(12345)
            rints = rng.integers(low=0, high=10, size=1)
            if rints[0] >= 5:
                self.memory._RAM[i] = 1
            else:
                self.memory._RAM[i] = 0

        """ Copied and edited from ui.py (self.cycle_ui) """
        #  Cycle the pipeline until either an END op is found in writeback or the cycle limit is reached
        while self.pipeline._pipeline[4].opcode != 32:
            self.pipeline.cycle_pipeline()
            if self.pipeline._cycles >= EISA.PROGRAM_MAX_CYCLE_LIMIT:
                print(f"Error: Exceeded maximum number of program cycles: {self.max_instructions}")
                break
        self.pipeline.cycle_pipeline()

        # Verify that each element in the array is less than or equal to its adjacent successor
        for i in range(word_counter, array_size + word_counter - 1):
            self.assertLessEqual(self.memory._RAM[i], self.memory._RAM[i+1])

def verify_assembly(path: str, test: unittest.TestCase) -> List[int]:
    src_path = path + '.asm'
    dest_path = path + '.out'
    expected_path = path + '.expected'

    command = f'assembler.py {src_path} -o {dest_path}'
    os.system(command)

    # Check whether the output file exists and open it
    assembled_file = open(dest_path)

    # Open the verification file that the output should match
    verification_file = open(expected_path)

    # Read in the lines for both files and strip the whitespace
    assembled_lines = [i.strip() for i in assembled_file.readlines()]
    verified_lines = [i.strip() for i in verification_file.readlines()]

    # Close filepointers
    assembled_file.close()
    verification_file.close()

    # Verify that they both have the same number of lines
    test.assertEqual(len(assembled_lines), len(verified_lines))

    # Compare each line, as the assembled lines should match the verified lines exactly
    for i in range(len(assembled_lines)):
        test.assertEqual(verified_lines[i], assembled_lines[i])

    return assembled_lines

if __name__ == '__main__':
    unittest.main()
