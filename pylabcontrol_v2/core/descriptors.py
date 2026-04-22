import logging
from typing import Any, Optional, List, Union
from pylabcontrol_v2.utils.logging_manager import LogTiers
from pylabcontrol_v2.utils.unit_manager import um

log = logging.getLogger(LogTiers.VALIDATION)

class InstrumentParameter:
    """
    A discrete, state-aware data descriptor for hardware properties.

    This class enforces the Intent-to-Action pipeline for simple hardware 
    states (e.g., ON/OFF, modes, boolean flags). It intercepts attribute 
    assignments, dynamically fetches abstract SCPI templates from the 
    instrument's TOML configuration, and delegates transport to the adapter.

    Attributes:
        scpi_set (Optional[str]): The TOML configuration key for the write command template.
        scpi_get (Optional[str]): The TOML configuration key for the read query template.
        allowed (Optional[List[str]]): A list of valid discrete states allowed for this parameter.
        name (str): The assigned attribute name of the descriptor (populated automatically).

    Engineering Context:
        By utilizing Python's descriptor protocol (`__get__`, `__set__`), we 
        prevent the user from having to call explicit methods (like `.set_output('ON')`).
        Instead, they use natural property assignments (`.output = 'ON'`), while 
        the framework invisibly handles the validation and I/O routing.
    """

    def __init__(
        self, 
        scpi_set: Optional[str] = None, 
        scpi_get: Optional[str] = None, 
        allowed: Optional[List[str]] = None
    ) -> None:
        """
        Initializes the state descriptor.

        Args:
            scpi_set (Optional[str]): TOML key mapping to the setter SCPI command.
            scpi_get (Optional[str]): TOML key mapping to the getter SCPI query.
            allowed (Optional[List[str]]): Enumerated list of valid strings/states.
        """
        self.scpi_set = scpi_set
        self.scpi_get = scpi_get
        self.allowed = allowed
        self.name: str = "" 

    def __set_name__(self, owner: type, name: str) -> None:
        """
        Automatically binds the descriptor instance to its assigned variable name.
        
        Args:
            owner (type): The class owning the descriptor.
            name (str): The variable name used in the class body.
        """
        self.name = name

    def __get__(self, obj: Any, objtype: Optional[type] = None) -> Any:
        """
        Intercepts property retrieval to query the physical hardware state.

        Args:
            obj (Any): The specific instrument instance accessing the parameter.
            objtype (Optional[type]): The class of the instrument.

        Returns:
            Any: The raw string response from the hardware adapter, or the 
                 descriptor instance itself if accessed via the class.

        Raises:
            AttributeError: If the descriptor was instantiated without a `scpi_get` key.
        """
        if obj is None: 
            return self
        
        if not self.scpi_get:
            raise AttributeError(f"Parameter '{self.name}' is write-only.")
        
        # Lookup the actual SCPI command from TOML
        cmd_template = obj.config.scpi_commands.get(self.scpi_get)
        
        # Nodal Injection
        formatted_cmd = cmd_template.format(**obj.routing_kwargs)
        
        raw_val = obj.adapter.query(formatted_cmd)
        log.debug(f"[{obj.instrument_id}] READ {self.name}: {raw_val}")
        return raw_val

    def __set__(self, obj: Any, value: Any) -> None:
        """
        Intercepts property assignment to validate state and command the hardware.

        Args:
            obj (Any): The specific instrument instance.
            value (Any): The intended target state.

        Raises:
            AttributeError: If the descriptor was instantiated without a `scpi_set` key.
            ValueError: If `value` is not found within the `allowed` list.
        """
        if not self.scpi_set:
            raise AttributeError(f"Parameter '{self.name}' is read-only.")
        
        # 1. State Validation (e.g., ON/OFF)
        if self.allowed:
            value = obj.validate_state(value, self.allowed, context=self.name)
        
        # 2. Lookup the SCPI command (e.g., 'set_wavelength' -> 'WA')
        cmd_template = obj.config.scpi_commands.get(self.scpi_set)

        # Nodal Injection
        formatted_cmd = cmd_template.format(value=value, **obj.routing_kwargs)
        
        log.info(f"[{obj.instrument_id}] SET {self.name} -> {value}")
        obj.adapter.write(formatted_cmd)


