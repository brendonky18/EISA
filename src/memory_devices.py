from __future__ import annotations  # must be first import, allows type hinting of next_device to be the enclosing class

from abc import ABC, abstractmethod  # Abstract Base Class
from functools import reduce
from typing import Union, Optional, Callable, Any

from tabulate import tabulate  # pip install tabulate

from clock import Clock
from eisa import EISA
from math import ceil


class MemoryMissError(ValueError):
    # raised on a cache miss
    pass

class Policy():
    def __init__(
        self, 
        device: MemoryDevice, 
        read_hit_policy: Callable[[Union[int, slice]], int], read_miss_policy: Callable[[Union[int, slice]], int],
        write_hit_policy: Callable[[Union[int, slice], int], None], write_miss_policy: Callable[[Union[int, slice], int], None]
    ):
        """[summary]

        Parameters
        ----------
        device : MemoryDevice
            the device which the policy applies to
        read_policy: Callable
            defines the device's read policy regarding what happens on a read hit or a read miss
        write_policy: Callable
            defines the device's write policy regarging what happens on a write hit or a write miss
        """

        self._device = device
        self._read_hit_policy = read_hit_policy
        self._read_miss_policy = read_miss_policy
        self._write_hit_policy = write_hit_policy
        self._write_miss_policy = write_miss_policy

    # read policy
    def __getitem__(self, address: Union[int, slice]) -> int:
        try:
            val = self._device[address]
        except MemoryMissError:
            # read miss
            returned_val = self._read_miss_policy(address)
            val = returned_val if returned_val is not None else val
        else:
            # read hit
            returned_val = self._read_hit_policy(address)
            val = returned_val if returned_val is not None else val
        finally:
            return val


    # write policy
    def __setitem__(self, address: int, value: int) -> None:
        try:
            self._device[address] = value
        except MemoryMissError:
            self._write_miss_policy(address, value)
        else:
            self._write_hit_policy(address, value)

class MemoryDevice(ABC):
    """Interface for all components of the memory subsystem
    """

    _local_addr_size: int
    _local_addr_space: int
    _memory: list[int]
    _read_speed: int
    _write_speed: int
    _next_device: Union[MemoryDevice, None]
    _clock: Clock = Clock()
    _policies: Policy

    def __init__(self, local_addr_size: int, next_device: Union[MemoryDevice, None], read_speed: int, write_speed: int): #TODO check if we need to specify read and write speeds seperately
        """Constructor for a memory device

        Parameters
        ----------
        addr_space : int
            the number of bits in the device's address space
            eg. 3 bits of address space -> 8 addressable words
        next_device : Memory Device
            the next memory device in the memory subsystem hierarchy
            None if there is not another
        read_speed : int
            the number of cycles required to perform a read operation
        write_speed : int
            the number of cycles required to perform a write operation
        """
        self._local_addr_size = local_addr_size
        self._local_addr_space = 2**local_addr_size
        self._memory = [0b0 * EISA.WORD_SIZE] * self._local_addr_space # 1 word * the number of words
        self._read_speed = read_speed
        self._write_speed = write_speed
        self._next_device = next_device

    def __str__(self, start: int=0, size: int=0) -> str:
        """to string method
        """
        if size == 0:
            size = self._local_addr_space

        stop = min(self._local_addr_space, start + size)

        s = tabulate(
            zip(range(start, stop), self._memory[start : stop]),
            headers=['Address', 'Value'],
            tablefmt='pretty',
            stralign='left',
            numalign='right'
        )
        return s

    @abstractmethod
    def __getitem__(self, address: Union[int, slice]) -> int:
        """Reads the specified address from the memory and returns the stored value

        Parameters
        ----------
        address : int
            the location to read from, formatted as 32 bits

        Returns
        -------
        int
            the word stored at the specified address

        Raises
        ------
        NotImplementedError
            if this method is not implemented by a class inheriting this interface
        """
        raise NotImplementedError

    @abstractmethod
    def __setitem__(self, address: int, value: int) -> None:
        """Writes the passed value to the specified address

        Parameters
        ----------
        address : int
            the location to write to, formatted as 32 bits
        value : int
            the value to write to memory, formatted as 32 bits

        Raises
        ------
        NotImplementedError
            if this method if not implemented by a class inheriting this interface
        """
        raise NotImplementedError

    def set_policies(
        self,
        read_hit_policy: Callable[[Union[int, slice]], int], read_miss_policy: Callable[[Union[int, slice]], int],
        write_hit_policy: Callable[[Union[int, slice], int], None], write_miss_policy: Callable[[Union[int, slice], int], None]
    ):
        self._policies = Policy(self, read_hit_policy, read_miss_policy, write_hit_policy, write_miss_policy)

