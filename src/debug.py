import argparse
from commandparse import CommandParser, commandparse_cb
from memory_subsystem import MemorySubsystem
from eisa import EISA
from clock import Clock
from threading import Lock

print_lock: Lock = Lock()




if __name__ == '__main__':
    arg_parser = argparse.ArgumentParser()
    
    arg_parser.add_argument('-cs', action='store', type=int, help='the size of the cache, in words') # arg to get cache size
    arg_parser.add_argument('-rs', action='store', type=int, help='the size of the RAM, in words') # arg to get memory size
    arg_parser.add_argument('-n', action='store', type=str, help='the size of the RAM, in words') # arg to get memory size

    args = arg_parser.parse_args()

    memory = MemorySubsystem(EISA.ADDRESS_SIZE, args.cs, 1, 1, args.rs, 2, 2)

    cmd_parser = CommandParser('dbg' if args.n is None else args.n)
    terminal_name = args.n

    def terminal_print(print_string:str):
        with print_lock:
            print(f'\r{print_string}')
            print(terminal_name, end='$ ', flush=True)

    @commandparse_cb
    def cache_read(addr: int):
        terminal_print(f'Reading from address {addr}\n{addr:#0{4}x}: {memory[addr]}')

    @commandparse_cb
    def cache_write(addr: int, val: int):
        terminal_print(f'writing {val} to address {addr}')
        memory[addr] = val

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
        print(str(memory._cache.get_cacheway(address)))

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

    cmd_parser.add_command('read', [int], cache_read)
    cmd_parser.add_command('write', [int, int], cache_write)
    cmd_parser.add_command('view', [str, int, int], view)
    cmd_parser.add_command('show', [str, int, int], view) # alias for the view command
    cmd_parser.add_command('view-way', [int], view_way)
    cmd_parser.add_command('show-way', [int], view_way) # alias
    cmd_parser.add_command('clock', [str], clock)
    cmd_parser.add_command('step', [int], step_clock)

    cmd_parser.start()
