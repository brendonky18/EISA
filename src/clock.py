class Clock:
    cycle_count = 0

    def __init__(self, execute):
        self.execute = execute # callback function for all operations that need to be performed 

    def cycle():
        while run:
            execute()
            cycle_count += 1
