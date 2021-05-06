from __future__ import annotations  # must be first import
from concurrent.futures import ThreadPoolExecutor, Future
from memory_devices import *


class PipelineStall(Exception):
    def __init__(self, stage: str, message='The pipeline has stalled'):
        self.stage = stage
        self.message = message

    def __str__(self):
        return f'The pipeline has stalled due to \'{self.stage}\''


class MemorySubsystem:
    _cache: Cache
    _cache2: Cache
    _RAM: RAM

    _is_reading: bool
    _is_writing: bool

    _io_executor: ThreadPoolExecutor

    _future_read: Future
    _future_write: Future

    # Int indicating what memory address is currently being read that is causing a stall
    # -> -1 if not waiting on any address currently
    waiting_on_reading: int
    waiting_on_writing: int
    # Int indicating how many remaining cycles will stall
    stalls_remaining_reading: int
    stalls_remaining_writing: int
    _write_miss: bool

    cache_enabled: bool
    cache_size_original: int
    cache_read_speed: int
    cache_write_speed: int

    cache2_enabled: bool
    cache2_size_original: int
    cache2_read_speed: int
    cache2_write_speed: int

    l2_hit: bool
    l2_hit_writing: bool

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

        self._is_reading = False
        self._is_writing = False

        self._future_read = None  # type: ignore
        self._future_write = None  # type: ignore
        self._io_executor = ThreadPoolExecutor(1, 'memory')

        self.waiting_on_reading = -1
        self.stalls_remaining_reading = 0

        self.waiting_on_writing = -1
        self.stalls_remaining_writing = 0
        self._write_miss = False

        # FIXME - hardcode these to EISA props
        self.cache_enabled = True
        self.cache_size_original = cache_size
        self.cache_read_speed = cache_read_speed
        self.cache_write_speed = cache_write_speed

        # NOTE - Hardcoded to EISA props
        self.cache2_enabled = True
        self.cache2_size_original = EISA.CACHE2_SIZE
        self.cache2_read_speed = EISA.CACHE2_READ_SPEED
        self.cache2_write_speed = EISA.CACHE2_WRITE_SPEED
        self._cache2 = Cache(self.cache2_size_original, 2, self._RAM, self.cache2_read_speed, self.cache2_write_speed, self.cache_evict_cb, level=2)
        self.l1_hit = False
        self.l2_hit = False
        self.l2_hit_writing = False
        self.l1_hit_writing = False

    # read
    def __getitem__(self, address: int) -> int:
        # run this section in a detached thread

        '''
        def get_func():
            if not self._cache.check_hit(address):
                # cache miss

                # get a slice corresponding to the block of words stored in each cache way
                address_block = self._cache.offset_align(address)
                # load the value from RAM into cache
                self._cache.replace(address_block, self._RAM[address_block]) # TODO: make the read from RAM use RAM's read policy rather than reading directly

            return self._cache[address]
        '''

        # TODO - Should reads and writes be concurrent with one another? If not, check for both self._is_reading and
        #   self._is_writing when either getitem or setitem is called

        # TODO - verify that cache hits require 1 extra cycle of read time (and thus send a single stall forward)

        # only start a new read if there isnt one running already
        if not self._is_reading:
            self._is_reading = True

            # self._future_read = self._io_executor.submit(get_func)
            if self.waiting_on_reading == -1:
                if not self._cache.check_hit(address) and not self._cache2.check_hit(address):
                    # cache miss

                    # mark this address as stalled, and set the stalls remaining to the RAM's read speed only if we
                    # aren't waiting on an address currently
                    self.stalls_remaining_reading = self._RAM._read_speed - 1 # NOTE - _read_speed is num of cycles required for a read
                elif self._cache2.check_hit(address):
                    # cache2 hit
                    self.stalls_remaining = self._cache2._read_speed - 1
                    # set l2 hit flag to true
                    self.l2_hit = True
                else:
                    # cache hit

                    # mark this address as stalled, and only stall for a single cycle because of a cache hit only if we
                    # aren't waiting on an address currently
                    self.stalls_remaining_reading = self._cache._read_speed - 1

            # set the address we are waiting on
            self.waiting_on_reading = address

            # raise pipeline stall
            raise PipelineStall('memory read')

        if self._is_reading and self.stalls_remaining_reading > 0:  # TODO - optimize if-elif statement

            # decrement the number of remaining number of stalled cycles
            self.stalls_remaining_reading -= 1
            # return none if the read is still occurring
            raise PipelineStall('memory read')

        elif self._is_reading and self.stalls_remaining_reading == 0:
            # stall has finished

            # TODO - Verify with Brendon that this is the correct way to evict
            # get a slice corresponding to the block of words stored in each cache way
            address_block = self._cache.offset_align(address)
            # load the value from RAM into cache AND cache2
            self._cache2.replace(address_block, self._RAM[address_block])
            self._cache.replace(address_block, self._RAM[
                address_block])  # TODO: make the read from RAM use RAM's read policy rather than reading directly
            # reset reading flag
            self._is_reading = False
            # now there is no address we are waiting on
            self.waiting_on_reading = -1

        # if no PipelineStall error is raised, return the value
        return self._cache[address]

    # write
    def __setitem__(self, address: int, value: int) -> None:
        # only start a new write if there isn't one running already
        if not self._is_writing:
            self._is_writing = True

            # self._future_write = self._io_executor.submit(set_func)
            if self.waiting_on_writing == -1:
                if not self._cache.check_hit(address) and not self._cache2.check_hit(address):
                    # cache miss

                    # mark this address as stalled, and set the stalls remaining to the RAM's read speed
                    self.stalls_remaining_writing = self._RAM._write_speed - 1 # NOTE - _read_speed is num of cycles required for a write
                    self._write_miss = True
                elif self._cache2.check_hit(address):
                    # cache2 hit
                    self.stalls_remaining_writing = self._cache2._write_speed - 1
                    # set l2 hit flag to true
                    self.l2_hit_writing = True
                else:
                    # cache hit

                    # mark this address as stalled, and set the stalls remaining to the RAM's read speed
                    self.stalls_remaining_writing = self._cache._write_speed  # NOTE - _read_speed is num of cycles required for a write

            # set the address we are waiting on
            self.waiting_on_writing = address

            # raise pipeline stall
            raise PipelineStall('memory write')

        if self._is_writing and self.stalls_remaining_writing > 0:

            # decrement the number of remaining number of stalled cycles
            self.stalls_remaining_writing -= 1
            # return none if the read is still occurring
            raise PipelineStall('memory write')

        elif self._is_writing and self.stalls_remaining_writing == 0: # TODO - Optimize if-elif statements

            # set address in RAM to value, and if the write is a hit, write the value to cache as well
            if not self._write_miss:
                if self.l2_hit_writing:
                    self._cache2[address] = value
                    self._cache.replace(self._cache.offset_align(address), value)
                else:
                    self._cache[address] = value
                    self._cache2.replace(self._cache.offset_align(address), value)
            self._RAM[address] = value

            # reset flags
            self._is_writing = False
            self.waiting_on_writing = -1
            self._write_miss = False

    def __enter__(self):
        pass

    def __exit__(self):
        """allows the memory subsystem to be used with 'with' statements,
        and the executor will automatically be shutdown when done
        """
        self._io_executor.shutdown()
