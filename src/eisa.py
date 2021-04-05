from constant import const


class EISA_properties(object):
    """
     _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _
    | 7 | 6 | 5 | 4 | 3 | 2 | 1 | 0 |
    |  Tag  |      Index    |Offset |
    | _ _ _ | _ _ _ _ _ _ _ | _ _ _ |

    First 0,1 bits are offset
    Bits 2,3,4,5 are for index
    Bits 6,7 are tag
    Bits > 7 -> ignore
    """

    @const
    def WORD_SIZE(self) -> int: return 32  # the number of bits in each word

    @const
    def ADDRESS_SIZE(self) -> int: return 8  # the number bits in the address space

    @const
    def OFFSET_SIZE(self) -> int: return 2  # the number of bits for the offset in a cache line

    @const
    def CACHE_SIZE(self) -> int: return 4  # the number of addressable bits used by the cache

    @const
    def RAM_SIZE(self) -> int: return 8  # the number of addressable bits used by RAM

    @const
    def NUM_GP_REGS(self) -> int: return 32 # number of 32-bit general purpose registers

    @const
    def GP_REGS_BITS(self) -> int: return 0b11111 # bits to mask register address

    @const
    def GP_NUM_FIELD_BITS(self) -> int: return 5 # number of bits to shift to each field in instructions

    @const
    def NUM_SCOREBOARD_ROWS(self) -> int: return 4 # number of rows present in pipeline scoreboard

    @const
    def NUM_INSTR_Q_ROWS(self) -> int: return 8 # max size of instruction queue in scoreboard

# wrappers
    @const
    def ADDRESS_SPACE(self) -> int: return 2 ** self.ADDRESS_SIZE  # the number of valid addresses
    @const
    def ADDRESS_MASK(self) -> int: return (2 ** self.ADDRESS_SIZE) - 1

    @const
    def OFFSET_SPACE(self) -> int: return 2 ** self.OFFSET_SIZE  # the number of words per line

    @const
    def CACHE_ADDR_SPACE(self) -> int: return 2 ** self.CACHE_SIZE  # the number of cache lines

    @const
    def RAM_ADDR_SPACE(self) -> int: return 2 ** self.RAM_SIZE  # the range of valid RAM addresses

    @const
    def WORD_SPACE(self) -> int: return 2 ** self.WORD_SIZE  # the range of valid word values
    @const
    def WORD_MASK(self) -> int: return (2 ** self.WORD_SIZE) - 1

EISA = EISA_properties()