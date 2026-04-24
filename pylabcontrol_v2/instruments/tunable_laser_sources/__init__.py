import time
from typing import Union, Any
from pint import Quantity
from pylabcontrol_v2.core.base_instrument import BaseInstrument
from pylabcontrol_v2.core.descriptors import MetricParameter, InstrumentParameter

class TLS(BaseInstrument):
    """
    Standardized Category Base for Tunable Laser Sources (TLS).
    
    Provides a universal interface for Agilent, Santec, Keysight, and EXFO lasers.
    All continuous properties are mathematically bounded by the TOML limits.
    """

    # --- CORE NOUNS (Tier-2 Descriptors) ---

    wavelength = MetricParameter(
        scpi_set="set_wavelength", 
        scpi_get="get_wavelength", 
        unit="nm", 
        limits_key="wavelength"
    )
    """Target output wavelength. Returns a Pint Quantity in nanometers."""

    power = MetricParameter(
        scpi_set="set_power", 
        scpi_get="get_power", 
        unit="dBm", 
        limits_key="power"
    )
    """Target optical output power. Returns a Pint Quantity (typically dBm or W)."""

    # --- CORE ADJECTIVES (InstrumentParameters) ---

    output = InstrumentParameter(
        scpi_set="set_output_status", 
        scpi_get="get_output_status", 
        allowed=["ON", "OFF", "1", "0"]
    )
    """Master optical shutter or laser diode output state."""

    # --- CORE VERBS (Methods) ---

    def wait_until_ready(self, timeout: float = 20.0) -> bool:
        """
        Generic handshake: Blocks execution until the laser has finished 
        tuning its motors and stabilizing its power control loops.
        
        By default, this relies on the standard IEEE 488.2 *OPC? query.
        Legacy instruments (like the Santec TSL-210) must override this 
        in their concrete proxy class to implement manual polling.
        
        Args:
            timeout (float): Maximum seconds to wait before failing.
            
        Returns:
            bool: True if operation completed, False if it timed out.
        """
        self.log.info(f"[{self.instrument_id}] Waiting for tuning completion...")
        opc_cmd = self.config.scpi_commands.get("opc_query", "*OPC?")
        
        start_time = time.time()
        while (time.time() - start_time) < timeout:
            try:
                # *OPC? typically returns '1' when the hardware queue is empty
                res = self.adapter.query(opc_cmd).strip()
                if "1" in res:
                    self.log.info(f"[{self.instrument_id}] Hardware READY.")
                    return True
            except Exception as e:
                self.log.debug(f"[{self.instrument_id}] OPC query failed: {e}")
                
            time.sleep(0.5)
            
        self.log.warning(f"[{self.instrument_id}] Hardware wait timed out!")
        return False