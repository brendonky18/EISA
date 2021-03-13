from ast import literal_eval
from typing import Callable, Any
from dataclasses import dataclass

@dataclass
class Command:
    arg_type: type 
    callback: Callable[[str], Any]
@dataclass
class UserInput:
    command: str
    args: str = ''

class CommandParser:
    def __init__(self, name=""):
        """Constructor

        Parameters
        ----------
        name : str, optional
            name of the terminal interface to be displayed, none by default
        """
        self.name = name
        self.valid_commands = {}

    # add a command which the terminal will recognize
    def add_command(self, cmd: str, arg_type: type, callback: Callable[[str], Any]) -> bool:
        """Adds a command to the terminal

        Parameters
        ----------
        cmd : str
            name of the command
        arg_type : type
            type of argument the command accepts
        callback : function(*str)
            callback function to be executed when the user enters the command
            function will be passed an array of strings, and must validate the inputs
            raise TypeError if inputs are invalid

        Returns
        -------
        bool
            True if the command was added, False if the command already exists
        """
        

        # adds the command to the dictionary of valid commands, unless it already exists
        if cmd in self.valid_commands:
            return False
        else:
            self.valid_commands[cmd] = Command(arg_type , callback)
            return True

    def start(self):
        """Starts running the termisshnal
        """

        run = True

        while run:
            # gets the user's input, splits it between the command and arguments, and puts it in a named tuple
            cur_input = UserInput(*input(f'{self.name}$ ').split(maxsplit=1))

            # checks if the user wants to exit the interface
            if cur_input.command == 'exit': 
                run = False
            
            # checks if the user entered a valid command
            elif cur_input.command not in self.valid_commands:
                print(f'\'{cur_input.command}\' is not recognized as a command')
            else:
                try:
                    self.valid_commands[cur_input.command].callback(*cur_input.args.split())
                except TypeError: # will error on anything that isn't a literal, including strings
                    print(f'invalid input, {cur_input.command} requires {self.valid_commands[cur_input.command].arg_type}. You entered \'{cur_input.args}\'')

                

