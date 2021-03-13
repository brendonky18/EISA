from memory_subsystem import MemoryDevice

class Cache(MemoryDevice):
    def __getitem__(self, address: int):
        pass

    
    def __setitem__(self, address: int, value: int) -> int:
        pass

class RAM(MemoryDevice):
    def __getitem__(self, address: int) -> int:
        self.validate_address(address)
        return self._memory[address]


    # Is this writing to the cache or to the memory?
    def __setitem__(self, address: int, value: int):
        self.validate_address(address)
        self._memory[address] = value


