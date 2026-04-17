import functools
import logging
import time
from pylabcontrol.utils.logging_manager import LogTiers

logger = logging.getLogger(LogTiers.ACTION)

def instrument_logger(func):
    @functools.wraps(func)
    def wrapper(self, *args, **kwargs):
        start_time = time.perf_counter()
        try:
            result = func(self, *args, **kwargs)
            duration = (time.perf_counter() - start_time) * 1000
            logger.info(
                f"[{self.instrument_id}] {func.__name__} executed in {duration:.2f}ms",
                extra={"inst_id": self.instrument_id}
            )
            return result
        except Exception as e:
            logger.error(f"[{self.instrument_id}] {func.__name__} FAILED: {str(e)}")
            raise
    return wrapper