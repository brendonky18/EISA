import sys
from copy import copy

from PyQt6.QtCore import Qt, QDir
from PyQt6.QtGui import QStandardItemModel
from PyQt6.QtWidgets import *

from memory_subsystem import MemorySubsystem
from pipeline import PipeLine, Instruction, DecodeError, Instructions, OpCode, ConditionCode

from eisa import EISA

# from debug import *
# from main import *

'''
class TableModel(QStandardItemModel):

    def __init__(self):
        super().__init__()

    def setMatrix(self, matrix):

        self.setColumnCount(len(matrix[0]))
        for (i, colHeader) in enumerate(matrix[0]):
            self.setHeaderData(i, Qt.Horizontal, colHeader)

        for (i, row) in enumerate(matrix[1:]):
            self.insertRow(i)
            for (j, cell) in enumerate(row):
                self.setData(self.index(i, j), cell)
'''
def format_list_to_table(rows: int, cols: int, table_list: list[int]) -> list[list]:
    table = []

    for i in range(rows+1):
        table.append([0 for j in range(cols+1)])

    list_counter = 0
    for i in range(1, rows+1):
        for j in range(1, cols+1):
            table[i][j] = table_list[list_counter]
            list_counter += 1

    return table


def set_headers(rows: int, cols: int, table: list[list]) -> list[list]:
    row_headers = []
    for i in range(rows+1):
        table[i][0] = f"Base: {cols * (i)}"
        row_headers.append(table[i][0])

    for i in range(cols+1):
        table[0][i] = f"Offset: {i}"

    return table, row_headers  # TODO - Test whether this returns the correct table


class MemoryGroup:
    ram_table: list[list]
    cache_table: list[list]
    regs_table: list[list]

    ram_rows: int
    ram_cols: int

    cache_rows: int
    cache_cols: int

    regs_rows: int
    regs_cols: int

    memory: MemorySubsystem

    ram_widget: QTableWidget
    cache_widget: QTableWidget
    regs_widget: QTableWidget

    def __init__(self, regs: list[int], memory_subsystem: MemorySubsystem):

        self.ram_rows = 32
        self.ram_cols = 8

        self.cache_rows = 2
        self.cache_cols = 8

        self.regs_rows = 4
        self.regs_cols = 8

        self.ram_box = QGroupBox("Memory")
        ramvbox = QVBoxLayout()

        self.cache_box = QGroupBox("Cache")
        cachevbox = QVBoxLayout()

        self.regs_box = QGroupBox("Registers")
        regsvbox = QVBoxLayout()

        self.memory = memory_subsystem

        self.ram = self.memory._RAM
        self.cache = self.memory._cache._cache  # NOTE - List of Cacheways #TODO -  have brendon look at reading cache values
        self.regs = regs

        self.load_memory()

        ramvbox.addWidget(self.ram_widget)
        cachevbox.addWidget(self.cache_widget)
        regsvbox.addWidget(self.regs_widget)

        ramvbox.setSpacing(0)

        self.ram_box.setLayout(ramvbox)
        self.cache_box.setLayout(cachevbox)
        self.regs_box.setLayout(regsvbox)

        #self.ram_box.setMinimumWidth(500)

    def load_ram(self):
        self.ram_table, row_headers = set_headers(self.ram_rows, self.ram_cols,
                                     format_list_to_table(self.ram_rows, self.ram_cols, self.ram))
        self.ram_widget = QTableWidget(self.ram_rows, self.ram_cols)
        for i in range(1, self.ram_rows+1):
            for j in range(1, self.ram_cols+1):
                temp = QTableWidgetItem()
                temp.setData(0, self.ram_table[i][j])
                self.ram_widget.setItem(i-1, j-1, temp)

        self.ram_widget.setHorizontalHeaderLabels(self.ram_table[0])
        self.ram_widget.setVerticalHeaderLabels(row_headers)

    def load_cache(self):
        self.cache_table, row_headers = set_headers(self.cache_rows, self.cache_cols,
                                       format_list_to_table(self.cache_rows, self.cache_cols, self.cache))
        self.cache_widget = QTableWidget(self.cache_rows, self.cache_cols)
        for i in range(1, self.cache_rows + 1):
            for j in range(1, self.cache_cols + 1):
                temp = QTableWidgetItem()
                temp.setData(0, self.cache_table[i][j])
                self.cache_widget.setItem(i - 1, j - 1, temp)

    def load_regs(self):
        self.regs_table, row_headers = set_headers(self.regs_rows, self.regs_cols,
                                      format_list_to_table(self.regs_rows, self.regs_cols, self.regs))
        self.regs_widget = QTableWidget(self.regs_rows, self.regs_cols)
        for i in range(1, self.regs_rows + 1):
            for j in range(1, self.regs_cols + 1):
                temp = QTableWidgetItem()
                temp.setData(0, self.regs_table[i][j])
                self.regs_widget.setItem(i - 1, j - 1, temp)

        self.regs_widget.setHorizontalHeaderLabels(self.regs_table[0])
        self.regs_widget.setVerticalHeaderLabels(row_headers)

    def load_memory(self):
        self.load_ram()
        self.load_cache()  # TODO - not loading cache for now. Need Brendon to look at reading cache vals
        self.load_regs()


