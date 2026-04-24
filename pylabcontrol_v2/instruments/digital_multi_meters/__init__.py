import re
from typing import List, Any, Union
from pint import Quantity
from pylabcontrol_v2.core.base_instrument import BaseInstrument
from pylabcontrol_v2.core.descriptors import InstrumentParameter, MetricParameter

class DMM(BaseInstrument):
    """
    Standardized Category Base for Digital Multimeters (DMM).
    
    Handles polymorphic parameters (Volts, Amps, Ohms) by dynamically injecting 
    the active measurement function into SCPI templates. It enforces strict 
    Hardware Gatekeeping by validating parameter availability against the TOML.
    """

    # =========================================================================
    # STATIC CORE DESCRIPTORS
    # =========================================================================

    measurement_mode = InstrumentParameter(
        scpi_set="set_function", 
        scpi_get="get_function", 
        allowed=None # Hydrated by 'validation.measurement_modes'
    )
    """The active physical measurement function (e.g., 'VOLT:DC', 'RES')."""

    sample_count = MetricParameter(
        scpi_set="set_sample_count",
        scpi_get="get_sample_count",
        unit="",
        limits_key="sample_count"
    )
    """Number of samples to acquire per trigger initiation."""

    # =========================================================================
    # FUNCTION-AWARE PROPERTIES (Polymorphic)
    # =========================================================================

    @property
    def range_level(self) -> float:
        """Hardware range level for the current measurement mode."""
        return self._function_mode_query("get_range")

    @range_level.setter
    def range_level(self, value: Union[float, str]) -> None:
        self._function_mode_write("set_range", value, "range")

    @property
    def auto_range(self) -> str:
        """Auto-range state for the current measurement mode (ON/OFF)."""
        res = self._function_mode_query("get_range_auto")
        return "ON" if "1" in str(res) else "OFF"

    @auto_range.setter
    def auto_range(self, value: str) -> None:
        self._function_mode_write("set_range_auto", self._bool_str(value), "range_auto")

    @property
    def nplc(self) -> float:
        """Number of Power Line Cycles (integration time)."""
        return self._function_mode_query("get_nplc")

    @nplc.setter
    def nplc(self, value: Union[float, str]) -> None:
        self._function_mode_write("set_nplc", value, "nplc")

    @property
    def resolution(self) -> float:
        """Measurement resolution for the current mode."""
        return self._function_mode_query("get_resolution")

    @resolution.setter
    def resolution(self, value: Union[float, str]) -> None:
        self._function_mode_write("set_resolution", value, "resolution")

    @property
    def zero_auto(self) -> str:
        """Auto-Zero configuration (ON/OFF) for offset compensation."""
        res = self._function_mode_query("get_zero_auto")
        return "ON" if "1" in str(res) else "OFF"

    @zero_auto.setter
    def zero_auto(self, value: str) -> None:
        self._function_mode_write("set_zero_auto", self._bool_str(value), "zero_auto")

    @property
    def terminals(self) -> str:
        """Queries the active physical routing terminals (e.g., FRON or REAR)."""
        cmd = self._get_command("get_terminals")
        return self.adapter.query(cmd).strip()

    # =========================================================================
    # EXECUTION VERBS
    # =========================================================================

    def read(self) -> List[Quantity]:
        """
        Standard blocking measurement.
        Triggers the hardware, waits for completion, and returns the data.
        Respects the current configuration (NPLC, Range, Sample Count).
        
        Returns:
            List[Quantity]: A list of measurements. If sample_count == 1, 
                            returns a list containing a single Quantity.
        """
        cmd = self._get_command("read")
        raw_res = self.adapter.query(cmd)
        return self._parse_buffer(raw_res)

    def initiate(self) -> None:
        """
        Arms the hardware trigger model for background acquisition.
        Non-blocking. Data must be retrieved later using fetch().
        """
        cmd = self._get_command("initiate")
        self.adapter.write(cmd)

    def fetch(self) -> List[Quantity]:
        """
        Retrieves buffered data from internal memory after an initiate() call.
        Does NOT trigger a new measurement.
        
        Returns:
            List[Quantity]: A list of buffered measurements.
        """
        cmd = self._get_command("fetch")
        raw_res = self.adapter.query(cmd)
        return self._parse_buffer(raw_res)

    def _parse_buffer(self, raw_data: str) -> List[Quantity]:
        """Helper to split CSV responses and apply the correct physical unit."""
        unit = self._resolve_current_unit()
        parts = raw_data.split(',')
        return [self.validate_level(self._clean_response(p), unit, context="Data Buffer") 
                for p in parts if p.strip()]

    # =========================================================================
    # INTERNAL CONTEXT-AWARE ROUTING HELPERS
    # =========================================================================

    def _function_mode_query(self, cmd_key: str) -> float:
        """Helper to safely query a command bound to the active measurement function."""
        func = self._get_safe_func()
        cmd_template = self._get_command(cmd_key)
        res = self.adapter.query(cmd_template.format(func=func))
        return float(self._clean_response(res))

    def _function_mode_write(self, cmd_key: str, value: Any, param_name: str) -> None:
        """
        Safely injects commands based on the active measurement mode.
        Acts as a Gatekeeper to prevent invalid parameters for the current mode.
        """
        func = self._get_safe_func() # e.g., "VOLT:DC"
        prefix = func.lower().replace(':', '_') # e.g., "volt_dc"
        
        # 1. THE GATEKEEPER: Is this parameter physically supported in this mode?
        allowed_params_key = f"valid_{prefix}_parameters"
        allowed_params = self.config.validation.get(allowed_params_key)
        
        if allowed_params and param_name not in allowed_params:
            self.log.error(f"[{self.instrument_id}] '{param_name}' is invalid in {func} mode.")
            raise NotImplementedError(
                f"The {self.config.model} does not support setting '{param_name}' "
                f"while in '{func}' measurement mode."
            )

        # 2. THE VALIDATOR: Is the numerical/string value safe?
        # Tries specific array first (e.g., valid_volt_dc_ranges), falls back to generic (e.g., valid_nplc)
        val_key_specific = f"valid_{prefix}_{param_name}s"
        val_key_generic = f"valid_{param_name}"
        
        allowed_values = self.config.validation.get(val_key_specific) or self.config.validation.get(val_key_generic)
        
        if allowed_values:
            value = self.validate_state(str(value), allowed_values, context=f"{func} {param_name}")
            
        # 3. THE INJECTOR: Send to hardware
        cmd_template = self._get_command(cmd_key)
        self.adapter.write(cmd_template.format(func=func, value=value))

    def _get_command(self, key: str) -> str:
        cmd = self.config.scpi_commands.get(key)
        if not cmd:
            raise NotImplementedError(f"Hardware capability '{key}' is not defined in TOML.")
        return cmd

    def _get_safe_func(self) -> str:
        """Retrieves active mode and strips surrounding quotes if present."""
        return str(self.measurement_mode).strip('"\'')

    def _bool_str(self, value: str) -> str:
        """Converts human ON/OFF intents to hardware 1/0 strings."""
        state = self.validate_state(str(value), ["ON", "OFF", "1", "0"], context="Boolean")
        return "1" if state in ["ON", "1"] else "0"

    def _resolve_current_unit(self) -> str:
        mode = self._get_safe_func().upper()
        if "VOLT" in mode: return "V"
        if "CURR" in mode: return "A"
        if "RES" in mode:  return "ohm"
        if "CAP" in mode:  return "F"
        if "FREQ" in mode: return "Hz"
        return ""

    def _clean_response(self, raw_res: str) -> str:
        match = re.search(r'([+-]?\d+(?:\.\d+)?(?:[eE][+-]?\d+)?)', raw_res)
        if match: return match.group(1)
        raise ValueError(f"Unparseable response: {raw_res}")