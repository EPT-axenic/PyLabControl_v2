import socket
from .base_adapter import BaseAdapter

class TCPAdapter(BaseAdapter):
    """Adapter for raw TCP/IP Socket communication."""

    def __init__(self, address: str, port: int = 5025, timeout: float = 5.0, **kwargs):
        super().__init__(address, **kwargs)
        self.port = port
        self.timeout = timeout
        self.sock = None
        self._connect()

    def _connect(self):
        self.sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self.sock.settimeout(self.timeout)
        self.sock.connect((self.address, self.port))

    def write(self, command: str):
        full_cmd = (command + '\n').encode('ascii')
        self.sock.sendall(full_cmd)

    def read(self) -> str:
        return self.sock.recv(4096).decode('ascii').strip()

    def query(self, command: str) -> str:
        self.write(command)
        return self.read()

    def close(self):
        if self.sock:
            self.sock.close()