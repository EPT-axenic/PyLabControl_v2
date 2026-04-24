import time
from typing import Union, Any
from pint import Quantity
from pylabcontrol_v2.core.base_instrument import BaseInstrument
from pylabcontrol_v2.core.descriptors import MetricParameter, InstrumentParameter

class SigGen(BaseInstrument):
    """
    Standardized Category Base for RF/Microwave Signal Generators.
    
    Provides a universal interface for Keysight, Anritsu, and Rohde & Schwarz sources.
    All properties are mathematically bounded by the TOML limits and seamlessly 
    support Pint dimensional units (e.g., 'MHz', 'GHz', 'dBm').
    """

    # =========================================================================
    # CORE NOUNS (Tier-2 Descriptors)
    # =========================================================================

    frequency = MetricParameter(
        scpi_set="set_frequency", 
        scpi_get="get_frequency", 
        unit="Hz", 
        limits_key="frequency"
    )
    """Target RF carrier frequency. Returns a Pint Quantity in Hertz."""

    power = MetricParameter(
        scpi_set="set_power", 
        scpi_get="get_power", 
        unit="dBm", 
        limits_key="power"
    )
    """Target RF output power amplitude. Returns a Pint Quantity in dBm."""

    # =========================================================================
    # CORE ADJECTIVES (InstrumentParameters)
    # =========================================================================

    output = InstrumentParameter(
        scpi_set="set_output_status", 
        scpi_get="get_output_status", 
        allowed=["ON", "OFF", "1", "0"]
    )
    """Master RF output amplifier state (ON/OFF)."""

    modulation = InstrumentParameter(
        scpi_set="set_modulation_status", 
        scpi_get="get_modulation_status", 
        allowed=["ON", "OFF", "1", "0"]
    )
    """Master modulation state (enables/disables AM, FM, Phase, or Pulse mod)."""

    # =========================================================================
    # HARDWARE ACTIONS
    # =========================================================================

    def wait_until_ready(self, timeout: float = 20.0) -> bool:
        """
        Generic handshake: Blocks execution until the synthesizer has finished 
        tuning its oscillators and stabilizing power.
        
        Args:
            timeout (float): Maximum seconds to wait before failing.
            
        Returns:
            bool: True if operation completed, False if it timed out.
        """
        self.log.info(f"[{self.instrument_id}] Waiting for PLL lock and settling...")
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