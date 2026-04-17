import logging
from typing import Any, Optional, List, Union
from pylabcontrol_v2.utils.logging_manager import LogTiers
from pylabcontrol_v2.utils.unit_manager import um

log = logging.getLogger(LogTiers.VALIDATION)

class InstrumentParameter:
    def __init__(self, scpi_set: Optional[str] = None, scpi_get: Optional[str] = None, allowed: Optional[List[str]] = None):
        self.scpi_set = scpi_set
        self.scpi_get = scpi_get
        self.allowed = allowed
        self.name: str = "" 

    def __set_name__(self, owner, name: str):
        self.name = name

    def __get__(self, obj: Any, objtype=None) -> Any:
        if obj is None: return self
        if not self.scpi_get:
            raise AttributeError(f"Parameter '{self.name}' is write-only.")
        
        # Lookup the actual SCPI command from TOML
        cmd = obj.config.scpi_commands.get(self.scpi_get)
        raw_val = obj.adapter.query(cmd)
        log.debug(f"[{obj.instrument_id}] READ {self.name}: {raw_val}")
        return raw_val

    def __set__(self, obj: Any, value: Any):
        if not self.scpi_set:
            raise AttributeError(f"Parameter '{self.name}' is read-only.")
        
        # 1. State Validation (e.g., ON/OFF)
        if self.allowed:
            value = obj.validate_state(value, self.allowed, context=self.name)
        
        # 2. Lookup the SCPI command (e.g., 'set_wavelength' -> 'WA')
        cmd = obj.config.scpi_commands.get(self.scpi_set)
        
        log.info(f"[{obj.instrument_id}] SET {self.name} -> {value}")
        obj.adapter.write(f"{cmd} {value}")


class MetricParameter(InstrumentParameter):
    def __init__(self, scpi_set: Optional[str] = None, scpi_get: Optional[str] = None, 
                 unit: Optional[str] = None, limits_key: Optional[str] = None):
        super().__init__(scpi_set, scpi_get)
        self.unit = unit
        self.limits_key = limits_key

    def __get__(self, obj: Any, objtype=None) -> Any:
        if obj is None: return self
        raw_val = super().__get__(obj)
        # Convert raw string from hardware to Pint Quantity
        return um.normalise_unit_input(raw_val, self.unit, context=self.name)

    def __set__(self, obj: Any, value: Union[float, str, Any]):
        # 1. Delegate validation to the instrument (The Bouncer)
        normalized = obj.validate_level(
            value=value, 
            target_unit=self.unit, 
            context=self.limits_key
        )
        
        # 2. Lookup command and send magnitude
        cmd = obj.config.scpi_commands.get(self.scpi_set)
        val_to_send = normalized.magnitude
        
        log.info(f"[{obj.instrument_id}] VALIDATED {self.name}: {value} -> {normalized}")
        obj.adapter.write(f"{cmd} {val_to_send:.4f}")