class StageGroup:
    fields: list[QLabel]

    def __init__(self, stage_name: str):
        self.stage = QGroupBox(stage_name)
        self.fields = []
        vbox = QVBoxLayout()

        '''
        self.encoded = QLabel("Encoded: ERROR")
        vbox.addWidget(self.encoded)

        self.opcode = QLabel("Opcode: ERROR")
        vbox.addWidget(self.opcode)

        self.reg1 = QLabel("Reg 1: ERROR")
        vbox.addWidget(self.reg1)

        self.reg2 = QLabel("Reg 2: ERROR")
        vbox.addWidget(self.reg2)

        self.reg3 = QLabel("Reg 3: ERROR")
        vbox.addWidget(self.reg3)

        self.op1 = QLabel("Op 1: ERROR")
        vbox.addWidget(self.op1)

        self.op2 = QLabel("Op 2: ERROR")
        vbox.addWidget(self.op2)

        self.op3 = QLabel("Op 3: ERROR")
        vbox.addWidget(self.op3)

        self.computed = QLabel("Computed: ERROR")
        vbox.addWidget(self.computed)
        '''
        opcode = QLabel("Opcode: Null")
        self.fields.append(opcode)
        vbox.addWidget(opcode)

        computed = QLabel("Computed: Null")
        self.fields.append(computed)
        vbox.addWidget(computed)

        for i in range(2, EISA.MAX_INSTRUCTION_FIELDS):
            self.fields.append(QLabel(""))
            vbox.addWidget(self.fields[i])

        stalled = QLabel("")
        self.fields.append(stalled)
        vbox.addWidget(stalled)

        self.stage.setLayout(vbox)


