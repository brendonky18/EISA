from __future__ import annotations # must be first import, allows type hinting of next_device to be the enclosing class
from typing import Dict, List, Type, Optional
from eisa import EISA

class BitVectorField:
    _start: int
    _stop: int
    _size: int

    def __init__(self, start, size):
        self.start = start
        self.size = size
        self.stop = start + size - 1
        self.mask = 2**size - 1


class BitVector:
    _bits: int

    # static variables
    _size: int = EISA.WORD_SIZE
    _fields: Dict[str, BitVectorField] = {}

    def __init__(self, val: int=0b0):
        self._bits = val

    def __str__(self):
        new_line_char = '\n'
        s = f'raw bits: {self._bits:0{2 + self._size}b}{new_line_char}'
        s += f'{new_line_char.join([f"{cur_key}: {self[cur_key]}" for cur_key in self._fields.keys()])}'
        
        return s

    def __getitem__(self, field: str) -> int:
        """gets the value stored at the specified field

        Parameters
        ----------
        field : str
            the name of the field

        Returns
        -------
        int
            the value stored at the field
        None
            if the field does not exist
        """
        target_field = None
        try:
            target_field = self._fields[field]
        except KeyError: # override the error message
            raise KeyError(f'\'{field}\' is not a field in type \'{type(self).__name__}\'') 
        else:
            return (self._bits >> target_field.start) & target_field.mask
    
    def __setitem__(self, field: str, value: int) -> None:
        """assigns the passed value to the passed field

        Parameters
        ----------
        field : str
            the name of the field
        value : int
            the value to be assigned

        Raises
        ------
        ValueError
            if the value being assigned will overflow, or if it is negative
        """

        target_field = None
        try:
            target_field = self._fields[field]
        except KeyError:
            print(f'\'{field}\' is not a field in type \'{type(self).__name__}\'')
        else:
            if value > target_field.mask:
                raise ValueError(f'Cannot to assign {value} to \'{field}\'. Can be at most {target_field.mask}')
            elif value < 0:
                raise ValueError(f'Cannot assign negative numbers to \'{field}\'')

            self._bits &= ~(target_field.mask << target_field.start)
            self._bits |= value << target_field.start

    @classmethod
    def add_field(cls, field_name: str, field_start: int, field_size: int, overlap: bool=False) -> Type[BitVector]:
        """creates a new field starting at the passed value, and of the passed size

        Parameters
        ----------
        field_name : str
            the name of the field to be created
        field_start : int
            the first bit of the new field
        field_size : int
            the size, in bits, of the new field to be created

        Returns
        -------
        Type[BitVector]
            itself

        Raises
        ------
        ValueError
            if the parameters of the new field are invalid;
            either they are negative, 
            would extend beyond the size of the bit field, 
            or the bits are already used by another field
        """

        new_field = BitVectorField(field_start, field_size)

        if new_field.start < 0:
            raise(ValueError('Cannot assign a negative to field_start'))

        if cls._size < new_field.stop:
            raise(ValueError('Cannot create a field which extends beyond the bit vector'))

        # checks if we're trying to allocate where something has already been allocated
        if not overlap:
            for cur_field_name in cls._fields:
                cur_field = cls._fields[cur_field_name]

                if new_field.start <= cur_field.stop and cur_field.start <= new_field.stop:
                    raise ValueError(f'Cannot create new field \'{field_name}\'. Overlaps with {cur_field_name}.')

        cls._fields[field_name] = new_field
        return cls
        
        

    @classmethod
    def remove_field(cls, field_name: str) -> Type[BitVector]:
        # remove the old field
        del cls._fields[field_name]
        return cls

    @classmethod
    def rename_field(cls, old_field_name: str, new_field_name) -> Type[BitVector]:
        if new_field_name in cls._fields:
            raise ValueError(f'Cannot rename field \'{old_field_name}\' to \'{new_field_name}\', \'{new_field_name}\' already exists.')
        
        cls._fields[new_field_name] = cls._fields.pop(old_field_name)

        return cls

    @classmethod
    def create_subtype(cls, name: str, size: Optional[int]=None):
        """creates a new class with the passed name, which inherits from this class

        Parameters
        ----------
        name : str
            the name of the new class to be created
        size : int, optional
            the size , in bits, of the bit vector to be created
            by default None

        Returns
        -------
        type
            the new class that was created
        """
        return type(name, (cls,), {
            '_size'         : size if size is not None else cls._size,
            '_fields'       : cls._fields.copy()
        })

# if __name__ == '__main__':
#     Instruction = BitVector.create_subtype('Instruction', size=32)

#     Instruction.add_field('opcode', 27, 5)

#     opcode_instance = Instruction()
#     opcode_instance['opcode'] = 12

#     opcode_instance._bits

#     BranchInstruction = Instruction.create_subtype('BranchInstruction')