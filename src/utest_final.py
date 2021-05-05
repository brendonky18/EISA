import unittest

from clock import *
from eisa import EISA
from memory_subsystem import MemorySubsystem
from pipeline import *
import os

dir_name = os.path.dirname(__file__)
assembler_path = os.path.join(dir_name, 'assembler.py')
class pipeline_stress_test(unittest.TestCase):

    memory = MemorySubsystem(EISA.ADDRESS_SIZE, 4, 1, 1, 8, 2, 2)
    pipeline = PipeLine(0, [1 for i in range(EISA.NUM_GP_REGS)], memory)
    max_instructions = 20000

    def test_add_str(self):
        # Run the assembler with the dedicated files
        assembled_lines = verify_assembly('test_add_str', self)

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
        assembled_lines = verify_assembly('test_load', self)

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
        assembled_lines = verify_assembly('test_conditional_branch', self)

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
        assembled_lines = verify_assembly('test_unconditional_branching', self)    

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

        assembled_lines = verify_assembly('test_branch_link', self)

        # write the program to RAM
        for i in range(len(assembled_lines)):
            self.memory._RAM[i] = int(assembled_lines[i], 2)

        # run the program
        cycle_counter = 0
        while self.pipeline._pipeline[4].opcode != OpCode.END and cycle_counter <= self.max_instructions:
            self.pipeline.cycle_pipeline()
            cycle_counter += 1

        self.assertEqual(50, self.memory._RAM[6])

def verify_assembly(path: str, test: unittest.TestCase) -> List[int]:
    src_file = path + '.asm'
    dest_file = path + '.out'
    expected_file = path + '.expected'

    src_path = os.path.join(dir_name, f'../asrc/{src_file}')
    dest_path = os.path.join(dir_name, f'../asrc/{dest_file}')
    expected_path = os.path.join(dir_name, f'../asrc/{expected_file}')

    command = f'python {assembler_path} {src_path} -o {dest_path}'
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