class MetricParameter(InstrumentParameter):
    """
    A continuous, unit-aware data descriptor for physical hardware limits.

    Inherits from `InstrumentParameter` but enforces strict integration with 
    the framework's `UnitManager`. All transactions flowing through this 
    descriptor must be mathematically bounded and dimensionally normalized 
    (represented as `Pint.Quantity` objects).

    Attributes:
        unit (Optional[str]): The fundamental physical unit the hardware expects (e.g., 'nm', 'dBm').
        limits_key (Optional[str]): The TOML dictionary key defining the physical safety limits.

    Engineering Context:
        Raw numerical floats must never bypass the UnitManager. This class 
        acts as the physical firewall, ensuring that an input of `1550` or 
        `1.55 * u.um` are both safely evaluated, bounded, and converted to 
        the exact string formatting the specific SCPI backend requires.
    """

    def __init__(
        self, 
        scpi_set: Optional[str] = None, 
        scpi_get: Optional[str] = None, 
        unit: Optional[str] = None, 
        limits_key: Optional[str] = None
    ) -> None:
        """
        Initializes the metric descriptor.

        Args:
            scpi_set (Optional[str]): TOML key mapping to the setter SCPI command.
            scpi_get (Optional[str]): TOML key mapping to the getter SCPI query.
            unit (Optional[str]): The baseline physical unit expected by the hardware.
            limits_key (Optional[str]): TOML key for Pydantic limit validations (min/max).
        """
        super().__init__(scpi_set, scpi_get)
        self.unit = unit
        self.limits_key = limits_key

    def __get__(self, obj: Any, objtype: Optional[type] = None) -> Any:
        """
        Intercepts property retrieval, queries hardware, and injects physical units.

        Args:
            obj (Any): The specific instrument instance.
            objtype (Optional[type]): The class of the instrument.

        Returns:
            Any: A fully normalized `Pint.Quantity` object, allowing the user 
                 to instantly perform mathematical operations on the read state.
                 
        Engineering Context:
            Relies on `super().__get__` to handle Nodal Injection (`{slot}`, `{channel}`)
            and thread-safe Mutex querying, before intercepting the raw string response
            to convert it into a Pint Quantity.
        """
        if obj is None: 
            return self
            
        raw_val = super().__get__(obj)
        # Convert raw string from hardware to Pint Quantity
        return um.normalise_unit_input(raw_val, self.unit, context=self.name)

    def __set__(self, obj: Any, value: Union[float, str, Any]) -> None:
        """
        Intercepts assignment, verifies physical limits, formats magnitude, and pushes data.

        Args:
            obj (Any): The specific instrument instance.
            value (Union[float, str, Any]): The intended metric target. Can be a raw float, 
                                            a string (e.g., '1550 nm'), or a Pint Quantity.
                                            
        Raises:
            ValueError: If the normalized value exceeds the hardware bounds 
                        defined in the TOML limits block.
            AttributeError: If the parameter is read-only.
        """
        # 1. Delegate validation to the instrument (The Bouncer)
        normalized = obj.validate_level(
            value=value, 
            target_unit=self.unit, 
            context=self.limits_key
        )
        
        # 2. Fetch the SCPI template
        cmd_template = obj.config.scpi_commands.get(self.scpi_set)
        if not cmd_template:
            raise AttributeError(f"Parameter '{self.name}' is read-only.")
        
        # 3. Format the precision safely before injection
        # Hardcoded to 4 decimal places to prevent buffer overflows on legacy IEEE 488.2 gear
        val_str = f"{normalized.magnitude:.4f}"
        
        # 4. Dynamic Nodal Injection (The Magic)
        # Injects {value}, plus any {slot} or {channel} coordinates this object owns
        formatted_cmd = cmd_template.format(value=val_str, **obj.routing_kwargs)
        
        log.info(f"[{obj.instrument_id}] VALIDATED {self.name}: {value} -> {normalized}")
        
        # 5. Thread-Safe Transport Delegation
        if hasattr(obj, 'write_raw'):
            obj.write_raw(formatted_cmd)
        else:
            obj.adapter.write(formatted_cmd)