# TODO: extra credit, use to implement associative caches instead of direct-mapped
class CacheBlock:
    pass

class CacheWay:
    """
    address structure
        offset bits
        index bits
        tag bits
    cache line structure
        data bits
        index bits
        tag bits
        dirty bit
        valid bit
    """

    # <instance variables> 
    _valid: int
    _dirty: int
    _tag: int
    _index: int
    _data: list[int] = [0, 0, 0, 0]
    _clock: Clock = Clock()
    # </instance variables>

    def __init__(self, index_bits: int, offset_bits: int):
        """constructor for a cache way

        Parameters
        ----------
        tag_bits : int
            the number of bits in the tag field
        index_bits : int
            the number of bits in the index field
        offset_bits : int
            the number of bits in the offset field
        """

        self._tag_bits = EISA.ADDRESS_SIZE - index_bits - offset_bits
        if self._tag_bits < 0:  # ensure that the tag field is at least 0
            raise TypeError('index bits and offset bits are larger than the address size')
        self._index_bits = index_bits
        self._offset_bits = offset_bits

        # the total number of bits needed to store all of the words in each way
        self._data_bits = EISA.WORD_SIZE * offset_bits

        # creates the accessor functions, and initialize values
        self._valid = False
        self._dirty = False
        self._tag = 0
        self._index = 0
        self._data = [0, 0, 0, 0]
    
    def __str__(self) -> str:
        """to string method
        """
        # Print starting line
        s = tabulate(
            [
                ['Valid', f'{self.valid():#0{2 + 1}x}'],
                ['Dirty', f'{self.dirty():#0{2 + 1}x}'],
                ['Tag', f'{self.tag():#0{2 + ceil(self._tag_bits / 4)}x}'],
                ['Index', f'{self.index():#0{2 + ceil(self._index_bits / 4)}x}'],
                ['Data', f'{self.data():#0{2 + ceil(self._data_bits / 4)}x}']
            ],
            headers=['Field', 'Value'],
            tablefmt='pretty',
            stralign='left',
            numalign='right'
        )

        return s

    # read
    def __getitem__(self, address: int) -> int:
        # get the offset
        offset = address & (2**self._offset_bits - 1)
        # get the index
        address >>= self._offset_bits
        index = address & (2**self._index_bits - 1)
        # get the tag
        address >>= self._index_bits
        tag = address & (2**self._tag_bits - 1)
        
        if index != self.index():
            raise ValueError('Indicies no not match')

        if tag != self.tag() or not self.valid():
            raise MemoryMissError('Read miss')

        self._clock.wait(1, wait_event_name='Cache read')
        return self._data[offset]

    # write
    def __setitem__(self, address: int, value: int):
        # get the offset
        offset = address & (2**self._offset_bits - 1)
        # get the index
        address >>= self._offset_bits
        index = address & (2**self._index_bits - 1)
        # get the tag
        address >>= self._index_bits
        tag = address & (2**self._tag_bits - 1)
        
        if index != self.index():
            raise ValueError('Vaues for index do not match')

        if tag != self.tag():
            raise MemoryMissError('Write miss')
        
        self._clock.wait(1, wait_event_name='Cache write')
        self._data[offset] = value
        self.valid(True)

    def check_hit(self, address: int) -> bool:
        """checks if an address is loaded in the cache

        Parameters
        ----------
        address : int
            the address to check

        Returns
        -------
        bool
            true if there is a cache hit
            false if there is a cache miss
        """
        # get the tag
        address >>= (self._index_bits + self._offset_bits)
        tag = address & (2**self._tag_bits - 1)

        return (tag == self.tag()) and bool(self.valid())
        
    # replace/evict
    def replace(self, address_block: slice, data: int):
        """performs a cache eviction by replacing the data in a cache way

        Parameters
        ----------
        address_block : slice
            the new block of words
        data : int
            the new value

        Raises
        ------
        ValueError
            if the index of the cache way being replaced, does not match the index of the incoming address block
        """
        address = address_block.start
    
        # get the index
        address >>= self._offset_bits
        index = address & (2**self._index_bits - 1)
        # get the tag
        address >>= self._index_bits
        tag = address & (2**self._tag_bits - 1)
    
        if index != self.index():
            raise ValueError('Indicies no not match')

        # update the tag
        self.tag(tag)
        # update the data
        self.data(data)

    def valid(self, value: Optional[int]=None) -> Union[int, CacheWay]:
        """accessor function for the valid bit

        Parameters
        ----------
        value : int
            perform a set, the value to assign the valid bit, by default None
        value: None
            perform a get

        Returns
        -------
        int
            the value stored in the valid bit if the access is a `get` operation
        CacheWay
            the CacheWay if the access is a `set` operation
        """
        if value is None:
            return self._valid
        else:
            self._valid = value
            return self

    def dirty(self, value: Optional[int]=None):
        """accessor function for the dirty bit

        Parameters
        ----------
        value : int
            perform a set, the value to assign the dirty bit, by default None
        value: None
            perform a get

        Returns
        -------
        int
            the value stored in the dirty bit if the access is a `get` operation
        CacheWay
            the CacheWay if the access is a `set` operation
        """
        if value is None:
            return self._dirty
        else:
            self._dirty = value
            return self
    
    def tag(self, value: Optional[int]=None):
        """accessor function for the tag field

        Parameters
        ----------
        value : int
            perform a set, the value to assign the tag field
        value: None
            perform a get

        Returns
        -------
        int
            the value stored in the tag field if the access is a `get` operation
        CacheWay
            the CacheWay if the access is a `set` operation
        """
        if value is None:
            return self._tag
        else:
            self._tag = value
            return self
    
    def index(self, value: Optional[int]=None):
        """accessor function for the index field

        Parameters
        ----------
        value : int
            perform a set, the value to assign the index field
        value: None
            perform a get

        Returns
        -------
        int
            the value stored in the index field if the access is a `get` operation
        """
        CacheWay
            
        if value is None:
            return self._index
        else:
            self._index = value
            return self
    
    # TODO implement this function inside __setitem__ and __getitem__
    # it will check for replacement vs assignment by using slices for replacement, and ints for assignment
    def data(self, value: Optional[int]=None):
        """accessor function for the index field

        Parameters
        ----------
        value : int
            perform a set, the value to assign the data field
        value: None
            perform a get

        Returns
        -------
        int
            the value stored in the data field if the access is a `get` operation
        """
        if value is None: # get
            return self._data
        else: # set
            # unpacks the passed integer into a list
            for i in range(2**self._offset_bits):
                self._data[i] = value & (EISA.WORD_SPACE - 1)
                value >>= EISA.WORD_SIZE
            self.valid(True)

            return self

