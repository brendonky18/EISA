from argparse import ArgumentParser
from parse import parse
import ..pipeline

class AssemblerError(RuntimeError):
    def __init__(self, symbol):
        super().__init__()
        self.message = f'Unexpected symbol \'{symbol}\' was encountered'

    def __str__(self):
        return self.message

if __name__ == '__main__':
    arg_parse = ArgumentParser()
    arg_parse.add_argument('source', type=str)
    arg_parse.add_argument('-o', type=str, metavar='destination')

    args = arg_parse.parse_args()

    dst_path = 'a.txt'

    if args.destination is not None:
        dst_path = args.destination

    with open(args.source, 'r') as src_file, open(dst_path, 'w+') as dst_file:
        # parse the arguments
        for line in src_file:
            # check if the line is a label or an instruction
            leading_spaces = len(line) - len(line.lstrip())
            if leading_spaces > 0:  # line is instruction
                

                # parse the instruction
                mnemonic, fields = parse('{:>} {}', line)
                # check that the mnemonic is valid
                if mnemonic not in pipeline.OpCode: 
                    raise AssemblerError(mnemonic)
                else:
                    opcode = pipeline.OpCode[mnemonic]

                cur_InstructionType = pipeline.OpCode_InstructionType_lookup[opcode].encoding

                # TODO refactor this functionality into the Instruction class
                # checks the different types and parse accordingly
                if isinstance(cur_InstructionType, pipeline.ALU_InstructionType):
                    vector = cur_InstructionType.encoding()
                    vector['opcode'] = opcode
                    if type(cur_InstructionType) == pipeline.ALU_InstructionType:
                        vector['dest'], fields = parse('{:>}, {}', fields)
                    
                    vector['op1'], fields = parse('{:>}, {}', fields)

                    vector['imm'] = parse('#{}', fields) is not None # the '#' charcter indicates an immediate in our assembly language

                    if vector['imm']:
                        vector['immediate'], fields = parse('#{}', fields)
                    else:
                        vector['op2'], vector['offset'] = parse('{}, #{}', fields)

                # write it to the file
                print(vector._bits, file=dst_file)
            else:  # linelabel
                
                
                # calculate the offset address

                # to the dictionary
                pass