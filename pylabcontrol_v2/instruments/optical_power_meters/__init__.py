import time
from typing import List, Union, Any
from pint import Quantity
from pylabcontrol_v2.core.base_instrument import BaseInstrument
from pylabcontrol_v2.core.descriptors import MetricParameter, InstrumentParameter

class OPM(BaseInstrument):
    """
    Standardized Category Base for Optical Power Meters (OPM).
    
    Provides a universal interface for Keysight, Thorlabs, Newport, and OptoTest.
    All properties are validated against the instrument's specific TOML limits.
    """

    # --- CORE NOUNS (Tier-2 Descriptors) ---

    power = MetricParameter(
        scpi_get="get_power", 
        unit="W", 
        limits_key=None
    )
    """Current optical power reading. Returns a Pint Quantity in Watts."""

    wavelength = MetricParameter(
        scpi_set="set_wavelength", 
        scpi_get="get_wavelength", 
        unit="nm", 
        limits_key="wavelength"
    )
    """Calibration wavelength for the detector diode."""

    averaging_time = MetricParameter(
        scpi_set="set_averaging_time", 
        scpi_get="get_averaging_time", 
        unit="s", 
        limits_key="averaging_time"
    )
    """Integration time for a single sample (e.g., 100ms)."""

    power_unit = InstrumentParameter(
        scpi_set="set_power_unit", 
        scpi_get="get_get_power_unit", 
        allowed=["W", "DBM", "DB"]
    )
    """Hardware display unit. Note: .power property always returns Watts."""

    auto_range = InstrumentParameter(
        scpi_set="set_auto_range", 
        scpi_get="get_auto_range", 
        allowed=["ON", "OFF", "1", "0"]
    )
    """Toggles hardware auto-ranging."""

    range_level = InstrumentParameter(
        scpi_set="set_range", 
        scpi_get="get_range", 
        allowed=None
    )
    """Manual range/gain setting. Validated against TOML validation.range_modes."""

    # --- CORE VERBS (Methods) ---

    def zero(self, wait: bool = True) -> None:
        """
        Executes dark-current zeroing.
        
        Args:
            wait: If True, blocks until the zeroing routine is complete.
        """
        cmd = self.config.scpi_commands.get("zero", "CAL:ZERO:AUTO ONCE")
        self.log.info(f"[{self.instrument_id}] Zeroing sensor...")
        self.adapter.write(cmd)
        
        if wait:
            # Poll *OPC? or wait for a fixed guard time defined in TOML
            guard_time = self.config.metadata.get("zero_duration", 2.0)
            time.sleep(guard_time)
            self.adapter.query("*OPC?")

    def set_reference(self) -> None:
        """Sets the current power level as the 0dB reference point."""
        cmd = self.config.scpi_commands.get("set_reference", "SENS:POW:REF:STAT ONCE")
        self.adapter.write(cmd)

    def fetch_array(self, count: int) -> List[Quantity]:
        """
        Retrieves a batch of power samples from the hardware buffer.
        
        Args:
            count: Number of samples to retrieve.
            
        Returns:
            List[Quantity]: A list of power readings in Watts.
        """
        cmd_template = self.config.scpi_commands.get("fetch_array", "SENS:DATA?")
        raw_data = self.adapter.query(cmd_template)
        # Concrete drivers should override this to handle vendor-specific binary/ASCII parsing
        return self._parse_buffer(raw_data)

    def _parse_buffer(self, raw_data: str) -> List[Quantity]:
        """Generic ASCII CSV parser for buffered data."""
        parts = raw_data.split(',')
        return [self.validate_level(p.strip(), "W") for p in parts if p.strip()]