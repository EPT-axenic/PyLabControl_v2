from abc import ABC, abstractmethod
import logging
from pylabcontrol.utils.logging_manager import LogTiers

class BaseAdapter(ABC):
    """
    Abstract Base Class for all PyLabControl transport layers.
    Every adapter must implement these primitives.
    """
    def __init__(self, address: str, instrument_id: str = None):
        self.address = address
        self.instrument_id = instrument_id or address
        # All transport traffic goes here
        self.logger = logging.getLogger(LogTiers.TRANSPORT)

    @abstractmethod
    def write(self, command: str):
        """Send a string command to the hardware."""
        pass

    @abstractmethod
    def read(self) -> str:
        """Read a string response from the hardware."""
        pass

    @abstractmethod
    def query(self, command: str) -> str:
        """Atomic Write + Read operation."""
        pass

    @abstractmethod
    def close(self):
        """Cleanly release the hardware resource."""
        pass