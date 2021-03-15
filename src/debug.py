import argparse
from commandparse import CommandParser, commandparse_cb
from memory_devices import RAM, Cache
from eisa import EISA
from clock import Clock


if __name__ == '__main__':
    arg_parser = argparse.ArgumentParser()
    
    arg_parser.add_argument('-cs', action='store', type=int, help='the size of the cache, in words') # arg to get cache size
    arg_parser.add_argument('-rs', action='store', type=int, help='the size of the RAM, in words') # arg to get memory size
    arg_parser.add_argument('-n', action='store', type=str, help='the size of the RAM, in words') # arg to get memory size

    args = arg_parser.parse_args()

    ram = RAM(EISA.RAM_SIZE, None, 1, 1)
    cache = Cache(EISA.CACHE_SIZE, EISA.OFFSET_SIZE, ram, 1, 1)

    cmd_parser = CommandParser('dbg' if args.n is None else args.n)

    @commandparse_cb
    def cache_read(addr: int):
        print(f'reading from address {addr}\n{addr:#0{4}x}: {cache[addr]}')

    @commandparse_cb
    def cache_write(addr: int, val: int):
        print(f'writing {val} to address {addr}')
        cache[addr] = val

    @commandparse_cb
    def view(device: str):
        if device.lower() == 'ram':
            print(str(ram))
        elif device.lower() == 'cache':
            print(str(cache))
        else:
            print(f'<{device}> is not a valid memory device')

    @commandparse_cb
    def view_way(address: int):
        print(str(cache.get_cacheway(address)))

    @commandparse_cb
    def clock(mode: str):
        if mode.lower() == 'start':
            Clock.start()
            print('Clock started')
        elif mode.lower() == 'stop':
            Clock.stop()
            print('Clock stopped')
        else:
            print(f'<{mode}> is not a valid option, please enter start/stop')

    cmd_parser.add_command('read', [int], cache_read)
    cmd_parser.add_command('write', [int, int], cache_write)
    cmd_parser.add_command('view', [str], view)
    cmd_parser.add_command('show', [str], view) # alias for the view command
    cmd_parser.add_command('view-way', [int], view_way)
    cmd_parser.add_command('show-way', [int], view_way) # alias
    cmd_parser.add_command('clock', [str], clock) # alias

    cmd_parser.start()


