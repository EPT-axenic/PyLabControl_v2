from pydantic import BaseModel, Field, field_validator
from typing import Dict, Any, Optional

class ParameterLimits(BaseModel):
    """Schema for numeric limits (e.g. wavelength, power)."""
    min: float
    max: float
    unit: str

class InstrumentConfig(BaseModel):
    """The full schema for a PyLabControl Instrument TOML."""
    brand: str
    model: str
    version: str
    
    # Allows unique SCPI strings for different brands [cite: 43]
    scpi_commands: Dict[str, str]
    
    # Maps parameter names to their numeric boundaries [cite: 51-52]
    limits: Dict[str, ParameterLimits]
    
    # This stores non-numeric validation data like channel lists or state strings 
    validation: Dict[str, Any]
    
    # Default startup states 
    defaults: Dict[str, Any]
    
    # Optional metadata for GUI or unique quirks 
    metadata: Optional[Dict[str, Any]] = {}
