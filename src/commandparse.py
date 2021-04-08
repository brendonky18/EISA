from typing import Callable, Any, List
from threading import Thread
from typing import Callable, Any, List
from dataclasses import dataclass
from clock import Clock

class InputError(ValueError):
    pass

@dataclass
class Command:
    arg_types: list[type ]
    callback: Callable[[str], Any]

class UserInput:
    command: str
    args: list[str] = []

    def __init__(self, command: str, arg_string: str=""):
        self.command = command
        self.args = arg_string.split()

class CommandParser:
    command_threads: List[Thread] = []

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
        from debug import terminal_print

        run = True
        Clock.start()

        while run:
            # gets the user's input, splits it between the command and arguments, and puts it in a named tuple
            try:
                terminal_print('')
                cur_input = UserInput(*input().split(maxsplit=1))
                
            except EOFError:
                cur_input = UserInput('exit', '')
            # checks if the user wants to exit the interface
            if cur_input.command == 'exit': 
                run = False
                if Clock.run_clock:
                    print('Warning: Clock not stopped, stopping now')
                    Clock.stop()
                for t in CommandParser.command_threads:
                    t.join()
                
            
            # checks if the user entered a valid command
            elif cur_input.command not in self.valid_commands:
                print(f'\'{cur_input.command}\' is not recognized as a command')
            else:
                # thread so we don't wait for something to return
                def command_thread():
                    try:
                        # invokes the designated callback, and passes the provided arguments as strings
                        cur_cmd = self.valid_commands[cur_input.command]
                        cur_cmd.callback(*cur_input.args, arg_types=cur_cmd.arg_types)
                    except InputError as e: # will error on anything that isn't a literal, including strings
                        num_args = len(self.valid_commands[cur_input.command].arg_types)
                        err_msg = (f'{str(e)}, '
                            f'{cur_input.command} requires {num_args} argument{"s" if num_args > 1 else ""} of type{"s" if num_args > 1 else ""} '
                            f'{", ".join([f"<{t.__name__}>" for t in self.valid_commands[cur_input.command].arg_types])}. '
                            f'You entered {cur_input.args}')
                        
                        terminal_print(err_msg)
                        
                    return

                new_thread = Thread(target=command_thread, name=f'Command thread - {cur_input.command}: {cur_input.args}')
                new_thread.start()
                self.command_threads.append(new_thread)
                


def commandparse_cb(func) -> Callable[..., Any]: 
    def commandparse_cb_wrapper(*args, arg_types: list[type]=[int], **kwargs):
        if not len(args) == len(arg_types):
            raise InputError("Number of parameters do not match")
        
        # casted_args = [any] * len(args)
        try:
            casted_args = list(map(lambda arg_type, arg: arg_type(arg), arg_types, args))
        except (ValueError, TypeError):
            raise InputError('Could not cast inputs')
        # for i in range(len(args)):
        #     casted_args[i] = arg_types[i](args[i])

        return func(*casted_args)
    return commandparse_cb_wrapper
