from tabulate import tabulate # pip install tabulate
from memory_subsystem import *
from typing import Union
from functools import reduce
from eisa import EISA

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
        self._data_bits = EISA.WORD_SIZE * offset_bits

        # calculates the indicies of where each section starts within entry
        self._index_start = self._data_start + self._data_bits
        # no offset start, becase we don't store the offsets in each line
        self._tag_start = self._index_start + self._index_bits
        self._dirty_start = self._tag_start + self._tag_bits
        self._valid_start = self._dirty_start + 1

        # creates the accessor functions
        self.valid = bitfield_property_constructor(self._valid_start, 1)
        self.dirty = bitfield_property_constructor(self._dirty_start, 1)
        self.tag = bitfield_property_constructor(self._tag_start, self._tag_bits)
        self.index = protected_bitfield_property_constructor(self._index_start, self._index_bits)
        self.data = protected_bitfield_property_constructor(0, self._data_bits)

        # initializes values
        self.valid(False)
        self.dirty(False)
        self.tag(0)
        self.index(0)
        self.data(0)

    def __str__(self) -> str:
        """to string method
        """
        # Print starting line
        s = tabulate([['Valid', self.valid()], ['Dirty', self.dirty()], ['Tag', self.tag()], ['Index', self.index()], ['Data', self.data()]])

        return s
    
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

        return (self._entry >> (offset * EISA.WORD_SIZE)) & (2**EISA.WORD_SIZE - 1)

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
    
    def bitfield_property_constructor(self, start, size) -> Callable[[Any], Any]: # this becomes the decorator
        print('constructor')
        
        def bitfield_property(self, value: Optional[int]=None) -> Any: 
            # get
            if value is None:
                print('get')
                return int(self._entry >> self._valid_start)
            # set
            else:
                print("set")
                self._entry &= ~(((2**size) - 1) << self._valid_start) # clears the original value
                self._entry |= value << start # assigns the value

        return bitfield_property

    def protected_bitfield_property_constructor(self, start: int, size: int):
        def bit_field_set(self, value):
            raise TypeError('cannot assign values to a protected bitfield')

        def bit_field_get(self):
            return bool(self._entry >> self._valid_start)

        return property(bit_field_get, bit_field_set)
# TODO: extra credit, use to implement associative caches instead of direct-mapped
class CacheBlock():
    pass

class Cache(MemoryDevice):
    """CPU cache
    write-through
    direct-mapped
    no allocate
    4 words per line
    """

    _offset_bits: int = 2 # 2 bits -> 4 words per line
    _cache: list[CacheWay]

    def __init__(self, addr_size: int, offset_bits: int, next_device: MemoryDevice, read_speed: int, write_speed: int):
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
        super().__init__(addr_size, next_device, read_speed, write_speed)
        self._offset_bits = offset_bits
        self._cache = [CacheWay(EISA.ADDRESS_SIZE - self._addr_size, self._addr_size, offset_bits)] * EISA.CACHE_ADDR_SPACE
           
    #TODO implement data structure for cache
    def __getitem__(self, address: int):
        pass
    
    def __setitem__(self, address: int, value: int) -> int:
        pass



class RAM(MemoryDevice):
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

        validate_address(address)

        if isinstance(address, int):
            return self._memory[address]
        elif isinstance(address, slice):
            # combines the list of 4 words, into a single integer
            return reduce(lambda accumulator, cur: (accumulator << EISA.WORD_SIZE) + cur, self._memory[address], 0) 

    def __setitem__(self, address: int, value: int):
        validate_address(address)
        self._memory[address] = value


