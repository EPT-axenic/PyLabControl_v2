from pydantic import BaseModel, Field
from typing import Dict, Any, Optional

class ParameterLimits(BaseModel):
    """
    Defines the physical bounding box for continuous numerical hardware parameters.

    This schema is used exclusively by the `MetricParameter` descriptor to enforce 
    hardware safety limits before values are processed by the transport layer.

    Attributes:
        min (float): The absolute minimum allowable value in the specified base unit.
        max (float): The absolute maximum allowable value in the specified base unit.
        unit (str): The exact physical unit string expected by the hardware (e.g., 'nm', 'dBm').

    Engineering Context:
        Acts as the immutable truth for hardware safety. By strictly defining bounds 
        at the schema level, we prevent catastrophic operator errors (e.g., attempting 
        to push 1000 W to a diode expecting 1000 mW). The `UnitManager` relies on the 
        `unit` attribute here to perform accurate dimensional analysis.
    """
    min: float
    max: float
    unit: str


class InstrumentConfig(BaseModel):
    """
    The master validation schema for PyLabControl V2 TOML configurations.

    Every instrument, whether a standalone device, a topological multiplexer (Chassis), 
    or a proxy driver (Module), must have its static TOML file parsed and validated 
    through this Pydantic model before the framework will instantiate it.

    Attributes:
        brand (str): The vendor or manufacturer identifier (e.g., 'agilent', 'santec').
        model (str): The specific model number of the physical hardware.
        version (str): The internal schema version for backward compatibility tracking.
        scpi_commands (Dict[str, str]): Abstract verb-to-SCPI mappings. Defines the exact 
                                        string templates (which may include kwargs like 
                                        `{slot}`) to be dispatched over the transport bus.
        limits (Dict[str, ParameterLimits]): Maps continuous descriptors (e.g., 'wavelength') 
                                             to their specific numerical safety boundaries.
        validation (Dict[str, Any]): Defines allowable discrete strings/states (e.g., 
                                     `["ON", "OFF", "1", "0"]`) for `InstrumentParameter` descriptors.
        defaults (Dict[str, Any]): Safe initialization states pushed to the instrument upon connection.
        metadata (Optional[Dict[str, Any]]): Topological directives utilized by the core routing 
                                             logic (e.g., `is_mainframe = true`, `max_slots = 4`).

    Engineering Context:
        This model represents the exact border between the static text file and dynamic 
        execution. By forcing TOML files through this strict validation layer, we guarantee 
        that the Tier-3 Logic Core (`BaseInstrument` and `ChassisBase`) will never encounter 
        a missing SCPI template or an undefined limit at runtime. If a user writes a bad 
        TOML, the script crashes here instantly, rather than failing silently halfway through 
        a 10-hour data acquisition sweep.
    """
    brand: str
    model: str
    version: str
    
    scpi_commands: Dict[str, str]
    limits: Dict[str, ParameterLimits]
    validation: Dict[str, Any]
    defaults: Dict[str, Any]
    
    metadata: Optional[Dict[str, Any]] = Field(default_factory=dict)