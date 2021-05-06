import unittest

from numpy.random import default_rng

from clock import *
from eisa import EISA
from memory_subsystem import MemorySubsystem
from ui import EISADialog
import aenum
from pipeline import *
import os
import subprocess, shlex

dir_name = os.path.dirname(__file__)
assembler_path = os.path.join(dir_name, 'assembler.py')


class pipeline_stress_test(unittest.TestCase):
    memory = MemorySubsystem(EISA.ADDRESS_SIZE, 4, 1, 1, EISA.ADDRESS_SIZE, 2, 2)
    pipeline = PipeLine(0, [0 for i in range(EISA.NUM_GP_REGS)], memory)
    max_instructions = 20000
    exchange_array_size = 100
    exchange_sort_length = 0

    def test_add_str(self):

        # Reset the PC, cycle counter, and the 'finished' status for the next test
        self.pipeline._pc = 0
        self.pipeline._cycles = 0
        self.pipeline._is_finished = False
        self.pipeline._pipeline = [Instruction(self.pipeline) for i in range(len(self.pipeline._pipeline))]
        self.pipeline._registers = [0 for i in range(len(self.pipeline._registers))]
        self.pipeline._registers[SpecialRegister.sp] = int(SpecialRegister['bp'])

        test_name = "test_add_str"

        # Run the assembler with the dedicated files, and load the binary into RAM
        self.verify_assembly(test_name)

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

        # Reset the PC, cycle counter, and the 'finished' status for the next test
        self.pipeline._pc = 0
        self.pipeline._cycles = 0
        self.pipeline._is_finished = False
        self.pipeline._pipeline = [Instruction(self.pipeline) for i in range(len(self.pipeline._pipeline))]
        self.pipeline._registers = [0 for i in range(len(self.pipeline._registers))]
        self.pipeline._registers[SpecialRegister.sp] = int(SpecialRegister['bp'])

        test_name = "test_load"

        # Run the assembler with the dedicated files, and load the binary into RAM
        self.verify_assembly(test_name)

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

        # Reset the PC, cycle counter, and the 'finished' status for the next test
        self.pipeline._pc = 0
        self.pipeline._cycles = 0
        self.pipeline._is_finished = False
        self.pipeline._pipeline = [Instruction(self.pipeline) for i in range(len(self.pipeline._pipeline))]
        self.pipeline._registers = [0 for i in range(len(self.pipeline._registers))]
        self.pipeline._registers[SpecialRegister.sp] = int(SpecialRegister['bp'])

        test_name = "test_conditional_branch"

        # Run the assembler with the dedicated files, and load the binary into RAM
        self.verify_assembly(test_name)

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

        # Reset the PC, cycle counter, and the 'finished' status for the next test
        self.pipeline._pc = 0
        self.pipeline._cycles = 0
        self.pipeline._is_finished = False
        self.pipeline._pipeline = [Instruction(self.pipeline) for i in range(len(self.pipeline._pipeline))]
        self.pipeline._registers = [0 for i in range(len(self.pipeline._registers))]
        self.pipeline._registers[SpecialRegister.sp] = int(SpecialRegister['bp'])

        test_name = "test_unconditional_branching"

        # Run the assembler with the dedicated files, and load the binary into RAM
        self.verify_assembly(test_name)

        # Cycle until an END instruction is found in writeback.
        #   If no END instruction is encounter within 20k cycles,
        #   report a failure.
        cycle_counter = 0
        validated_last_push = False
        while self.pipeline._pipeline[4].opcode != OpCode.END and cycle_counter <= self.max_instructions:
            self.pipeline.cycle_pipeline()
            cycle_counter += 1
            if self.pipeline._cycles == 24:
                self.assertEqual(8189, self.pipeline.sp)  # Verify that the stack pointer changed after 2 pushes
                self.assertEqual(10, self.memory._RAM[8191])  # Verify that the initial position of the stack pointer is
                #   loaded with the correct value
            if self.pipeline.sp == 8188 and self.memory._RAM[8189] == 20:
                validated_last_push = True


        self.assertLessEqual(cycle_counter, self.max_instructions)
        self.assertTrue(validated_last_push)

        # Verify arithmetic
        self.assertEqual(10, self.pipeline._registers[
            3])  # If this is 0, that means line 12 executed when it shouldn't have
        self.assertEqual(20, self.pipeline._registers[1])
        self.assertEqual(10, self.pipeline._registers[2])

        # Done

    def test_branch_link(self):
        # this test uses order of operations
        # if branch + link works, it should do R0 = ((10 * 2) + 5) * 2 = 50
        # if it just does branching it should do R0 = (10 * 2) = 10
        # if it does not branch it should do R0 = (10 + 5) * 2 = 30

        # Reset the PC, cycle counter, and the 'finished' status for the next test
        self.pipeline._pc = 0
        self.pipeline._cycles = 0
        self.pipeline._is_finished = False
        self.pipeline._pipeline = [Instruction(self.pipeline) for i in range(len(self.pipeline._pipeline))]
        self.pipeline._registers = [0 for i in range(len(self.pipeline._registers))]
        self.pipeline._registers[SpecialRegister.sp] = int(SpecialRegister['bp'])

        test_name = "test_branch_link"

        # Run the assembler with the dedicated files, and load the binary into RAM
        self.verify_assembly(test_name)

        # Cycle until an END instruction is found in writeback.
        #   If no END instruction is encounter within 20k cycles,
        #   report a failure.
        cycle_counter = 0
        while self.pipeline._pipeline[4].opcode != OpCode.END and cycle_counter <= self.max_instructions:
            self.pipeline.cycle_pipeline()
            cycle_counter += 1

        # Verify arithmetic
        self.assertEqual(50, self.memory._RAM[6])

        # Done

    def test_exchange_sort_descending(self):

        # Reset the PC, cycle counter, and the 'finished' status for the next test
        self.pipeline._pc = 0
        self.pipeline._cycles = 0
        self.pipeline._is_finished = False
        self.pipeline._pipeline = [Instruction(self.pipeline) for i in range(len(self.pipeline._pipeline))]
        self.pipeline._registers = [0 for i in range(len(self.pipeline._registers))]
        self.pipeline._registers[SpecialRegister.sp] = int(SpecialRegister['bp'])

        test_name = "test_exchange_sort"

        # Run the assembler with the dedicated files, and load the binary into RAM
        self.verify_assembly(test_name)

        word_counter = self.exchange_sort_length  # Number of words that are instructions - 1
        array_size = self.exchange_array_size  # FIXME - How large is the array for the exchange sort demo?

        # Insert 'array_size' random ints after the last instruction for the exchange sort
        #   Note - I put in a descending ordered list instead of random values
        for i in range(word_counter, array_size + word_counter):
            self.memory._RAM[i] = array_size - i

        """ Copied and edited from ui.py (self.cycle_ui) """
        #  Cycle the pipeline until either an END op is found in writeback or the cycle limit is reached
        while self.pipeline._pipeline[4].opcode != 32:
            self.pipeline.cycle_pipeline()
            if self.pipeline._cycles >= self.max_instructions:
                print(f"Error: Exceeded maximum number of program cycles: {self.max_instructions}")
                break
        self.pipeline.cycle_pipeline()

        # Verify that each element in the array is less than or equal to its adjacent successor
        for i in range(word_counter, array_size + word_counter - 1):
            self.assertLessEqual(self.memory._RAM[i], self.memory._RAM[i + 1])

        # Done

    def test_exchange_sort_same_value(self):

        # Reset the PC, cycle counter, and the 'finished' status for the next test
        self.pipeline._pc = 0
        self.pipeline._cycles = 0
        self.pipeline._is_finished = False
        self.pipeline._pipeline = [Instruction(self.pipeline) for i in range(len(self.pipeline._pipeline))]
        self.pipeline._registers = [0 for i in range(len(self.pipeline._registers))]
        self.pipeline._registers[SpecialRegister.sp] = int(SpecialRegister['bp'])

        test_name = "test_exchange_sort"

        # Run the assembler with the dedicated files, and load the binary into RAM
        self.verify_assembly(test_name)

        word_counter = self.exchange_sort_length  # Number of words that are instructions - 1
        array_size = self.exchange_array_size  # FIXME - How large is the array for the exchange sort demo?

        # Insert 'array_size' random ints after the last instruction for the exchange sort
        #   Note - this test uses values of all 1 for the array to see what happens when only duplicate values exist
        for i in range(word_counter, array_size + word_counter):
            self.memory._RAM[i] = 1

        """ Copied and edited from ui.py (self.cycle_ui) """
        #  Cycle the pipeline until either an END op is found in writeback or the cycle limit is reached
        while self.pipeline._pipeline[4].opcode != 32:
            self.pipeline.cycle_pipeline()
            if self.pipeline._cycles >= self.max_instructions:
                print(f"Error: Exceeded maximum number of program cycles: {self.max_instructions}")
                break
        self.pipeline.cycle_pipeline()

        # Verify that each element in the array is less than or equal to its adjacent successor
        for i in range(word_counter, array_size + word_counter - 1):
            self.assertEqual(self.memory._RAM[i], self.memory._RAM[i + 1])

        # Done

    def test_exchange_sort_mixed(self):

        # Reset the PC, cycle counter, and the 'finished' status for the next test
        self.pipeline._pc = 0
        self.pipeline._cycles = 0
        self.pipeline._is_finished = False
        self.pipeline._pipeline = [Instruction(self.pipeline) for i in range(len(self.pipeline._pipeline))]
        self.pipeline._registers = [0 for i in range(len(self.pipeline._registers))]
        self.pipeline._registers[SpecialRegister.sp] = int(SpecialRegister['bp'])

        test_name = "test_exchange_sort"

        # Run the assembler with the dedicated files, and load the binary into RAM
        self.verify_assembly(test_name)

        word_counter = self.exchange_sort_length  # Number of words that are instructions - 1
        array_size = self.exchange_array_size  # FIXME - How large is the array for the exchange sort demo?

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
            if self.pipeline._cycles >= self.max_instructions:
                print(f"Error: Exceeded maximum number of program cycles: {self.max_instructions}")
                break
        self.pipeline.cycle_pipeline()

        # Verify that each element in the array is less than or equal to its adjacent successor
        for i in range(word_counter, array_size + word_counter - 1):
            self.assertLessEqual(self.memory._RAM[i], self.memory._RAM[i + 1])

        # Done

    def verify_assembly(self, path: str) -> List[int]:
        src_file = path + '.asm'
        dest_file = path + '.out'
        expected_file = path + '.expected'

        src_path = os.path.join(dir_name, f'..\\asrc\\{src_file}')
        dest_path = os.path.join(dir_name, f'..\\asrc\\{dest_file}')
        expected_path = os.path.join(dir_name, f'..\\asrc\\{expected_file}')

        command = f'"python" "{assembler_path}" "{src_path}" -o "{dest_path}"'
        subprocess.run(shlex.split(command))

        # Check whether the output file exists and open it
        assembled_file = open(dest_path)

        # Open the verification file that the output should match
        verification_file = open(expected_path)

        # Read in the lines for both files and strip the whitespace
        assembled_lines = [i.strip() for i in assembled_file.readlines()]
        verified_lines = [i.strip() for i in verification_file.readlines()]

        if path == "test_exchange_sort":
            self.exchange_sort_length = len(assembled_lines)

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

        return assembled_lines


if __name__ == '__main__':
    unittest.main()