class Cache(MemoryDevice):
    """CPU cache
    write-through
    direct-mapped
    no allocate
    4 words per line
    """

    _offset_size: int = 2  # 2 bits -> 4 words per line
    _offset_space: int = 4 # 2 bits -> 4 words per line
    _cache: list[CacheWay]
    _next_device: MemoryDevice
    _on_evict: Callable[[MemoryDevice], Any]

    def __init__(
        self, 
        local_addr_size: int, 
        offset_size: int, 
        next_device: MemoryDevice, 
        read_speed: int, 
        write_speed: int, 
        evict_cb: Optional[Callable[[], Any]]=None
    ):
        """Constructor for a cache

        Parameters
        ----------
        addr_size : int
            the number of bits in the device's address space
            eg. 3 bits of address space -> 8 addressable lines
        offset_bits:
            the number of bits in each line's 'offset' field
            eg. 2 bits -> 4 words per line
        next_device : Memory Device
            the next memory device in the memory subsystem hierarchy
        read_speed : int
            the number of cycles required to perform a read operation
        write_speed : int
            the number of cycles required to perform a write operation
        """
        super().__init__(local_addr_size, next_device, read_speed, write_speed)
        self._offset_size = offset_size
        self._offset_space = 2**offset_size
        self._cache = [CacheWay(self._local_addr_size, offset_size).index(i) for i in range(EISA.CACHE_ADDR_SPACE)]

        if evict_cb is not None:
            self._on_evict = evict_cb # type: ignore
            # mypy does not like assigning to functions but I think it should be ok

    def __str__(self, start: int=0, size: int=0) -> str:
        """to string method
        """

        if size == 0:
            size = self._local_addr_space

        stop = min(self._local_addr_space, start + size)


        s = tabulate(
            zip(range(start, stop), [cur.data() for cur in self._cache[start : stop]]),
            headers=['Address', 'Value'],
            tablefmt='pretty',
            stralign='left',
            numalign='right'
        )
        return s

        # Print starting line
        s = f'+{"".center(10, "-")}+\n'

        # Print each entry line + block line
        for i in self._cache:
            s += f'|{str(i.data())[1:-1].center(10)}|\n+{"".center(10, "-")}+\n'

        return s

    # read
    def __getitem__(self, address: int) -> int: # type: ignore
        return self.get_cacheway(address)[address]

    # write
    def __setitem__(self, address: int, value: int) -> None:
        self.get_cacheway(address)[address] = value

    # replace/evict
    def replace(self, address_block: slice, data: int) -> None:
        address = address_block.start

        self._on_evict()

        self.get_cacheway(address).replace(address_block, data)

    def check_hit(self, address: int) -> bool:
        return self.get_cacheway(address).check_hit(address)

    def get_cacheway(self, address: int) -> CacheWay:
        """function to expose individual cache ways so that they can be viewed

        Parameters
        ----------
        address : int
            the address of the associated cacheway
            ignores all but the index bits in the specified address
        """

        return self._cache[(address >> self._offset_size) & (self._local_addr_space - 1)] 

    def offset_align(self, address: int) -> slice:
        """helper function that takes in an address and gives an offset-aligned slice 
        

        Parameters
        ----------
        address : int
            the address to align

        Returns
        -------
        int
            a slice of addresses aligned to the cache's offset
        """
        return slice(address & ~(self._offset_space - 1), (address | (self._offset_space - 1)) + 1)

