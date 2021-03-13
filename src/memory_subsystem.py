from abc import ABC, abstractmethod # Abstract Base Class

class MemoryDevice(ABC):
    """Interface for all components of the memory subsystem
    """
    
    _size: int
    _memory: list[int]
    _read_speed: int
    _write_speed: int

    def __init__(self, size: int, read_speed: int, write_speed: int): #TODO check if we need to specify read and write speeds seperately
        """Constructor for a memory device

        Parameters
        ----------
        size : int
            the number of addressable words that the device can store
        read_speed : int
            the number of cycles required to perform a read operation
        write_speed : int
            the number of cycles required to perform a write operation
        """
        self._size = size
        self._memory = [0b00000000000000000000000000000000] * size # 1 word * the number of words
        self._read_speed = read_speed
        self._write_speed = write_speed

    def __str__(self):
        """to string method
        """

        # Print starting line
        print('+', "".center(10, '-'), '+')

        # Print each entry line + block line
        for i in self._memory:
            print('+', str(int(i)).center(10), '+')
            print('+', "".center(10, '-'), '+')

        # Print ending line
        print('+', "".center(10, '-'), '+')

    def validate_address(self, address: int):
        """helper function which checks that an address is an integer, and not out of bounds

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
        """
        if type(address) is not int:
            raise TypeError
        if address > self._size:
            raise IndexError
    
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
    def __setitem__(self, address: int, value: int): 
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


class AddressError(LookupError):
    """Raised when an invalid address is accessed
    """
    pass