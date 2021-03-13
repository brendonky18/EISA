import unittest
from src import memory_devices

class CacheTest(unittest.TestCase):

    #test constructor
    def test_cache__init__(self):

        #Arbitrary instantiation
        test_cache = memory_devices.Cache(32,0,None,1,1)

        #Too large instantiation
        test_cache = memory_devices.Cache(256, 0, None, 1, 1)

        #Too small instantiation
        test_cache = memory_devices.Cache(0, 0, None, 1, 1)
        test_cache = memory_devices.Cache(-1, 0, None, 1, 1)

        #Wrong arguement types
        test_cache = memory_devices.Cache(32.12, 0, None, 1, 1)

    def test_cache__getitem__(self):
        self.assertEqual(True, False)

    def test_cache__setitem__(self):
        self.assertEqual(True, False)

if __name__ == '__main__':
    unittest.main()
