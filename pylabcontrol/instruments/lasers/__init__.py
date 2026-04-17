from pylabcontrol.core.base_instrument import BaseInstrument
from pylabcontrol.core.descriptors import MetricParameter, InstrumentParameter

class TLS(BaseInstrument):
    """
    Category Base for Tunable Laser Sources.
    Defines the universal 'Nouns' (Parameters) and 'Verbs' (Methods) 
    that every laser in PyLabControl must implement.
    """
    
    # --- Universal Nouns (Descriptors) ---
    # These use generic limits_keys that every laser TOML must include.
    wavelength = MetricParameter(
        scpi_set="set_wavelength", 
        scpi_get="get_wavelength", 
        unit="nm", 
        limits_key="wavelength"
    )
    
    power = MetricParameter(
        scpi_set="set_power", 
        scpi_get="get_power", 
        unit="dBm", 
        limits_key="power"
    )

    output = InstrumentParameter(
        scpi_set="set_output_status", 
        scpi_get="get_output_status", 
        allowed=["ON", "OFF", "1", "0"]
    )

    # --- Universal Verbs (Methods) ---
    def wait_for_idle(self):
        """Standard blocking call to wait for laser operations to finish."""
        return self.wait() # Uses IEEE 488.2 *WAI from core base