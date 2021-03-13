from constant import const

@const
def WORD_SIZE(): return 32 # the number of bits in each word

@const
def ADDRESS_SIZE(): return 8 # the number bits in the address space

@const
def OFFSET_SIZE(): return 2 # the number of bits for the offset in a cache line

@const
def CACHE_SIZE(): return 4 # the number of addressable bits used by the cache

@const
def RAM_SIZE(): return 8 # the number of addressable bits used by RAM

# wrappers
@const
def ADDRESS_SPACE(): return 2**ADDRESS_SIZE # the number of valid addresses

@const
def OFFSET_SPACE(): return 2**OFFSET_SIZE # the number of words per line

@const
def CACHE_ADDR_SPACE(): return 2**CACHE_SIZE # the number of cache lines

@const
def RAM_ADDR_SPACE(): return 2**RAM_SIZE # the range of valid RAM addresses