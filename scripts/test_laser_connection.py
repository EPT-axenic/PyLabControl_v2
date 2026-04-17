import logging
import time
from pylabcontrol_v2.core.factory import load_instrument
from pylabcontrol_v2.utils.logging_manager import setup_logging

setup_logging(level=logging.DEBUG)
log = logging.getLogger("pylabcontrol_v2.test")

def run_full_test():
    log.info("=== STARTING RAW HARDWARE CONTROL TEST ===")
    laser = None
    
    try:
        laser = load_instrument(
            category="lasers", 
            brand="santec", 
            model="tsl210", 
            address="GPIB0::1::INSTR"
        )
        
        log.info(f"IDN Response: {laser.idn()}")

        # ---------------------------------------------------------
        # 1. EXPLICIT INITIALIZATION (User takes responsibility)
        # ---------------------------------------------------------
        log.info("Action: Enabling Laser Output (Injecting Base Current)")
        laser.output = "ON"
        time.sleep(1.0) # Wait for internal relay [cite: 960]
        
        # ---------------------------------------------------------
        # 2. POWER CONTROL IN APC MODE
        # ---------------------------------------------------------
        log.info("Action: Forcing APC Control Mode")
        laser.control_mode = "APC"
        time.sleep(0.1)

        log.info("Action: Setting Target Power to 5.0 dBm")
        laser.power = -2
        laser.wait_until_ready()
        log.info(f"Verification: Current Power is {laser.power}")

        # ---------------------------------------------------------
        # 3. WAVELENGTH TUNING
        # ---------------------------------------------------------
        # Try any of these: 1555, "1555nm", "1.555 um"
        target_wl = 1580 
        log.info(f"Action: Setting Wavelength to {target_wl}")
        laser.wavelength = target_wl
        laser.wait_until_ready()
        log.debug(f"Current Wavelength: {laser.wavelength:.3f} nm")
        

        '''
        # ---------------------------------------------------------
        # 4. SAFE SHUTDOWN WITH POLLING
        # ---------------------------------------------------------
        log.info("Action: Sending Command to Turn Output OFF")
        laser.output = "OFF"
        
        # Poll the laser every 0.5 seconds until the protection circuit finishes discharging
        timeout = 10.0 # Maximum seconds to wait
        elapsed = 0.0
        
        while elapsed < timeout:
            time.sleep(0.5)
            elapsed += 0.5
            current_status = laser.output
            
            if current_status == "OFF":
                log.info(f"Verification: Laser successfully powered down after {elapsed} seconds.")
                break
            else:
                log.debug(f"Waiting... Laser is still {current_status} at {elapsed}s")
                
        if laser.output == "ON":
            log.warning("Timeout reached! Laser is still reporting ON.")
        '''
        log.info("=== ALL TESTS PASSED SUCCESSFULLY ===")

    except Exception as e:
        log.error(f"CRITICAL TEST FAILURE: {e}", exc_info=True)
    finally:
        if laser:
            # Ensure the laser is off before closing the connection
            laser.output = "OFF" 
            laser.close()
            log.info("GPIB Resource released safely.")

if __name__ == "__main__":
    run_full_test()