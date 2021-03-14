from src import constant as c

@c.const
def WORD_SIZE(self): return 32 # the number of bits in each word
@c.const
def ADDRESS_SIZE(self): return 8 # the number bits in the address space
@c.const
def OFFSET_SIZE(self): return 2 # the number of bits for the offset in a cache line
@c.const
def CACHE_SIZE(self): return 4 # the number of addressable bits used by the cache
@c.const
def RAM_SIZE(self): return 8 # the number of addressable bits used by RAM

# wrappers
@c.const
def ADDRESS_SPACE(self): return 2 **self.ADDRESS_SIZE  # the number of valid addresses
@c.const
def OFFSET_SPACE(self): return 2**self.OFFSET_SIZE # the number of words per line
@c.const
def CACHE_ADDR_SPACE(self): return 2**self.CACHE_SIZE # the number of cache lines
@c.const
def RAM_ADDR_SPACE(self): return 2**self.RAM_SIZE # the range of valid RAM addresses

#EISA = EISA_properties()