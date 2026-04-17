import pyvisa as visa
from .base_adapter import BaseAdapter

class VISAAdapter(BaseAdapter):
    """
    Adapter for VISA-compliant instruments (GPIB, USB-TMC, TCPIP::INSTR).
    Refactored from the legacy ConnectionManager.
    """
    def __init__(self, address: str, timeout: int = 5000, term_chars: str = '\n', **kwargs):
        super().__init__(address, **kwargs)
        self.rm = visa.ResourceManager()
        self.inst = self.rm.open_resource(address)
        self.inst.timeout = timeout
        self.inst.write_termination = term_chars
        self.inst.read_termination = term_chars

    def write(self, command: str):
        self.inst.write(command)

    def read(self) -> str:
        return self.inst.read().strip()

    def query(self, command: str) -> str:
        return self.inst.query(command).strip()

    def close(self):
        self.inst.close()
        self.rm.close()