class Dialog(QDialog):
    """Dialog."""

    _memory: MemorySubsystem
    _pipeline: PipeLine
    _hex: True

    def __init__(self, memory: MemorySubsystem, pipeline: PipeLine, parent=None):
        """Initializer."""
        super().__init__(parent)
        self._memory = memory
        self._pipeline = pipeline
        self._hex = True

        self.setWindowTitle('Encryptinator')
        self.dlgLayout = QVBoxLayout()  # QVBoxLayout()
        self.whole_layout = QHBoxLayout()
        self.build_stages()
        self.build_pipeline_layout()

        self.memory_group = MemoryGroup(self._pipeline._registers, self._pipeline._memory)
        self.build_memory_layout()

        self.update_ui()

        self.whole_layout.addLayout(self.dlgLayout)


        self.setLayout(self.whole_layout)

    def build_ui(self):
        app = QApplication(sys.argv)
        # Build UI dialog box
        dlg = Dialog()
        dlg.update_ui()
        dlg.show()
        # sys.exit(app.exec_())

    def update_ui(self):
        self.destroy_stage_fields()
        self.load_stages()
        self.update_memory()
        self.pc_counter.setText(f"PC: {self._pipeline._pc}")
        self.cycle_counter.setText(f"Cycles: {self._pipeline._cycles}")
        self.flags.setText(f"Flags: {str(self._pipeline.condition_flags)}")

    def cycle_ui(self, event):
        self._pipeline.cycle_pipeline()
        self.update_ui()

    '''
    def build_cycle_button(self):
        self.cycle_button = QPushButton("Cycle")
        self.cycle_button.clicked.connect(self.cycle_ui)
        self.dlgLayout.addWidget(self.cycle_button, 2, 5)
    '''

    def build_stages(self):
        self.stage_fetch = StageGroup("Fetch")  # self.create_stage_group("Fetch")
        self.stage_decode = StageGroup("Decode")  # self.create_stage_group("Decode")
        self.stage_execute = StageGroup("Execute")  # self.create_stage_group("Execute")
        self.stage_memory = StageGroup("Memory")  # self.create_stage_group("Memory")
        self.stage_writeback = StageGroup("Writeback")  # self.create_stage_group("Writeback")
        self.pc_counter = QLabel(f"PC: {self._pipeline._pc}")
        self.flags = QLabel(f"Flags: {str(self._pipeline.condition_flags)}")
        self.cycle_counter = QLabel(f"Cycle: {self._pipeline._cycles}")
        self.stages = [self.stage_fetch, self.stage_decode, self.stage_execute, self.stage_memory, self.stage_writeback]
        for i in self.stages:
            i.stage.adjustSize()
            i.stage.setMaximumWidth(i.stage.width() + 20)
            i.stage.setMinimumWidth(i.stage.width() + 20)

    def build_pipeline_layout(self):
        stages_layout = QHBoxLayout()  # QGridLayout()
        stages_layout.addWidget(self.stage_fetch.stage)
        stages_layout.addWidget(self.stage_decode.stage)
        stages_layout.addWidget(self.stage_execute.stage)
        stages_layout.addWidget(self.stage_memory.stage)
        stages_layout.addWidget(self.stage_writeback.stage)


        self.hex_button = QPushButton("Hex Toggle")
        self.hex_button.clicked.connect(self.hex_toggle)
        self.load_button = QPushButton("Load Program")
        self.load_button.clicked.connect(self.load_program_from_file)
        self.exch_button = QPushButton("Load Exch. Sort")
        # self.exch_button.clicked.connect(self.load_exchange_demo)  # TODO - Implement Exchange Sort Benchmark/Demo
        self.matrix_button = QPushButton("Load Matrix Mult.")
        # self.matrix_button.clicked.connect(self.load_matrix_demo)  # TODO - Implement Matrix Multiply Benchmark/Demo
        self.cycle_button = QPushButton("Cycle")
        self.cycle_button.clicked.connect(self.cycle_ui)

        button_layout = QHBoxLayout()
        button_layout.addWidget(self.hex_button)
        button_layout.addWidget(self.load_button)
        button_layout.addWidget(self.exch_button)
        button_layout.addWidget(self.matrix_button)
        button_layout.addWidget(self.cycle_button)

        counters_group = QGroupBox()
        counters_layout = QHBoxLayout()
        counters_layout.addWidget(self.pc_counter)  # TODO - Add LR and ALU regs, Add cycle counter
        counters_layout.addWidget(self.cycle_counter)
        counters_layout.addWidget(self.flags)
        counters_group.setLayout(counters_layout)

        pipeline_group = QGroupBox("Pipeline")

        pipeline_layout = QVBoxLayout()
        pipeline_layout.addWidget(counters_group)
        pipeline_layout.addLayout(stages_layout)
        pipeline_layout.addLayout(button_layout)

        pipeline_group.setLayout(pipeline_layout)
        self.dlgLayout.addWidget(pipeline_group)

    def build_memory_layout(self):
        self.dlgLayout.addWidget(self.memory_group.regs_box)
        self.dlgLayout.addWidget(self.memory_group.cache_box)
        self.whole_layout.addWidget(self.memory_group.ram_box)

    def destroy_stage_fields(self):
        for i in self.stages:
            for j in range(EISA.MAX_INSTRUCTION_FIELDS):
                i.fields[j].setText("")


    def load_stage(self, stage: int):
        '''Loads a SINGLE SPECIFIED stage of the pipeline into the UI'''

        instruction = self._pipeline._pipeline[stage]
        private_stage = self.stages[stage]

        private_stage.fields[0].setText(f"Opcode: {str(instruction.opcode)}")
        private_stage.fields[1].setText(f"Computed: {str(instruction.computed)}")

        if stage == 0:
            private_stage.fields[EISA.MAX_INSTRUCTION_FIELDS].setText(f"Stalled: {str(self._pipeline._stalled_fetch)}")

        if stage == 3:
            private_stage.fields[EISA.MAX_INSTRUCTION_FIELDS].setText(f"Stalled: {str(self._pipeline._stalled_memory)}")

        if instruction.opcode == 0:
            return

        decoded = instruction._decoded

        if decoded is None:
            return

        decoded_fields = decoded._fields

        counter = 2
        for i in decoded_fields:
            key = str(i)
            if key == 'opcode' or len(key) == 1:
                continue
            private_stage.fields[counter].setText(f"{key.capitalize()}: {str(decoded[key])}")
            counter += 1


        '''
        self.stages[stage].encoded.setText(f"Encoded: {self._pipeline._pipeline[stage]._encoded}")
        self.stages[stage].opcode.setText(f"Opcode: {self._pipeline._pipeline[stage].opcode}")

        try:
            dest = self._pipeline._pipeline[stage].try_get('dest')
        except DecodeError:
            dest = None

        try:
            src1 = self._pipeline._pipeline[stage].try_get('op1')
        except DecodeError:
            src1 = None

        try:
            src2 = self._pipeline._pipeline[stage].try_get('op2')
        except DecodeError:
            dest = None

        self.stages[stage].reg1.setText(f"Dest: {dest}")
        self.stages[stage].reg2.setText(f"Src1: {src1}")
        self.stages[stage].reg3.setText(f"Src2: {src2}")

        self.stages[stage].op1.setText(f"DestVal: {self._pipeline._registers[dest]}")
        self.stages[stage].op2.setText(f"Op1: {self._pipeline._registers[src1]}")
        self.stages[stage].op3.setText(f"Op2: {self._pipeline._registers[src2]}")

        #self.stages[stage].computed.setText(f"Computed: {self._pipeline._pipeline[stage]._computed}")
        '''
        '''
        self.stages[stage].encoded.setText(f"Encoded: {self._pipeline._pipeline[stage]._encoded}")
        self.stages[stage].opcode.setText(f"Opcode: {self._pipeline._pipeline[stage]._opcode}")
        self.stages[stage].reg1.setText(f"Reg1: {self._pipeline._pipeline[stage].try_get('dest')}")
        self.stages[stage].reg2.setText(f"Reg2: {self._pipeline._pipeline[stage]._regB}")
        self.stages[stage].reg3.setText(f"Reg3: {self._pipeline._pipeline[stage]._regC}")
        self.stages[stage].op1.setText(f"Op1: {self._pipeline._pipeline[stage]._opA}")
        self.stages[stage].op2.setText(f"Op2: {self._pipeline._pipeline[stage]._opB}")
        self.stages[stage].op3.setText(f"Op3: {self._pipeline._pipeline[stage]._opC}")
        self.stages[stage].computed.setText(f"Computed: {self._pipeline._pipeline[stage].computed}")
        '''

    def load_stages(self):
        '''Loads ALL stages of the pipeline into the UI.'''
        for i in range(5):
            self.load_stage(i)

    def update_ram(self):
        ram = [i for i in self._pipeline._memory._RAM]

        for i in range(1, self.memory_group.ram_rows+1):
            for j in range(1, self.memory_group.ram_cols+1):
                val = ram[((i-1)*self.memory_group.ram_cols) + (j-1)]
                if self._hex:
                    val = hex(val)
                self.memory_group.ram_table[i][j] = val
                self.memory_group.ram_widget.item(i-1, j-1).setText(str(val))

    def update_regs(self):
        regs = self._pipeline._registers.copy()

        for i in range(1, self.memory_group.regs_rows+1):
            for j in range(1, self.memory_group.regs_cols+1):
                val = regs[((i - 1) * self.memory_group.regs_cols) + (j - 1)]
                if self._hex:
                    val = hex(val)
                self.memory_group.regs_table[i][j] = val
                self.memory_group.regs_widget.item(i-1, j-1).setText(str(val))

    def update_cache(self):
        cache = self._pipeline._memory._cache._cache

        for i in range(1, self.memory_group.cache_rows+1):
            for j in range(1, self.memory_group.cache_cols+1):
                val = [i for i in cache[((i - 1) * self.memory_group.cache_cols) + (j - 1)]._data]
                if self._hex:
                    for k in range(len(val)):
                        val[k] = hex(val[k])
                self.memory_group.cache_table[i][j] = val
                self.memory_group.cache_widget.item(i-1, j-1).setText(str(val))

    def update_memory(self):
        self.update_ram()
        self.update_regs()
        self.update_cache()

    def hex_toggle(self):
        self._hex = not(self._hex)
        self.update_ui()

    def load_program_from_file(self):
        filepath = QFileDialog.getOpenFileName(self, 'Hey! Select a File')[0]
        if filepath == '':
            return

        # TODO - retain prior pipeline/memory in load program rather than deleting it

        del self._memory
        del self._pipeline

        self._memory = MemorySubsystem(EISA.ADDRESS_SIZE, EISA.CACHE_SIZE, 1, 1, EISA.RAM_SIZE, 2, 2)
        self._pipeline = PipeLine(0, [0] * 32, self._memory)

        with open(filepath) as f:
            content = f.readlines()
        instructions = [x.strip() for x in content]  # Remove whitespace

        for i in range(len(instructions)):
            self._memory._RAM[i] = int(instructions[i], 2)

        self.update_ui()



    def load_exchange_demo(self):
        pass

    def load_matrix_demo(self):
        pass

