from ast import literal_eval
from typing import Callable, Any, Optional
from dataclasses import dataclass

@dataclass
class Command:
    arg_types: list[type]
    callback: Callable[[str], Any]

class UserInput:
    command: str
    args: list[str] = []

    def __init__(self, command: str, arg_string: str=""):
        self.command = command
        self.args = arg_string.split()

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

    def add_command(self, cmd: str, arg_types: list[type], callback: Callable[..., Any]) -> bool:
        """add a command which the terminal will recognize

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
            self.valid_commands[cmd] = Command(arg_types, callback)
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
                    # invokes the designated callback, and passes the provided arguments as strings
                    cur_cmd = self.valid_commands[cur_input.command]
                    cur_cmd.callback(*cur_input.args, arg_types=cur_cmd.arg_types)
                except (TypeError, ValueError) as e: # will error on anything that isn't a literal, including strings
                        num_args = len(self.valid_commands[cur_input.command].arg_types)
                        print(f'invalid input, {cur_input.command} requires {num_args} argument{"s" if num_args > 1 else ""} of type{"s" if num_args > 1 else ""} {", ".join([f"<{t.__name__}>" for t in self.valid_commands[cur_input.command].arg_types])}. You entered {cur_input.args}')
                        


def commandparse_cb(func) -> Callable[..., Any]: 
    def commandparse_cb_wrapper(*args, arg_types: list[type]=[int], **kwargs):
        if not len(args) == len(arg_types):
            raise ValueError("lists do not match")
        
        # casted_args = [any] * len(args)
        casted_args = map(lambda arg_type, arg: arg_type(arg), arg_types, args)

        # for i in range(len(args)):
        #     casted_args[i] = arg_types[i](args[i])

        return func(*casted_args)
    return commandparse_cb_wrapper
        
            

                

