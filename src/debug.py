import argparse
import sys
from typing import List
from threading import Lock
from memory_subsystem import MemorySubsystem, PipelineStall
from clock import Clock
from commandparse import CommandParser, commandparse_cb, InputError
from pipeline import PipeLine, Instruction
from eisa import EISA
from time import sleep

def main(memory: MemorySubsystem, pipeline: PipeLine):
    if __name__ != 'debug':
        from debug import terminal_print

    @commandparse_cb
    def cache_read(addr: int):

        stalled = True
        while stalled:
            try:
                ret = memory[addr]
            except PipelineStall:
                sleep(0.001)
            else: 
                stalled = False

        terminal_print(f'Reading from address {addr}\n{addr:#0{4}x}: {ret}')


    @commandparse_cb
    def cache_write(addr: int, val: int):
        stalled = True
        while stalled:
            try:
                memory[addr] = val
            except PipelineStall:
                sleep(0.001)
            else: 
                stalled = False

        terminal_print(f'Wrote {val} to address {addr}')

        


    @commandparse_cb
    def view(device: str, start: int, size: int):
        if device.lower() == 'ram':
            terminal_print(memory._RAM.__str__(start, size))
        elif device.lower() == 'cache':
            terminal_print(memory._cache.__str__(start, size))
        else:
            terminal_print(f'<{device}> is not a valid memory device')


    @commandparse_cb
    def view_way(index: int):
        address = index << 2
        terminal_print(str(memory._cache.get_cacheway(address)))


    @commandparse_cb
    def clock(mode: str):
        mode = mode.lower()
        if mode == 'start':
            Clock.start()
            terminal_print('Clock started')
        elif mode == 'stop':
            Clock.stop()
            terminal_print('Clock stopped')
        else:
            terminal_print(f'<{mode}> is not a valid option, please enter start/stop')


    @commandparse_cb
    def step_clock(steps: int):
        terminal_print(f'Clock stepping {steps} iterations')
        Clock.step(steps)


    @commandparse_cb
    def load_program(file_path: str, start_addr: int):
        # read instructions from the file
        try:
            with open(file_path, 'r') as f:
                program_instructions: List[int] = []  # 2 indicates converting from a base 2 string
                for line in f:
                    val = line.rstrip().split('#', maxsplit=1)[0]
                    
                    try:
                        conv = int(val, 2)
                    except ValueError:
                        pass
                    else:
                        program_instructions.append(conv)
        except FileNotFoundError:
            raise InputError(f'File \'{file_path}\' not found. No such file exitst')

        # load them into memory
        stop_addr = start_addr + len(program_instructions)
        if stop_addr > memory._RAM._local_addr_space:
            raise ValueError(
                f'Program requires {len(program_instructions) * 4} bytes and is too large to be loaded starting at address {start_addr}')

        for dest_addr, cur_instruction in zip(range(start_addr, stop_addr), program_instructions):
            stalled = True
            while stalled:
                try:
                    memory[dest_addr] = cur_instruction
                except PipelineStall:
                    sleep(0.001)
                else: 
                    stalled = False

    @commandparse_cb
    def run_pipeline(cycle_count: int):
        pipeline.cycle(cycle_count)
        terminal_print('pipeline ran')


    @commandparse_cb
    def view_piepline():
        terminal_print(str(pipeline))


    @commandparse_cb
    def view_registers():
        terminal_print(f'{pipeline._registers}')

    '''
    @commandparse_cb
    def build_ui():
        dialog = Dialog(memory, pipeline)
        dialog.build_ui()
    '''

    cmd_parser.add_command('read', [int], cache_read)
    cmd_parser.add_command('write', [int, int], cache_write)
    cmd_parser.add_command('view', [str, int, int], view)
    cmd_parser.add_command('show', [str, int, int], view)  # alias for the view command
    cmd_parser.add_command('view-way', [int], view_way)
    cmd_parser.add_command('show-way', [int], view_way)  # alias
    cmd_parser.add_command('clock', [str], clock)
    cmd_parser.add_command('step', [int], step_clock)
    cmd_parser.add_command('load', [str, int], load_program)
    cmd_parser.add_command('cycle', [int], run_pipeline)
    cmd_parser.add_command('show-pipeline', [], view_piepline)
    cmd_parser.add_command('show-registers', [], view_registers)
    #cmd_parser.add_command('build-ui', [], build_ui)

    cmd_parser.start()

    return

print_lock: Lock = Lock()

def terminal_print(print_string: str):
    global terminal_name
    with print_lock:
        print(f'\r{print_string}')

        print(terminal_name, end='$ ', flush=True)

    return

def set_terminal_name(name: str):
    global terminal_name
    terminal_name = name

if __name__ == '__main__':
    arg_parser = argparse.ArgumentParser()

    # add command line arguments
    arg_parser.add_argument('-cs', action='store', type=int,
                            help='the size of the cache, in words')  # arg to get cache size
    arg_parser.add_argument('-rs', action='store', type=int,
                            help='the size of the RAM, in words')  # arg to get memory size
    arg_parser.add_argument('-n', action='store', type=str,
                            help='the size of the RAM, in words')  # arg to get memory size

    args = arg_parser.parse_args()

    cmd_parser = CommandParser('dbg' if args.n is None else args.n)

    terminal_name = None
    
    import debug

    debug.set_terminal_name(args.n)

    memory = MemorySubsystem(EISA.ADDRESS_SIZE, args.cs, 1, 1, args.rs, 2, 2)
    pipeline = PipeLine(0, [0] * 32, memory)
    main(memory, pipeline)