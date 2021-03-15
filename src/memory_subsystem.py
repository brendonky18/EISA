from __future__ import annotations # must be first import, allows type hinting of next_device to be the enclosing class
from abc import ABC, abstractmethod # Abstract Base Class
from typing import Union, Optional, Callable, Any
from eisa import EISA
from constant import const


class MemoryDevice(ABC):
    """Interface for all components of the memory subsystem
    """

    _addr_size: int
    _addr_space: int
    _memory: list[int]
    _read_speed: int
    _write_speed: int
    _next_device: Union[MemoryDevice, None]

    def __init__(self, addr_size: int, next_device: Union[MemoryDevice, None], read_speed: int, write_speed: int): #TODO check if we need to specify read and write speeds seperately
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
        self._addr_size = addr_size
        self._addr_space = 2**self._addr_size
        self._memory = [0b0 * EISA.WORD_SIZE] * self._addr_space # 1 word * the number of words
        self._read_speed = read_speed
        self._write_speed = write_speed
        self._next_device = next_device

    def __str__(self) -> str:
        """to string method
        """
        # Print starting line
        s = f'+{"".center(10, "-")}+\n'

        # Print each entry line + block line
        for i in self._memory:
            s += f'|{str(int(i)).center(10)}|\n+{"".center(10, "-")}+\n'

        return s

    @abstractmethod
    def __getitem__(self, address: int) -> int:
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
    def __setitem__(self, address: int, value: int) -> int:
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

