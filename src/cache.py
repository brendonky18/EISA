class Cache:
    def __init__(self, size):
        self.size = size
        self.entries = [0b0] * size

    # TODO
    def __str__(self):
        # Print starting line
        print('+', "".center(10, '-'), '+')

        # Print each entry line + block line
        for i in self.entries:
            print('+', str(int(i)).center(10), '+')
            print('+', "".center(10, '-'), '+')

        # Print ending line
        print('+', "".center(10, '-'), '+')

    # Is this reading the cache value or the memory value?
    def read(self, address):
        pass

    # Is this writing to the cache or to the memory?
    def write(self, address, value):

        #Assuming writing to memory

        #How are we referencing the memory system?
        #   We should pass a reference to the memory system
        #   when calling the constructor and storing that reference
        #   in the cache object. That way when we need to write to
        #   memory, we don't have to pass a reference to the
        #   memory system we want to write to.


        pass