class RAM(MemoryDevice):
    def __getitem__(self, address: Union[int, slice]) -> int:
        """Reads the specified address/range of addresses from the memory and returns the stored value

        Parameters
        ----------
        address : int or slice
            the address or range of addresses, formatted as a 32 bit integer

        Returns
        -------
        int
            single combined integer representind all of the data found at the passed address(es)
        """
        validate_address(address)

        self._clock.wait(self._read_speed, wait_event_name='RAM read')

        if isinstance(address, int):
            return self._memory[address]
        elif isinstance(address, slice):
            # combines the list of words, into a single integer
            memory_block = self._memory[address][::-1]
            return_val = reduce(lambda accumulator, cur: (accumulator << EISA.WORD_SIZE) | cur, memory_block, 0)
            return return_val

    def __setitem__(self, address: int, value: int) -> None:
        """writes the passed value to the specified address

        Parameters
        ----------
        address : int
            the location to write to, formatted as a 32 bit integer
        value : int
            the value to write to memory, formatted as a 32 bit integer
        """
        validate_address(address)

        self._clock.wait(self._write_speed, wait_event_name='RAM write')

        self._memory[address] = value

def validate_address(address: Union[int, slice]):
        """helper function which checks that an address is an integer, and is within the bounds of the memory subsystem's address space

        Parameters
        ----------
        address : int
            the address to be validated

        Raises
        ------
        TypeError
            if the address is not an integer
        IndexError
            if the address is out of bounds
        ValueError
            if a block of addresses are not sequential
        """
        if isinstance(address, int):
            if address > EISA.ADDRESS_SPACE:
                raise IndexError
            else:
                return True
        elif isinstance(address, slice):
            if address.start > EISA.ADDRESS_SPACE or address.stop > EISA.ADDRESS_SPACE:
                raise IndexError
            elif address.step != 1 and address.step != None:
                raise ValueError('address slices only support steps of 1')
            else:
                return True
        else:
            raise TypeError('address is outside of the address space')

def check_address(address: Union[int, slice], address_space: int):
        """helper function which checks that an address is an integer, and that the address is within the specified address space

        Parameters
        ----------
        address : int
            the address to be validated
        address_space : int
            the number of bits in the address space to be checked

        Returns
        ------
        bool
            True if the address is within the device's address space, False otherwise
        """
        if isinstance(address, int):
            return address <= 2 ** address_space
        else:
            return address.start <= 2 ** address_space and address.stop <= 2 ** address_space

