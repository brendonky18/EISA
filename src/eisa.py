from constant import const
class EISA_properties(object):
    @const
    def WORD_SIZE(self): return 32 # the number of bits in each word
    @const
    def ADDRESS_SIZE(self): return 8 # the number bits in the address space
    @const
    def OFFSET_SIZE(self): return 2 # the number of bits for the offset in a cache line
    @const
    def CACHE_SIZE(self): return 4 # the number of addressable bits used by the cache
    @const
    def RAM_SIZE(self): return 8 # the number of addressable bits used by RAM

    # wrappers
    @const
    def ADDRESS_SPACE(self): return 2**self.ADDRESS_SIZE # the number of valid addresses
    @const
    def OFFSET_SPACE(self): return 2**self.OFFSET_SIZE # the number of words per line
    @const
    def CACHE_ADDR_SPACE(self): return 2**self.CACHE_SIZE # the number of cache lines
    @const
    def RAM_ADDR_SPACE(self): return 2**self.RAM_SIZE # the range of valid RAM addresses
    @const
    def WORD_INT_LIM(self): return 2 **self.WORD_SIZE  # the range of valid RAM addresses


EISA = EISA_properties()