if __name__ == '__main__':
    app = QApplication(sys.argv)

    memory = MemorySubsystem(EISA.ADDRESS_SIZE, EISA.CACHE_SIZE, 1, 1, EISA.RAM_SIZE, 2, 2)
    my_pipe = PipeLine(0, [0] * 32, memory)

    # region Simple Add
    '''
    my_pipe._registers[31] = 10
    my_pipe._registers[4] = 30

    # Opcode: 000001 (ADD/MOV)
    # Destination: 00011 (Register 3)
    # Operand 1: 11111 (Register 31)
    # Immediate Flg: 0
    # Operand 2: 00100 (Register 4)
    # PADDING: 0000000000 (Bits 9 - 0 are Irrelevant)
    instruction = OpCode_InstructionType_lookup[0b000001].encoding()
    instruction['opcode'] = 0b000001
    instruction['dest'] = 0b00011
    instruction['op1'] = 0b11111
    instruction['op2'] = 0b00100
    instruction['imm'] = False

    # cook END instruction to signal pipeline to end
    end = OpCode_InstructionType_lookup[0b100000].encoding()

    # cook the pipe's memory
    my_pipe._memory._RAM[0] = instruction._bits
    my_pipe._memory._RAM[1] = end._bits
    '''
    # endregion Simple Add

    # region Load 2 operands
    '''
    # Opcode: 001101 (LOAD)
    instruction = OpCode_InstructionType_lookup[0b001101].encoding()
    instruction['opcode'] = 0b001101
    instruction['dest'] = 3
    instruction['lit'] = False
    instruction['base'] = 31

    # TODO - is the offset being treated as a register number or a literal?
    instruction['offset'] = 0

    my_pipe._memory._RAM[0] = instruction._bits

    my_pipe._memory._RAM[12] = 72
    my_pipe._registers[31] = 12

    # Opcode: 001101 (LOAD)
    instruction2 = OpCode_InstructionType_lookup[0b001101].encoding()
    instruction2['opcode'] = 0b001101
    instruction2['dest'] = 4
    instruction2['lit'] = False
    instruction2['base'] = 30
    instruction2['offset'] = 0

    my_pipe._memory._RAM[1] = instruction2._bits

    my_pipe._memory._RAM[13] = 36
    my_pipe._registers[30] = 13

    # cook END instruction to signal pipeline to end
    end = OpCode_InstructionType_lookup[0b100000].encoding()
    end['opcode'] = 0b100000
    my_pipe._memory._RAM[2] = end._bits
    '''
    # endregion Load 2 operands

    # region Simple Store
    '''
    # Opcode: 001110 (STR) Src: 00011 (Register 3) PADDING: 00000 (Bits 20-16 are Irrelevant) Base/Literal: 11111
    # (Register 31) Offset/Literal: 0000000000 (Offset 0) TODO - is this a register number or a literal????
    #  Assuming reg num for now

    instruction = OpCode_InstructionType_lookup[0b001110].encoding()
    instruction['opcode'] = 0b001110
    instruction['src'] = 3
    instruction['base'] = 31
    instruction['offset'] = 0

    my_pipe._memory._RAM[0] = instruction._bits  # Set the 0th word in memory to this instruction, such that it's
    # the first instruction the PC points to

    my_pipe._registers[31] = 18  # Storing to address 18 in memory

    my_pipe._registers[3] = 256  # storing value in register 3

    # cook END instruction to signal pipeline to end
    end = OpCode_InstructionType_lookup[0b100000].encoding()
    end['opcode'] = 0b100000
    my_pipe._memory._RAM[1] = end._bits  # END is stored at address (word) 1 in memory
    '''
    # endregion Simple Store

    # region Moderate Complexity Test
    # Load 2 operands -> Add Them -> Store Result

    '''
    # Opcode: 001101 (LOAD)
    instruction = OpCode_InstructionType_lookup[0b001101].encoding()
    instruction['opcode'] = 0b001101
    instruction['dest'] = 3
    instruction['lit'] = False
    instruction['base'] = 31

    # TODO - is the offset being treated as a register number or a literal?
    instruction['offset'] = 0

    my_pipe._memory._RAM[0] = instruction._bits

    my_pipe._memory._RAM[12] = 72
    my_pipe._registers[31] = 12

    # Opcode: 001101 (LOAD)
    instruction2 = OpCode_InstructionType_lookup[0b001101].encoding()
    instruction2['opcode'] = 0b001101
    instruction2['dest'] = 4
    instruction2['lit'] = False
    instruction2['base'] = 30
    instruction2['offset'] = 0

    my_pipe._memory._RAM[1] = instruction2._bits

    my_pipe._memory._RAM[13] = 36
    my_pipe._registers[30] = 13

    # Opcode: 000001 (ADD/MOV)
    instruction3 = OpCode_InstructionType_lookup[0b000001].encoding()
    instruction3['opcode'] = 0b000001
    instruction3['dest'] = 24
    instruction3['op1'] = 4  # Destination of the first load
    instruction3['op2'] = 3  # Destination of the second load
    instruction3['imm'] = False

    my_pipe._memory._RAM[2] = instruction3._bits

    # Opcode: 001110 (STR) Src: 00011 (Register 3) PADDING: 00000 (Bits 20-16 are Irrelevant) Base/Literal: 11111
    # (Register 31) Offset/Literal: 0000000000 (Offset 0) TODO - is this a register number or a literal????
    #  Assuming reg num for now

    instruction4 = OpCode_InstructionType_lookup[0b001110].encoding()
    instruction4['opcode'] = 0b001110
    instruction4['src'] = 24  # Destination of the add op
    instruction4['base'] = 16  # Register holding the address we want to store the result (Register 16)
    instruction4['offset'] = 0

    my_pipe._memory._RAM[3] = instruction4._bits
    my_pipe._registers[16] = 8

    # cook END instruction to signal pipeline to end
    end = OpCode_InstructionType_lookup[0b100000].encoding()
    end['opcode'] = 0b100000
    my_pipe._memory._RAM[4] = end._bits  # END is stored at address (word) 1 in memory
    '''
    # endregion Moderate Complexity Test

    # region Unconditional Branching Test

    # Registers in use: 3, 31, 4, 30, 24, 16, 12
    # Memory in use: 0, 12, 1, 13, 8, 30, 31, 32

    mem_sub = MemorySubsystem(EISA.ADDRESS_SIZE, 4, 1, 1, 8, 2, 2)

    my_pipe = PipeLine(0, [1 for i in range(EISA.NUM_GP_REGS)], mem_sub)

    # Opcode: 001101 (LOAD)
    instruction = Instructions[OpCode.LDR].encoding()
    instruction['opcode'] = 0b001101
    instruction['dest'] = 3
    instruction['lit'] = False
    instruction['base'] = 31

    # TODO - is the offset being treated as a register number or a literal?
    instruction['offset'] = 0

    my_pipe._memory._RAM[0] = instruction._bits

    my_pipe._memory._RAM[12] = 72
    my_pipe._registers[31] = 12

    # Opcode: 001101 (LOAD)
    instruction2 = Instructions[OpCode.LDR].encoding()
    instruction2['opcode'] = 0b001101
    instruction2['dest'] = 4
    instruction2['lit'] = False
    instruction2['base'] = 30
    instruction2['offset'] = 0

    my_pipe._memory._RAM[1] = instruction2._bits

    my_pipe._memory._RAM[13] = 36
    my_pipe._registers[30] = 13

    # Opcode: 011110 (B)
    instructionB = Instructions[OpCode.B].encoding()
    instructionB['opcode'] = 0b011110
    instructionB['cond'] = ConditionCode.EQ
    instructionB['imm'] = False
    instructionB['base'] = 12
    instructionB['offset'] = 0

    my_pipe._registers[12] = 30
    my_pipe._memory._RAM[2] = instructionB._bits

    # Opcode: 000001 (ADD/MOV)
    instruction3 = Instructions[OpCode.ADD].encoding()
    instruction3['opcode'] = 0b000001
    instruction3['dest'] = 24
    instruction3['op1'] = 4  # Destination of the first load
    instruction3['op2'] = 3  # Destination of the second load
    instruction3['imm'] = False

    my_pipe._memory._RAM[30] = instruction3._bits

    # Opcode: 001110 (STR) Src: 00011 (Register 3) PADDING: 00000 (Bits 20-16 are Irrelevant) Base/Literal: 11111
    # (Register 31) Offset/Literal: 0000000000 (Offset 0) TODO - is this a register number or a literal????
    #  Assuming reg num for now

    instruction4 = Instructions[OpCode.STR].encoding()
    instruction4['opcode'] = 0b001110
    instruction4['src'] = 24  # Destination of the add op
    instruction4['base'] = 16  # Register holding the address we want to store the result (Register 16)
    instruction4['offset'] = 0

    my_pipe._memory._RAM[31] = instruction4._bits
    my_pipe._registers[16] = 8

    # cook END instruction to signal pipeline to end
    end = Instructions[OpCode.END].encoding()
    end['opcode'] = 0b100000
    my_pipe._memory._RAM[32] = end._bits  # END is stored at address (word) 1 in memory
    # endregion Unconditional Branching Test



    #  Conditional looping + branching test. Cleared as of 4/24
    '''
    my_pipe._registers[2] = 24  # Counter
    my_pipe._registers[0] = 20  # Condition to beat
    my_pipe._registers[1] = 1  # Amount to increment counter by
    my_pipe._registers[3] = 0  # Address to branch back to

    instruction1 = OpCode_InstructionType_lookup[0b001101].encoding()
    instruction1['opcode'] = 0b001101
    instruction1['dest'] = 25  # Load into register 25
    instruction1['base'] = 2  # Register 2 holds the memory address who's value loads into reg 25
    instruction1['offset'] = 0
    instruction1['lit'] = False

    instruction2 = OpCode_InstructionType_lookup[0b000001].encoding()
    instruction2['opcode'] = 0b0000001
    instruction2['dest'] = 31  # Put sum in reg 31
    instruction2['op1'] = 31  # Register 31 as op1
    instruction2['op2'] = 25  # Register 25 as op2
    instruction2['imm'] = False

    instruction3 = OpCode_InstructionType_lookup[0b000001].encoding()
    instruction3['opcode'] = 0b0000001
    instruction3['dest'] = 2  # Put sum in reg 2
    instruction3['op1'] = 2  # Register 2 as op1
    instruction3['op2'] = 1  # Register 1 as op1
    instruction3['imm'] = False

    # Opcode: 011110 (CMP)
    instructionC = OpCode_InstructionType_lookup[0b000011].encoding()
    instructionC['opcode'] = 0b000011
    instructionC['op1'] = 31  # Register 31 as op1
    instructionC['op2'] = 0  # Register 0 as op2
    instructionC['imm'] = False

    #  Add flag fields to branch instructions

    #.add_field('v', 22, 1) 
    #.add_field('c', 23, 1) 
    #.add_field('z', 24, 1) 
    #.add_field('n', 25, 1)


    # Opcode: 011110 (B)
    instructionB = OpCode_InstructionType_lookup[0b011110].encoding()
    instructionB['opcode'] = 0b011110

    instructionB.add_field('z', 24, 1)
    instructionB['z'] = 1

    instructionB.add_field('or', 21, 1)
    instructionB['or'] = 1

    instructionB.add_field('n', 25, 1)
    instructionB['n'] = 1

    instructionB['imm'] = False
    instructionB['base'] = 3  # Register 3 has the address to branch back to
    instructionB['offset'] = 0

    instructionBLOCK = OpCode_InstructionType_lookup[0b0].encoding()
    instructionBLOCK['opcode'] = 0b0

    # cook END instruction to signal pipeline to end
    end = OpCode_InstructionType_lookup[0b100000].encoding()
    end['opcode'] = 0b100000

    my_pipe._memory._RAM[0] = instruction1._bits
    my_pipe._memory._RAM[1] = instruction2._bits
    my_pipe._memory._RAM[2] = instruction3._bits
    my_pipe._memory._RAM[3] = instructionC._bits
    my_pipe._memory._RAM[4] = instructionB._bits
    my_pipe._memory._RAM[5] = instructionBLOCK._bits
    my_pipe._memory._RAM[6] = end._bits

    my_pipe._memory._RAM[24] = 5
    my_pipe._memory._RAM[25] = 5
    my_pipe._memory._RAM[26] = 5
    my_pipe._memory._RAM[27] = 5
    my_pipe._memory._RAM[28] = 5
    my_pipe._memory._RAM[29] = 5
    '''
    # Build UI dialog box
    dlg = Dialog(memory, my_pipe)

    dlg.show()

    try:
        app.exec()
    except Exception as e:
        print(e)

