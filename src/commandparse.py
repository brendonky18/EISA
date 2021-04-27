from __future__ import annotations
from typing import Callable, Any, List
from concurrent.futures import Executor, ThreadPoolExecutor, Future
from types import TracebackType
from typing import Callable, Any, List, Optional, Dict, Tuple, Type, Literal
from dataclasses import dataclass

class InputError(ValueError):
    pass

@dataclass
class Command:
    arg_types: List[Type]
    callback: Callable[[str], Any]

class UserInput:
    command: str
    args: list[str] = []

    def __init__(self, command: str, arg_string: str=""):
        self.command = command
        self.args = arg_string.split()

class CommandParser:
    _command_executor: Executor
    _command_tasks: List[Future]

    valid_commands: Dict

    def __init__(self, name="", commands: List[Tuple[str, List[type], Callable[..., None]]]=[]):
        """Constructor

        Parameters
        ----------
        name : str, optional
            name of the terminal interface to be displayed, none by default
        commands: List[Tuple[str, List[type], Callable[..., None]], optional
            a list of commands to add
        """
        self.name = name
        self.valid_commands = {}

        self._command_executor = ThreadPoolExecutor(thread_name_prefix='command_thread')
        self._command_tasks = []

        for cur_command in commands:
            # add all of the passed commands, raise an error when attempting to add duplicate commands
            if not self.add_command(*cur_command):
                raise ValueError(f'Command \'{cur_command[0]} already exists')

    def __enter__(self) -> CommandParser:
        """allows CommandParser to be used in 'with' syntax,
        function is called on start

        Returns
        -------
        commandparse
            the reference to itself, 
            is is called after the constructor so it is required to get a reference to the newly instantiated object
        """
        from debug import terminal_print
        # initialize the terminal
        terminal_print('')
        return self

    def __exit__(
            self,
            exc_type: Optional[Type[BaseException]],
            exc_val: Optional[BaseException],
            exc_tb: Optional[TracebackType]
        ) -> Literal[False]:
        """allows CommandParser to be used in 'with' syntax,
        attempts to gracefully shut down the command parser
        """
        self._command_executor.shutdown(wait=True)
        print(f'{self.name} closed')

        # return false in order to get the error traceback if there was one
        # return true to suppress the error message
        return False

    def add_command(self, cmd: str, arg_types: List[type], callback: Callable[..., None]) -> bool:
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
        terminal_print()
        run = True

        while run:
            # gets the user's input, splits it between the command and arguments, and puts it in a named tuple
            try:
                cur_input = UserInput(*input().split(maxsplit=1))
                
            except EOFError:
                cur_input = UserInput('exit', '')
            # checks if the user wants to exit the interface
            if cur_input.command == 'exit': 
                run = False
                
            # checks if the user entered a valid command
            elif cur_input.command not in self.valid_commands:
                terminal_print(f'\'{cur_input.command}\' is not recognized as a command')
            else:
                # thread so we don't wait for something to return
                def command_thread():
                    # invokes the designated callback, and passes the provided arguments as strings
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
                
                # back in the main thread
                new_task = self._command_executor.submit(command_thread)
                self._command_tasks.append(new_task)

                for task in self._command_tasks:
                    # check if the task raised any exceptions
                    if task.done() and (task_exception := task.exception()) is not None:
                        raise task_exception

                # remove all the tasks that are done
                self._command_tasks = list(filter(lambda cur_task: not cur_task.done(), self._command_tasks))

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
