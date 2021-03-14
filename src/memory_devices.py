from src import memory_subsystem as ms
from typing import Union
from functools import reduce
from src import eisa

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
    
    # the raw bits corresponding to the cache way
    _entry: int = 0b0

    _tag_bits: int
    _index_bits: int
    _offset_bits: int
    _data_bits: int

    _valid_start: int
    _dirty_start: int
    _tag_start: int
    _index_start: int
    _data_start: int = 0

    def __init__(self, tag_bits: int, index_bits: int, offset_bits: int):
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

        self._tag_bits = tag_bits
        self._index_bits = index_bits
        self._offset_bits = offset_bits
        
        # the total number of bits needed to store all of the words in each way
        self._data_bits = eisa.WORD_SIZE * offset_bits

        # calculates the indicies of where each section starts within entry
        self._index_start = self._data_start + self._data_bits
        # no offset start, becase we don't store the offsets in each line
        self._tag_start = self._index_start + self._index_bits
        self._dirty_start = self._tag_start + self._tag_bits
        self._valid_start = self._dirty_start + 1

        self.valid = ms.bitfield_property_constructor(self._valid_start, 1)
        self.dirty = ms.bitfield_property_constructor(self._dirty_start, 1)
        self.tag = ms.bitfield_property_constructor(self._tag_start, self._tag_bits)
        self.index = ms.protected_bitfield_property_constructor(self._index_start, self._index_bits)

    def __getitem__(self, offset: int) -> int:
        """read a word from the line

        Parameters
        ----------
        offset : int
            the offset of the word

        Returns
        -------
        int
            the data stored at the specified offset
        """

        # ensures that the offset is correct
        if offset > 2**self._offset_bits:
            raise IndexError(f'offset can be at most {2**self._offset_bits}')

        return (self._entry >> (offset * eisa.WORD_SIZE)) & (2**eisa.WORD_SIZE - 1)

    # TODO: finish function to add items to cache line, should only be able to write all 4 words,
    # should not be able to write words individually
    def __setitem__(self, offset: int, value: int):
        """write a word to the line

        Parameters
        offset
        address : int
            the offset of the word 
        value : int
            the value to write
        """
        pass

# TODO: extra credit, use to implement associative caches instead of direct-mapped
class CacheBlock():
    pass

class Cache(ms.MemoryDevice):
    """CPU cache
    write-through
    direct-mapped
    no allocate
    4 words per line
    """

    _offset_bits: int = 2 # 2 bits -> 4 words per line

    def __init__(self, addr_space: int, offset_bits: int, next_device: ms.MemoryDevice, read_speed: int, write_speed: int):
        """Constructor for a cache

        Parameters
        ----------
        addr_space : int
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
        super().__init__(addr_space, next_device, read_speed, write_speed)
        self._offset_bits = offset_bits

    #TODO implement data structure for cache
    def __getitem__(self, address: int):
        pass
    
    def __setitem__(self, address: int, value: int) -> int:
        pass

class RAM(ms.MemoryDevice):
    def __getitem__(self, address: Union[int, slice]) -> int:
        """retreives the data from the specified address or range of addresses

        Parameters
        ----------
        address : int or slice
            the address or range of addresses 

        Returns
        -------
        int
            single combined integer representind all of the data found at the passed address(es)
        """

        ms.validate_address(address)

        if isinstance(address, int):
            return self._memory[address]
        elif isinstance(address, slice):
            # combines the list of 4 words, into a single integer
            return reduce(lambda accumulator, cur: (accumulator << eisa.WORD_SIZE) + cur, self._memory[address], 0)

    def __setitem__(self, address: int, value: int):
        ms.validate_address(address)
        self._memory[address] = value


