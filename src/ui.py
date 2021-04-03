import sys
from PyQt5.QtWidgets import *
from memory_subsystem import *
from pipeline import *
from clock import Clock
from debug import *
from PyQt5.QtCore import QThread
from debug import main


class StageGroup:
    def __init__(self, stage_name: str):
        self.stage = QGroupBox(stage_name)
        vbox = QVBoxLayout()

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

        self.stage.setLayout(vbox)


class Dialog(QDialog):
    """Dialog."""

    _memory: MemorySubsystem
    _pipeline: PipeLine

    def __init__(self, memory: MemorySubsystem, pipeline: PipeLine, parent=None):
        """Initializer."""
        super().__init__(parent)
        # self._memory = MemorySubsystem(EISA.ADDRESS_SIZE, EISA.CACHE_SIZE, 1, 1, EISA.RAM_SIZE, 2, 2)
        # self._pipeline = PipeLine(0, [0] * 32, self._memory)

        self._memory = memory
        self._pipeline = pipeline

        self.setWindowTitle('Encryptinator')
        self.dlgLayout = QGridLayout()  # QVBoxLayout()
        self.build_stages()
        self.build_pipeline_layout()
        self.setLayout(self.dlgLayout)
        self.load_stages()
        self.build_cycle_button()

    def build_ui(self):
        app = QApplication(sys.argv)
        Clock.start()
        # Build UI dialog box
        dlg = Dialog()
        dlg.show()
        # sys.exit(app.exec_())

    def cycle_ui(self, event):
        self._pipeline.cycle_pipeline()
        self.load_stages()

    def build_cycle_button(self):
        self.cycle_button = QPushButton("Cycle")
        self.cycle_button.clicked.connect(self.cycle_ui)
        self.dlgLayout.addWidget(self.cycle_button, 2, 5)

    def build_stages(self):
        self.stage_fetch = StageGroup("Fetch")  # self.create_stage_group("Fetch")
        self.stage_decode = StageGroup("Decode")  # self.create_stage_group("Decode")
        self.stage_execute = StageGroup("Execute")  # self.create_stage_group("Execute")
        self.stage_memory = StageGroup("Memory")  # self.create_stage_group("Memory")
        self.stage_writeback = StageGroup("Writeback")  # self.create_stage_group("Writeback")
        self.stages = [self.stage_fetch, self.stage_decode, self.stage_execute, self.stage_memory, self.stage_writeback]

    def build_pipeline_layout(self):
        self.dlgLayout.addWidget(self.stage_fetch.stage, 1, 1)
        self.dlgLayout.addWidget(self.stage_decode.stage, 1, 2)
        self.dlgLayout.addWidget(self.stage_execute.stage, 1, 3)
        self.dlgLayout.addWidget(self.stage_memory.stage, 1, 4)
        self.dlgLayout.addWidget(self.stage_writeback.stage, 1, 5)

    def load_stage(self, stage: int):
        self.stages[stage].encoded.setText(f"Encoded: {self._pipeline._pipeline[stage]._encoded}")
        self.stages[stage].opcode.setText(f"Opcode: {self._pipeline._pipeline[stage]._opcode}")
        self.stages[stage].reg1.setText(f"Reg1: {self._pipeline._pipeline[stage]._regA}")
        self.stages[stage].reg2.setText(f"Reg2: {self._pipeline._pipeline[stage]._regB}")
        self.stages[stage].reg3.setText(f"Reg3: {self._pipeline._pipeline[stage]._regC}")
        self.stages[stage].op1.setText(f"Op1: {self._pipeline._pipeline[stage]._opA}")
        self.stages[stage].op2.setText(f"Op2: {self._pipeline._pipeline[stage]._opB}")
        self.stages[stage].op3.setText(f"Op3: {self._pipeline._pipeline[stage]._opC}")
        self.stages[stage].computed.setText(f"Computed: {self._pipeline._pipeline[stage]._computed}")

    def load_stages(self):
        for i in range(5):
            self.load_stage(i)


if __name__ == '__main__':
    app = QApplication(sys.argv)

    app.setStyle('Windows')

    memory = MemorySubsystem(EISA.ADDRESS_SIZE, EISA.CACHE_SIZE, 1, 1, EISA.RAM_SIZE, 2, 2)
    pipeline = PipeLine(0, [0 for i in range(32)], memory)

    Clock.start()

    # Build UI dialog box
    dlg = Dialog(memory, pipeline)

    dlg.show()

    sys.exit(app.exec_())

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