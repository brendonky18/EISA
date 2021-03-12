from ast import literal_eval
import types
from dataclasses import dataclass

@dataclass
class Command:
    arg_type: type = None
    callback: types.LambdaType = lambda x: print("default callback")
@dataclass
class UserInput:
    command: str = None
    args: str = ''

class CommandParser:
    def __init__(self, name=""):
        self.name = name
        self.user_commands = {}

    def add_command(self, cmd: str, arg_type: type, callback: types.LambdaType):
        self.user_commands[cmd] = Command(arg_type , callback)

    def start(self):
        run = True
        while run:
            # gets the user's input, splits it between the command and arguments, and puts it in a named tuple
            cur_input = UserInput(*input(f'{self.name}$ ').split(maxsplit=1))

            if cur_input.command == 'exit': # checks if the user wants to exit the interface
                run = False
                continue
            elif cur_input.command not in self.user_commands:
                print(f'\'{cur_input.command}\' is not recognized as a command')
            else:
                try:
                    self.user_commands[cur_input.command].callback(*cur_input.args.split())
                except TypeError: # will error on anything that isn't a literal, including strings
                    print(f'invalid input, {cur_input.command} requires {self.user_commands[cur_input.command].arg_type}. You entered \'{cur_input.args}\'')

                

