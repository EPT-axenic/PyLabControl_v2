import logging
import sys
import queue
from typing import Optional

class LogTiers:
    """Standardized tiers for PyLabControl V2 logging."""
    # Ensure these match your package name exactly
    TRANSPORT = "pylabcontrol_v2.transport"   # Raw SCPI/Adapter traffic
    VALIDATION = "pylabcontrol_v2.validation" # Descriptor/Unit logic
    ACTION = "pylabcontrol_v2.action"         # High-level instrument methods

class GUILogHandler(logging.Handler):
    """
    Thread-safe handler that pushes logs into a Queue.
    The GUI polls this queue to update its display.
    """
    def __init__(self, log_queue: queue.Queue):
        super().__init__()
        self.log_queue = log_queue

    def emit(self, record):
        try:
            # Format the message using the attached formatter
            msg = self.format(record)
            self.log_queue.put({
                "time": record.created,
                "level": record.levelname,
                "tier": record.name,
                "msg": record.getMessage(),
                "formatted": msg,
                "inst_id": getattr(record, "inst_id", "System")
            })
        except Exception:
            self.handleError(record)

def setup_logging(level=logging.DEBUG, log_file="pylabcontrol_v2.log", log_queue: Optional[queue.Queue] = None):
    """Initializes the hierarchical logging system for the v2 namespace."""
    
    # 1. Get the TOP LEVEL logger for the framework
    # Any log sent to "pylabcontrol_v2.anything" will flow through this
    framework_log = logging.getLogger("pylabcontrol_v2")
    framework_log.setLevel(level)
    
    # Clear existing handlers to prevent duplicate lines in VS Code
    if framework_log.hasHandlers():
        framework_log.handlers.clear()

    # 2. Formatter: Time | Context (Tier) | Level | Message
    formatter = logging.Formatter('%(asctime)s | %(name)-25s | %(levelname)-8s | %(message)s', 
                                  datefmt='%H:%M:%S')

    # 3. Stream Handler (The "Terminal" Pipe)
    sh = logging.StreamHandler(sys.stdout)
    sh.setFormatter(formatter)
    framework_log.addHandler(sh)

    # 4. File Handler (The "Black Box" Record)
    fh = logging.FileHandler(log_file)
    fh.setFormatter(formatter)
    framework_log.addHandler(fh)

    # 5. Optional GUI Handler (The "Screen" Pipe)
    if log_queue is not None:
        gh = GUILogHandler(log_queue)
        gh.setFormatter(formatter)
        framework_log.addHandler(gh)

    framework_log.info(f"V2 Logging Initialized at level {logging.getLevelName(level)}")
    return framework_log