import logging
from typing import Any, Optional, List, Union
from pylabcontrol_v2.utils.unit_manager import um, u
from pylabcontrol_v2.utils.logging_manager import LogTiers

# Descriptors operate in the Validation tier to track logic translation
log = logging.getLogger(LogTiers.VALIDATION)

class InstrumentParameter:
    """
    Tier 2: Universal Descriptor for basic Instrument Settings (Nouns).
    Handles mapping between class attributes and raw hardware communication.
    """
    def __init__(self, 
                 scpi_set: Optional[str] = None, 
                 scpi_get: Optional[str] = None, 
                 allowed: Optional[List[str]] = None):
        self.scpi_set = scpi_set
        self.scpi_get = scpi_get
        self.allowed = allowed
        self.name: str = "" 

    def __set_name__(self, owner, name: str):
        self.name = name

    def __get__(self, obj: Any, objtype=None) -> Any:
        if obj is None:
            return self
        
        if not self.scpi_get:
            log.error(f"[{obj.instrument_id}] Attempted to read write-only parameter: {self.name}")
            raise AttributeError(f"Parameter '{self.name}' is write-only.")
        
        raw_val = obj.adapter.query(self.scpi_get)
        log.debug(f"[{obj.instrument_id}] READ {self.name}: raw='{raw_val}'")
        return raw_val

    def __set__(self, obj: Any, value: Any):
        if not self.scpi_set:
            log.error(f"[{obj.instrument_id}] Attempted to write read-only parameter: {self.name}")
            raise AttributeError(f"Parameter '{self.name}' is read-only.")
        
        # Validation using BaseInstrument logic
        if self.allowed:
            value = obj.validate_state(value, self.allowed)
        
        log.info(f"[{obj.instrument_id}] SET {self.name} -> {value}")
        command = f"{self.scpi_set} {value}"
        obj.adapter.write(command)


class MetricParameter(InstrumentParameter):
    """
    Tier 2: Unit-aware Descriptor.
    Refactored to use Pydantic object access for hardware limits.
    """
    def __init__(self, 
                 scpi_set: Optional[str] = None, 
                 scpi_get: Optional[str] = None, 
                 unit: Optional[str] = None, 
                 limits_key: Optional[str] = None):
        super().__init__(scpi_set, scpi_get)
        self.unit = unit
        self.limits_key = limits_key

    def __get__(self, obj: Any, objtype=None) -> Any:
        if obj is None:
            return self
        
        raw_val = super().__get__(obj)
        quantity = um.normalise_unit_input(raw_val, self.unit, context=self.name)
        log.debug(f"[{obj.instrument_id}] DECODE {self.name}: {raw_val} -> {quantity}")
        return quantity

    def __set__(self, obj: Any, value: Union[float, str, Any]):
        # --- NEW STEP C REFACTOR ---
        # Access the limits dictionary directly from the Pydantic config object 
        limits = obj.config.limits.get(self.limits_key)
        
        if not limits:
            log.error(f"[{obj.instrument_id}] No limits defined for '{self.limits_key}' in config.")
            raise ValueError(f"Limit key '{self.limits_key}' is missing from instrument configuration.")

        # Trigger validation using direct attribute access (limits.min / limits.max) 
        try:
            normalized = obj.validate_level(
                value, limits.min, limits.max, self.unit, context=self.name
            )
            
            log.info(f"[{obj.instrument_id}] VALIDATE {self.name}: {value} -> {normalized}")
            
            val_to_send = normalized.magnitude 
            command = f"{self.scpi_set} {val_to_send}"
            obj.adapter.write(command)
            
        except ValueError as e:
            log.error(f"[{obj.instrument_id}] VALIDATION FAILED for {self.name}: {str(e)}")
            raise