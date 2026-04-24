import re
from typing import List, Any, Union, Tuple
from pint import Quantity
from pylabcontrol_v2.core.base_instrument import BaseInstrument
from pylabcontrol_v2.core.descriptors import InstrumentParameter, MetricParameter

class SMU(BaseInstrument):
    """
    Standardized Category Base for Source Measure Units (SMU).
    
    Features a Dual-State engine to independently route commands 
    based on the active Source Mode and the active Measure Mode.
    Automatically handles compliance inversion (V-source -> I-limit).
    """

    # =========================================================================
    # STATIC CORE DESCRIPTORS
    # =========================================================================

    source_mode = InstrumentParameter(
        scpi_set="set_source_mode", 
        scpi_get="get_source_mode", 
        allowed=None # Hydrated by 'validation.source_modes'
    )
    
    measure_mode = InstrumentParameter(
        scpi_set="set_measure_mode", 
        scpi_get="get_measure_mode", 
        allowed=None # Hydrated by 'validation.measure_modes'
    )

    output = InstrumentParameter(
        scpi_set="set_output_status", 
        scpi_get="get_output_status", 
        allowed=None # Hydrated by 'validation.output_modes'
    )

    sense_mode = InstrumentParameter(
        scpi_set="set_sense_mode", 
        scpi_get="get_sense_mode", 
        allowed=None # Hydrated by 'validation.sense_modes'
    )
    """Toggles 2-wire vs 4-wire remote sensing."""

    sample_count = MetricParameter(
        scpi_set="set_sample_count",
        scpi_get="get_sample_count",
        unit="",
        limits_key="sample_count"
    )

    # =========================================================================
    # SOURCE-AWARE PROPERTIES (Driven by source_mode)
    # =========================================================================

    @property
    def source_level(self) -> Quantity:
        raw_val = self._source_mode_query("get_source_level")
        unit = "V" if "VOLT" in self._get_safe_s_func() else "A"
        return self.validate_level(raw_val, unit, context="source_level")

    @source_level.setter
    def source_level(self, value: Union[float, str, Quantity]) -> None:
        unit = "V" if "VOLT" in self._get_safe_s_func() else "A"
        qty = self.validate_level(value, unit, context="source_level")
        self._source_mode_write("set_source_level", qty.magnitude, "source_level")

    @property
    def source_range(self) -> float:
        return self._source_mode_query("get_source_range")

    @source_range.setter
    def source_range(self, value: Union[float, str]) -> None:
        self._source_mode_write("set_source_range", value, "source_range")

    @property
    def compliance(self) -> Quantity:
        """The safety limit applied to the output (Inverts source unit)."""
        c_func, unit = self._get_compliance_unit_and_func()
        cmd_template = self._get_command("get_compliance")
        res = self.adapter.query(cmd_template.format(c_func=c_func))
        return self.validate_level(self._clean_response(res), unit, context="compliance")

    @compliance.setter
    def compliance(self, value: Union[float, str, Quantity]) -> None:
        c_func, unit = self._get_compliance_unit_and_func()
        qty = self.validate_level(value, unit, context="compliance")
        
        cmd_template = self._get_command("set_compliance")
        self.adapter.write(cmd_template.format(c_func=c_func, value=qty.magnitude))

    # =========================================================================
    # MEASURE-AWARE PROPERTIES (Driven by measure_mode)
    # =========================================================================

    @property
    def measure_range(self) -> float:
        return self._measure_mode_query("get_measure_range")

    @measure_range.setter
    def measure_range(self, value: Union[float, str]) -> None:
        self._measure_mode_write("set_measure_range", value, "measure_range")

    @property
    def nplc(self) -> float:
        return self._measure_mode_query("get_nplc")

    @nplc.setter
    def nplc(self, value: Union[float, str]) -> None:
        self._measure_mode_write("set_nplc", value, "nplc")

    # =========================================================================
    # EXECUTION VERBS (Data Acquisition Trinity)
    # =========================================================================

    def read(self) -> List[Quantity]:
        cmd = self._get_command("read")
        raw_res = self.adapter.query(cmd)
        return self._parse_buffer(raw_res)

    def initiate(self) -> None:
        cmd = self._get_command("initiate")
        self.adapter.write(cmd)

    def fetch(self) -> List[Quantity]:
        cmd = self._get_command("fetch")
        raw_res = self.adapter.query(cmd)
        return self._parse_buffer(raw_res)

    # =========================================================================
    # INTERNAL DUAL-STATE ROUTING HELPERS
    # =========================================================================

    def _source_mode_query(self, cmd_key: str) -> float:
        s_func = self._get_safe_s_func()
        cmd_template = self._get_command(cmd_key)
        res = self.adapter.query(cmd_template.format(s_func=s_func))
        return float(self._clean_response(res))

    def _measure_mode_query(self, cmd_key: str) -> float:
        m_func = self._get_safe_m_func()
        cmd_template = self._get_command(cmd_key)
        res = self.adapter.query(cmd_template.format(m_func=m_func))
        return float(self._clean_response(res))

    def _source_mode_write(self, cmd_key: str, value: Any, param_name: str) -> None:
        s_func = self._get_safe_s_func()
        prefix = f"source_{s_func.lower()}"
        self._gatekeeper_and_inject(cmd_key, s_func, "s_func", prefix, param_name, value)

    def _measure_mode_write(self, cmd_key: str, value: Any, param_name: str) -> None:
        m_func = self._get_safe_m_func()
        prefix = f"measure_{m_func.lower().replace(':', '_')}"
        self._gatekeeper_and_inject(cmd_key, m_func, "m_func", prefix, param_name, value)

    def _gatekeeper_and_inject(self, cmd_key: str, func_val: str, placeholder: str, prefix: str, param_name: str, value: Any) -> None:
        """Universal gatekeeper logic supporting both Source and Measure states."""
        
        # 1. Gatekeeper Fencing
        allowed_params = self.config.validation.get(f"valid_{prefix}_parameters")
        if allowed_params and param_name not in allowed_params:
            raise NotImplementedError(f"'{param_name}' is invalid in {func_val} mode.")

        # 2. Value Fencing
        val_key_specific = f"valid_{prefix}_{param_name}s"
        val_key_generic = f"valid_{param_name}"
        allowed_values = self.config.validation.get(val_key_specific) or self.config.validation.get(val_key_generic)
        
        if allowed_values:
            value = self.validate_state(str(value), allowed_values, context=f"{func_val} {param_name}")

        # 3. Injection
        cmd_template = self._get_command(cmd_key)
        kwargs = {placeholder: func_val, "value": value}
        self.adapter.write(cmd_template.format(**kwargs))

    def _get_compliance_unit_and_func(self) -> Tuple[str, str]:
        """Inverts the active source mode to return the compliance (limit) mode and unit."""
        s_func = self._get_safe_s_func()
        if "VOLT" in s_func:
            return "CURR", "A"
        return "VOLT", "V"

    def _get_safe_s_func(self) -> str:
        return str(self.source_mode).strip('"\'').upper()

    def _get_safe_m_func(self) -> str:
        return str(self.measure_mode).strip('"\'').upper()

    def _get_command(self, key: str) -> str:
        cmd = self.config.scpi_commands.get(key)
        if not cmd:
            raise NotImplementedError(f"Hardware capability '{key}' is missing in TOML.")
        return cmd

    def _parse_buffer(self, raw_data: str) -> List[Quantity]:
        m_func = self._get_safe_m_func()
        unit = "V" if "VOLT" in m_func else "A" if "CURR" in m_func else "ohm"
        
        parts = raw_data.split(',')
        return [self.validate_level(self._clean_response(p), unit) for p in parts if p.strip()]

    def _clean_response(self, raw_res: str) -> str:
        match = re.search(r'([+-]?\d+(?:\.\d+)?(?:[eE][+-]?\d+)?)', raw_res)
        if match: return match.group(1)
        raise ValueError(f"Unparseable response: {raw_res}")