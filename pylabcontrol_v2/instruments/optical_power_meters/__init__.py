import time
import re
from typing import List, Any
from pint import Quantity
from pylabcontrol_v2.core.base_instrument import BaseInstrument
from pylabcontrol_v2.core.descriptors import MetricParameter, InstrumentParameter

class OPM(BaseInstrument):
    """
    Standardized Category Base for Optical Power Meters (OPM).
    Provides a universal interface via the Data Acquisition Trinity 
    (Read, Initiate, Fetch) and normalizes all readings to Pint Quantities.
    """

    # =========================================================================
    # CORE NOUNS (MetricParameters - Continuous Values)
    # =========================================================================

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
    """Integration time for a single sample."""

    sample_count = MetricParameter(
        scpi_set="set_sample_count",
        scpi_get="get_sample_count",
        unit="",
        limits_key="sample_count"
    )
    """Number of samples to acquire per hardware trigger."""

    correction_factor = MetricParameter(
        scpi_set="set_correction_factor",
        scpi_get="get_correction_factor",
        unit="dB",
        limits_key="correction_factor"
    )
    """Global offset applied to all power readings (e.g., for tap couplers)."""

    # =========================================================================
    # CORE ADJECTIVES (InstrumentParameters - Discrete States)
    # =========================================================================

    power_unit = InstrumentParameter(
        scpi_set="set_power_unit", 
        scpi_get="get_power_unit", 
        allowed=["W", "DBM", "DB"]
    )
    """Hardware display unit. Note: fetch/read methods resolve unit dynamically."""

    auto_range = InstrumentParameter(
        scpi_set="set_auto_range", 
        scpi_get="get_auto_range", 
        allowed=["ON", "OFF", "1", "0"]
    )
    """Toggles hardware auto-ranging."""

    range_level = InstrumentParameter(
        scpi_set="set_range", 
        scpi_get="get_range", 
        allowed=None # Hydrated by TOML 'range_modes'
    )
    """Manual hardware gain/range setting."""

    # =========================================================================
    # EXECUTION VERBS (Data Acquisition Trinity)
    # =========================================================================

    def read(self) -> List[Quantity]:
        """
        Standard blocking measurement.
        Triggers the hardware, waits for completion, and returns the data array.
        """
        cmd = self._get_command("read")
        raw_res = self.adapter.query(cmd)
        return self._parse_buffer(raw_res)

    def initiate(self) -> None:
        """Arms the hardware trigger model for background acquisition."""
        cmd = self._get_command("initiate")
        self.adapter.write(cmd)

    def fetch(self) -> List[Quantity]:
        """Retrieves buffered data from internal memory after an initiate() call."""
        cmd = self._get_command("fetch")
        raw_res = self.adapter.query(cmd)
        return self._parse_buffer(raw_res)

    # =========================================================================
    # HARDWARE ACTIONS
    # =========================================================================

    def zero(self, wait: bool = True) -> None:
        """Executes dark-current zeroing offset."""
        cmd = self._get_command("zero")
        self.log.info(f"[{self.instrument_id}] Zeroing sensor...")
        self.adapter.write(cmd)
        
        if wait:
            guard_time = self.config.metadata.get("zero_duration", 2.0)
            time.sleep(guard_time)
            if self.config.scpi_commands.get("opc_query"):
                self.adapter.query(self.config.scpi_commands.get("opc_query"))

    def set_reference(self) -> None:
        """Sets the current power level as the 0dB relative reference point."""
        cmd = self._get_command("set_reference")
        self.adapter.write(cmd)

    # =========================================================================
    # INTERNAL HELPERS
    # =========================================================================

    def _get_command(self, key: str) -> str:
        cmd = self.config.scpi_commands.get(key)
        if not cmd:
            raise NotImplementedError(f"Hardware capability '{key}' is not defined in TOML.")
        return cmd

    def _parse_buffer(self, raw_data: str) -> List[Quantity]:
        """Parses CSV responses and assigns the current hardware unit."""
        # Query unit directly or assume W/dBm based on current state
        # (Implementation of _get_current_unit left to proxy or basic mapping)
        unit = "W" if "W" in str(self.power_unit).upper() else "dBm"
        parts = raw_data.split(',')
        return [self.validate_level(self._clean_response(p), unit, context="Buffer") 
                for p in parts if p.strip()]

    def _clean_response(self, raw_res: str) -> str:
        match = re.search(r'([+-]?\d+(?:\.\d+)?(?:[eE][+-]?\d+)?)', raw_res)
        if match: return match.group(1)
        raise ValueError(f"Unparseable response: {raw_res}")