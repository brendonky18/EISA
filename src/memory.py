class Memory:
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
    
    def read(self, address):
        pass

    def write(self, address, value):
        pass