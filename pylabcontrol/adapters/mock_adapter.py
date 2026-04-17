from .base_adapter import BaseAdapter

class MockAdapter(BaseAdapter):
    """
    Simulation Adapter. Returns pre-defined responses 
    to simulate physical hardware.
    """
    def __init__(self, address: str = "MOCK::ID", **kwargs):
        super().__init__(address, **kwargs)
        self.responses = {
            "*IDN?": "PyLabControl, MockInstrument, V2-Alpha",
            "*OPC?": "1"
        }
        self.last_written = None

    def write(self, command: str):
        self.last_written = command
        # You could add logic here to update internal state (e.g. power on/off)

    def read(self) -> str:
        return self.responses.get(self.last_written, "MOCK_OK")

    def query(self, command: str) -> str:
        self.write(command)
        return self.read()

    def close(self):
        pass