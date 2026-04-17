import logging
import queue
from logging.handlers import QueueHandler

class LogTiers:
    """Standardized tiers for PyLabControl logging."""
    TRANSPORT = "pylabcontrol.transport"   # Raw SCPI/Adapter traffic
    VALIDATION = "pylabcontrol.validation" # Descriptor/Unit logic
    ACTION = "pylabcontrol.action"       # High-level instrument methods

class GUILogHandler(logging.Handler):
    """
    Thread-safe handler that pushes logs into a Queue.
    The GUI will poll this queue to update its display.
    """
    def __init__(self, log_queue: queue.Queue):
        super().__init__()
        self.log_queue = log_queue

    def emit(self, record):
        # We store the record as a dict for easy GUI parsing
        self.log_queue.put({
            "time": self.formatTime(record),
            "level": record.levelname,
            "tier": record.name,
            "msg": record.getMessage(),
            "inst_id": getattr(record, "inst_id", "System")
        })

def setup_logging(level=logging.DEBUG, log_file="pylabcontrol.log"):
    """Initializes the hierarchical logging system."""
    formatter = logging.Formatter('%(asctime)s | %(name)-20s | %(levelname)-8s | %(message)s')
    
    # Root Logger
    root = logging.getLogger("pylabcontrol")
    root.setLevel(level)

    # File Handler
    fh = logging.FileHandler(log_file)
    fh.setFormatter(formatter)
    root.addHandler(fh)

    # Stream Handler (Console)
    sh = logging.StreamHandler()
    sh.setFormatter(formatter)
    root.addHandler(sh)

    return root