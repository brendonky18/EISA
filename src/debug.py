import argparse
import sys
from typing import List, Tuple, Callable
from threading import Lock
from memory_subsystem import MemorySubsystem, PipelineStall
# from clock import Clock
from commandparse import CommandParser, commandparse_cb, InputError
from pipeline import PipeLine, Instruction
from eisa import EISA
from time import sleep
from termcolor import cprint

def init_commands(memory: MemorySubsystem, pipeline: PipeLine) -> List[Tuple[str, List, Callable[..., None]]]:
    if __name__ != 'debug':
        from debug import terminal_print

    @commandparse_cb
    def cache_read(addr: int) -> None:

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
    def cache_write(addr: int, val: int) -> None:
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
    def view(device: str, start: int, size: int) -> None:
        if device.lower() == 'ram':
            terminal_print(memory._RAM.__str__(start, size))
        elif device.lower() == 'cache':
            terminal_print(memory._cache.__str__(start, size))
        else:
            terminal_print(f'<{device}> is not a valid memory device')

    @commandparse_cb
    def view_way(index: int) -> None:
        address = index << 2
        terminal_print(str(memory._cache.get_cacheway(address)))

    '''
    @commandparse_cb
    def clock(mode: str) -> None:
        mode = mode.lower()
        if mode == 'start':
            Clock.start()
            terminal_print('Clock started')
        elif mode == 'stop':
            Clock.stop()
            terminal_print('Clock stopped')
        else:
            terminal_print(f'<{mode}> is not a valid option, please enter start/stop')
    '''

    '''
    @commandparse_cb
    def step_clock(steps: int) -> None:
        terminal_print(f'Clock stepping {steps} iterations')
        Clock.step(steps)
    '''

    @commandparse_cb
    def load_program(file_path: str, start_addr: int) -> None:
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
    def run_pipeline(cycle_count: int) -> None:
        pipeline.cycle(cycle_count)
        terminal_print('pipeline ran')

    @commandparse_cb
    def view_piepline() -> None:
        terminal_print(str(pipeline))

    @commandparse_cb
    def view_registers() -> None:
        terminal_print(f'{pipeline._registers}')
    
    commands = [ 
        ('read', [int], cache_read)
      , ('write', [int, int], cache_write)
      , ('view', [str, int, int], view)
      , ('show', [str, int, int], view)  # alias for the view command
      , ('view-way', [int], view_way)
      , ('show-way', [int], view_way)  # alias
      # , ('clock', [str], clock)
      # , ('step', [int], step_clock)
      , ('load', [str, int], load_program)
      , ('cycle', [int], run_pipeline)
      , ('show-pipeline', [], view_piepline)
      , ('show-registers', [], view_registers)
    ] # type: List[Tuple[str, List, Callable[..., None]]]

    return commands

print_lock: Lock = Lock()

def terminal_print(print_string: str):
    global terminal_name
    with print_lock:
        print(f'\r{print_string}')

        try:
            if terminal_name is not None:
                cprint(f'{terminal_name}', end=f'$ ', color='blue')
        except NameError:
            cprint('WARNING: terminal_name undefined', color='red')
            cprint('', end=f'$ ', color='blue')

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

    commands = init_commands(memory, pipeline)

    # with Clock() as c, CommandParser(name=args.n, commands=commands) as command_parser:
    command_parser = CommandParser(name=args.n, commands=commands)
    command_parser.start()