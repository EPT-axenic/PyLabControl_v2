import logging
import time
from pylabcontrol_v2.core.factory import load_instrument
from pylabcontrol_v2.utils.logging_manager import setup_logging, LogTiers

# 1. Initialize hierarchical logging
setup_logging(level=logging.DEBUG)
log = logging.getLogger("pylabcontrol.test")

def run_hardware_test():
    log.info("=== STARTING REAL HARDWARE TEST: SANTEC TSL-210 ===")
    
    try:
        # 2. Load the instrument via Factory
        # This handles: 
        # - Loading configs/lasers/santec/tsl210.toml
        # - Creating VISAAdapter for GPIB0::1::INSTR
        # - Injecting them into the TSL210 class
        laser = load_instrument(
            category="lasers", 
            brand="santec", 
            model="tsl210", 
            address="GPIB0::1::INSTR"
        )

        # 3. Test Basic Connectivity (The "Hello World" of Lab Equipment)
        identity = laser.idn()
        log.info(f"Connected to Device: {identity}")

        # 4. Test MetricParameter (Read and Write)
        # Note: The descriptor handles the unit conversion to 'nm' automatically
        current_wav = laser.wavelength
        log.info(f"Current Wavelength: {current_wav}")

        new_wav = "1550.5 nm"
        log.info(f"Setting wavelength to {new_wav}...")
        laser.wavelength = new_wav
        
        # 5. Test State Control
        log.info("Turning Output ON...")
        laser.output = "ON"
        time.sleep(1)
        log.info(f"Output Status: {laser.output}")
        
        log.info("Turning Output OFF...")
        laser.output = "OFF"

        log.info("=== TEST SUCCESSFUL ===")

    except Exception as e:
        log.error(f"=== TEST FAILED ===\nError: {e}", exc_info=True)
    finally:
        if 'laser' in locals():
            laser.close()

if __name__ == "__main__":
    run_hardware_test()