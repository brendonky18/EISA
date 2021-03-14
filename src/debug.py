import argparse
from src import commandparse as cp
from src import memory_devices as md
from src import eisa


if __name__ == '__main__':
    arg_parser = argparse.ArgumentParser()
    
    arg_parser.add_argument('cs', action='store', type=int, help='the size of the cache, in words') # arg to get cache size
    arg_parser.add_argument('rs', action='store', type=int, help='the size of the RAM, in words') # arg to get memory size

    ram = RAM(EISA.RAM_SIZE, None, 1, 1)
    cache = Cache(EISA.CACHE_SIZE, EISA.OFFSET_SIZE, ram, 1, 1)

    cmd_parser = CommandParser('memdbgr')

    @commandparse_cb
    def cache_read(addr: int):
        print(f'reading from address {addr}\n{cache[addr]}')

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

    cmd_parser.add_command('read', [int], cache_read)
    cmd_parser.add_command('write', [int, int], cache_write)
    cmd_parser.add_command('view', [str], view)
    cmd_parser.add_command('show', [str], view) # alias for the view command

    cmd_parser.start()


