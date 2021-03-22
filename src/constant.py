def const(f):
    """helper class that allows for the declaration of constants
    """
    def fset(self, value):
        raise TypeError('cannot assign values to a constant')
    def fget(self):
        return f(self)
    return property(fget, fset)
