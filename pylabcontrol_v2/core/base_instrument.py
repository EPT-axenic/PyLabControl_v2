import logging
from typing import Optional, List, Any
from pylabcontrol_v2.core.models import InstrumentConfig
from pylabcontrol_v2.adapters.base_adapter import BaseAdapter
from pylabcontrol_v2.utils.unit_manager import um

class BaseInstrument:
    """
    Tier 3: The Logic Core.
    Handles the bridge between high-level properties and low-level adapter traffic.
    """
    def __init__(self, config: InstrumentConfig, adapter: BaseAdapter):
        self.config = config
        self.adapter = adapter
        
        # Consistent naming: Use 'self.log' everywhere
        self.log = logging.getLogger(f"pylabcontrol_v2.{self.config.model.lower()}")
        
        # Build the ID once from the config
        self.instrument_id = f"{self.config.brand}_{self.config.model}"

    # --------------------------------------------------------------------------
    # VALIDATIONS (The Bouncers)
    # --------------------------------------------------------------------------

    def validate_state(self, value: Any, allowed_list: List[str], context: str = "") -> str:
        """Validates string states (e.g., 'ON', 'OFF') against TOML or Descriptor lists."""
        val_str = str(value).upper()
        upper_allowed = [str(a).upper() for a in allowed_list]

        if val_str not in upper_allowed:
            self.log.error(f"[{self.instrument_id}] INVALID STATE: '{value}' for {context}")
            raise ValueError(f"Invalid state '{value}' for {context}. Allowed: {allowed_list}")
        
        return val_str

    def validate_level(self, value: Any, target_unit: str, context: Optional[str] = None):
        """Validates numeric levels against TOML limits using Pint."""
        # Normalize input to a Pint Quantity
        qty = um.normalise_unit_input(value, target_unit, context=context)

        # Check limits if they exist in the Pydantic config
        if context and hasattr(self.config.limits, context):
            limit_cfg = getattr(self.config.limits, context)
            val_num = qty.magnitude

            if val_num < limit_cfg.min or val_num > limit_cfg.max:
                self.log.error(f"[{self.instrument_id}] LIMIT BREACH: {qty} is outside {context} range")
                raise ValueError(
                    f"Out of bounds: {qty} for {context}. "
                    f"Range: [{limit_cfg.min}, {limit_cfg.max}] {limit_cfg.unit}"
                )
        return qty

    # --------------------------------------------------------------------------
    # IEEE 488.2 Common Commands (Verbs) - Refactored for Adapter Tier
    # --------------------------------------------------------------------------

    def clear_status(self):
        """*CLS - Clears status byte and error queue."""
        cmd = self.config.scpi_commands.get("clear_status", "*CLS")
        self.adapter.write(cmd)

    def ese(self, data: int):
        """*ESE <data> - Sets bits in standard event status enable register. [cite: 1081]"""
        self.adapter.write(f"*ESE {data}")

    def ese_query(self) -> str:
        """*ESE? - Queries standard event status enable register. [cite: 1083]"""
        return self.adapter.query("*ESE?")

    def esr_query(self) -> str:
        """*ESR? - Queries standard event status register. [cite: 1086]"""
        return self.adapter.query("*ESR?")

    def idn(self) -> str:
        """*IDN? - Queries instrument identification string. [cite: 1089]"""
        cmd = self.config.scpi_commands.get("idn", "*IDN?")
        return self.adapter.query(cmd)

    def opc(self):
        """*OPC - Sets bit 0 in SESR when operations complete. [cite: 1091]"""
        self.adapter.write("*OPC")

    def opc_query(self) -> str:
        """*OPC? - Queries if all operations are complete. [cite: 1093]"""
        return self.adapter.query("*OPC?")

    def opt_query(self) -> str:
        """*OPT? - Queries installed options. [cite: 1095]"""
        return self.adapter.query("*OPT?")

    def psc(self, state: str):
        """*PSC <0|1> - Controls power-on status clear. [cite: 1097]"""
        self.adapter.write(f"*PSC {state}")

    def psc_query(self) -> str:
        """*PSC? - Queries power-on status clear setting. [cite: 1099]"""
        return self.adapter.query("*PSC?")

    def recall(self, filename: str):
        """*RCL - Recalls configuration from file. [cite: 1101]"""
        self.adapter.write(f'*RCL "{filename}"')

    def reset(self):
        """*RST - Resets instrument to factory defaults. [cite: 1103]"""
        cmd = self.config.scpi_commands.get("reset", "*RST")
        self.adapter.write(cmd)

    def save(self, filename: str):
        """*SAV - Saves current configuration to file. [cite: 1105]"""
        self.adapter.write(f'*SAV "{filename}"')

    def sre(self, data: int):
        """*SRE <data> - Sets service request enable register. [cite: 1107]"""
        self.adapter.write(f"*SRE {data}")

    def sre_query(self) -> str:
        """*SRE? - Queries service request enable register. [cite: 1109]"""
        return self.adapter.query("*SRE?")

    def stb_query(self) -> str:
        """*STB? - Queries status byte. [cite: 1111]"""
        return self.adapter.query("*STB?")

    def trigger(self):
        """*TRG - Triggers the instrument. [cite: 1114]"""
        self.adapter.write("*TRG")

    def self_test(self) -> str:
        """*TST? - Runs self-test. [cite: 1116]"""
        return self.adapter.query("*TST?")

    def wait(self):
        """*WAI - Waits for pending commands to complete. [cite: 1119]"""
        self.adapter.write("*WAI")

    def close(self):
        """Cleanly releases adapter resources. [cite: 1021-1023]"""
        self.adapter.close()