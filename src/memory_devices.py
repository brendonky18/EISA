from memory_subsystem import MemoryDevice
from typing import Union
from functools import reduce
class Cache(MemoryDevice):
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

        self.validate_address(address)

        if isinstance(address, int):
            return self._memory[address]
        elif isinstance(address, slice):
            # combines the list of 4 words, into a single integer
            return reduce(lambda accumulator, cur: (accumulator << 32) + cur, self._memory[address], 0) 

        

    

    def __setitem__(self, address: int, value: int):
        self.validate_address(address)
        self._memory[address] = value


