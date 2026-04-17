import pyvisa as visa
from ..adapters.base_adapter import BaseAdapter
from pylabcontrol_v2.core.models import InstrumentConfig
from ..utils.unit_manager import um, u


class BaseInstrument:
    """
    Tier 3: The Logic Core. 
    Refactored to support Adapter Injection while maintaining full 
    validation and IEEE 488.2 command sets. 
    """
    def __init__(self, adapter: BaseAdapter, config: InstrumentConfig, logger=None, instrument_id=None):
        self.adapter = adapter
        self.config = config
        self.logger = logger
        self.um = um  # Shared unit manager

        # Build standardized ID and sync with adapter for shared context
        self.instrument_id = instrument_id or self.build_instrument_id()
        self.adapter.instrument_id = self.instrument_id

    def build_instrument_id(self):
        """Constructs a standard ID: <brand>_<model>_<class_name>"""
        brand = getattr(self, "brand", "UnknownBrand")
        model = getattr(self, "model", "UnknownModel")
        class_name = self.__class__.__name__
        return f"{brand}_{model}_{class_name}"

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