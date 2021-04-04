from __future__ import annotations # must be first import
from tabulate import tabulate  # pip install tabulate
from memory_devices import *
from typing import Union, Callable, Any, List   
from functools import reduce
from eisa import EISA
from clock import Clock
from threading import Thread

class PipelineStall(Exception):
    def __init__(self, stage: str, message='The pipeline has stalled'):
        self.stage = stage
        self.message = message

    def __str__(self):
        return f'The pipeline has stalled due to \'{self.stage}\''


class MemorySubsystem:
    _cache: Cache
    _RAM: RAM

    def cache_evict_cb(self):
        return None

    def __init__(
        self, 
        address_size: int, 
        cache_size: int, cache_read_speed: int, cache_write_speed: int,  
        ram_size: int, ram_read_speed: int, ram_write_speed: int
    ):
        self._RAM = RAM(ram_size, None, ram_read_speed, ram_write_speed)
        self._cache = Cache(cache_size, 2, self._RAM, cache_read_speed, cache_write_speed, self.cache_evict_cb)

    # read
    def __getitem__(self, address: int) -> int: # TODO write docstring
        val = 0

        # run this section in a detached thread
        def get_func():
            if not self._cache.check_hit(address):
                # cache miss

                # get a slice corresponding to the block of words stored in each cache way
                address_block = self._cache.offset_align(address)
                # load the value from RAM into cache
                self._cache.replace(address_block, self._RAM[address_block]) # TODO: make the read from RAM use RAM's read policy rather than reading directly
            
            val = self._cache[address]
        
        get_thread = Thread(target=get_func, name='memory get thread')
        get_thread.start()

        if get_thread.is_alive():
            # return none if the read is still occuring
            raise PipelineStall('memory read')
        else:
            # join the thread and return the value
            get_thread.join()
            return val

    # write
    def __setitem__(self, address: int, value: int) -> None: # TODO write docstring
        def set_func():
            if self._cache.check_hit(address):
                # cache hit
                self._cache[address] = value
                self._RAM[address] = value
            else:
                # cache miss
                self._RAM[address] = value

        set_thread = Thread(target=set_func, name='memory write')
        set_thread.start()

        if set_thread.is_alive():
            raise PipelineStall('memory write')
        else:
            set_thread.join()

        
            