'''
class PipeLineUI(QThread):
    memory: MemorySubsystem
    pipeline: PipeLine

    def __init__(self, memory: MemorySubsystem, pipeline: PipeLine):
        QThread.__init__(self)
        self.memory = memory
        self.pipeline = pipeline

    def __del__(self):
        self.wait()

    def run(self) -> None:
        app = QApplication(sys.argv)

        Clock.start()

        # Build UI dialog box
        dlg = Dialog(self.memory, self.pipeline)

        dlg.show()

        # sys.exit(app.exec_())


class DebugThread(QThread):
    memory: MemorySubsystem
    pipeline: PipeLine

    def __init__(self, memory: MemorySubsystem, pipeline: PipeLine):
        QThread.__init__(self)
        self.memory = memory
        self.pipeline = pipeline

    def __del__(self):
        self.wait()

    def run(self):
        main(self.memory, self.pipeline)


if __name__ == '__main__':
    # app = QApplication(sys.argv)

    memory = MemorySubsystem(EISA.ADDRESS_SIZE, EISA.CACHE_SIZE, 1, 1, EISA.RAM_SIZE, 2, 2)
    pipeline = PipeLine(0, [0] * 32, memory)

    ui_thread = PipeLineUI(memory, pipeline)
    debug_thread = DebugThread(memory, pipeline)

    ui_thread.start()
    debug_thread.start()

    # Clock.start()

    # Build UI dialog box
    # dlg = Dialog(memory, pipeline)

    # dlg.show()

    # sys.exit(app.exec_())

'''
