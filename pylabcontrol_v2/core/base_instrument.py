import logging
from typing import Optional, List, Any
from pylabcontrol_v2.core.models import InstrumentConfig
from pylabcontrol_v2.adapters.base_adapter import BaseAdapter
from pylabcontrol_v2.utils.unit_manager import um

class BaseInstrument:
    """
    Tier 3: The Logic Core and Universal Base Driver.

    This class serves as the foundational bridge between high-level Pythonic 
    intents (Descriptors/Properties) and low-level physical transport (Adapters). 
    It enforces State-Aware Validation, handles unit normalization, and provides 
    universal access to IEEE 488.2 standard SCPI commands.

    Attributes:
        config (InstrumentConfig): The loaded Pydantic TOML configuration schema.
        adapter (BaseAdapter): The injected transport layer (VISA, TCP, Mock, etc.).
        log (logging.Logger): The dedicated logger instance mapped to this specific model.
        instrument_id (str): A unique string identifier (e.g., "SANTEC_TSL210") for log tracing.

    Engineering Context:
        By forcing every instrument to inherit from this class, we guarantee a 
        Hardware-Agnostic Ecosystem. Whether an instrument is an $80,000 mainframe 
        or a $100 USB generic device, the framework evaluates its limits, logs its 
        actions, and handles its basic IEEE status registers identically.
    """

    def __init__(self, config: InstrumentConfig, adapter: BaseAdapter) -> None:
        """
        Initializes the abstract instrument logic core.

        Args:
            config (InstrumentConfig): The validated TOML configuration dictionary.
            adapter (BaseAdapter): The initialized physical communication bus.
        """
        self.config = config
        self.adapter = adapter
        
        # Consistent naming: Use 'self.log' everywhere for unified routing
        self.log = logging.getLogger(f"pylabcontrol_v2.{self.config.model.lower()}")
        
        # Build the ID once from the config for high-speed logging
        self.instrument_id = f"{self.config.brand.upper()}_{self.config.model.upper()}"

        # The universal coordinate dictionary for Nodal Injection
        self.routing_kwargs = {}

    # --------------------------------------------------------------------------
    # I/O DELEGATION LAYER (The Mutex Gate)
    # --------------------------------------------------------------------------
    # These methods are designed to be overridden by ModuleBase or ChannelBase 
    # to wrap hardware traffic in Mutex locks.

    def write_raw(self, command: str) -> None:
        """
        Final dispatch point for all string commands.
        
        Engineering Context:
            By routing all commands through this method instead of calling 
            self.adapter directly, we allow modular proxies to intercept the 
            call and apply thread-safety locks. [cite: 156, 177]
        """
        self.adapter.write(command)

    def query_raw(self, command: str) -> str:
        """Final dispatch point for all queries."""
        return self.adapter.query(command)

    # --------------------------------------------------------------------------
    # VALIDATIONS (The Bouncers)
    # --------------------------------------------------------------------------

    def validate_state(self, value: Any, allowed_list: List[str], context: str = "") -> str:
        """
        Validates discrete string states against dynamically loaded configuration lists.

        Args:
            value (Any): The target state requested by the user or script.
            allowed_list (List[str]): The enumerated list of acceptable states from the TOML.
            context (str, optional): The name of the parameter being validated (for logging). Defaults to "".

        Returns:
            str: The fully validated, uppercase string representation of the state.

        Raises:
            ValueError: If the requested state does not exist in the allowed_list.

        Engineering Context:
            Acts as a fail-safe firewall. Prevents bad strings (e.g., 'ONN' instead of 'ON') 
            from locking up hardware transport layer queues by catching them in Python first.
        """
        val_str = str(value).upper()
        upper_allowed = [str(a).upper() for a in allowed_list]

        if val_str not in upper_allowed:
            self.log.error(f"[{self.instrument_id}] INVALID STATE: '{value}' for {context}")
            raise ValueError(f"Invalid state '{value}' for {context}. Allowed: {allowed_list}")
        
        return val_str

    def validate_level(self, value: Any, target_unit: str, context: Optional[str] = None) -> Any:
        """
        Validates numeric magnitude against physical hardware limits using the UnitManager.

        Args:
            value (Any): The requested level (can be raw float, formatted string, or Pint Quantity).
            target_unit (str): The physical unit the specific hardware expects.
            context (Optional[str]): The TOML limit block name (e.g., 'wavelength_range').

        Returns:
            Any: A normalized Pint Quantity object mathematically representing the target state.

        Raises:
            ValueError: If the normalized value violates the min/max bounds defined in the TOML.

        Engineering Context:
            This is the core of the framework's physical safety matrix. By evaluating 
            limits against Pint Quantities rather than raw floats, we ensure that a 
            request of '1.55 um' is safely validated against a TOML limit of '1600 nm'.
        """
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

    def clear_status(self) -> None:
        """
        Clears the internal instrument status byte and standard event registers.
        Uses the `*CLS` standard command or overrides defined in the TOML.
        """
        cmd = self.config.scpi_commands.get("clear_status", "*CLS")
        self.write_raw(cmd)

    def ese(self, data: int) -> None:
        """
        Sets the bits in the Standard Event Status Enable Register.

        Args:
            data (int): The decimal representation of the bitmask.
        """
        self.write_raw(f"*ESE {data}")

    def ese_query(self) -> str:
        """
        Queries the current value of the Standard Event Status Enable Register.

        Returns:
            str: The hardware string response representing the decimal bitmask.
        """
        return self.query_raw("*ESE?")

    def esr_query(self) -> str:
        """
        Queries and subsequently clears the Standard Event Status Register.

        Returns:
            str: The decimal representation of the register byte.
        """
        return self.query_raw("*ESR?")

    def idn(self) -> str:
        """
        Queries the unique instrument identification string.

        Returns:
            str: The IDN string containing Manufacturer, Model, Serial, and Firmware details.
        """
        cmd = self.config.scpi_commands.get("idn", "*IDN?")
        return self.query_raw(cmd)

    def opc(self) -> None:
        """
        Sets bit 0 in the Standard Event Status Register when all pending operations complete.
        Crucial for asynchronous hardware synchronization.
        """
        self.write_raw("*OPC")

    def opc_query(self) -> str:
        """
        Halts the execution queue until all pending operations are complete.

        Returns:
            str: "1" when the physical execution queue is successfully cleared.
        """
        return self.query_raw("*OPC?")

    def opt_query(self) -> str:
        """
        Queries the hardware to return all installed hardware/software options.

        Returns:
            str: Comma-separated list of installed modular options.
        """
        return self.query_raw("*OPT?")

    def psc(self, state: str) -> None:
        """
        Controls the Power-on Status Clear flag.

        Args:
            state (str): '0' (Retain registers across reboots) or '1' (Clear upon boot).
        """
        self.write_raw(f"*PSC {state}")

    def psc_query(self) -> str:
        """
        Queries the current Power-on Status Clear setting.

        Returns:
            str: Current integer flag ('0' or '1') as a string.
        """
        return self.query_raw("*PSC?")

    def recall(self, filename: str) -> None:
        """
        Recalls a saved instrument configuration state from the device memory.

        Args:
            filename (str): The specific registry slot or filename on the hardware.
        """
        self.write_raw(f'*RCL "{filename}"')

    def reset(self) -> None:
        """
        Executes a hard reset of the instrument to factory default conditions.
        Fetches the specific reset string (`*RST` by default) from the TOML override.
        """
        cmd = self.config.scpi_commands.get("reset", "*RST")
        self.write_raw(cmd)

    def save(self, filename: str) -> None:
        """
        Saves the current hardware configuration state into the device's volatile memory.

        Args:
            filename (str): The target registry slot or filename.
        """
        self.write_raw(f'*SAV "{filename}"')

    def sre(self, data: int) -> None:
        """
        Sets the Service Request Enable Register bitmask.

        Args:
            data (int): The decimal representation of the target bitmask.
        """
        self.write_raw(f"*SRE {data}")

    def sre_query(self) -> str:
        """
        Queries the Service Request Enable Register configuration.

        Returns:
            str: Decimal representation of the configured bitmask.
        """
        return self.query_raw("*SRE?")

    def stb_query(self) -> str:
        """
        Queries the global Status Byte Register. Useful for polling hardware errors.

        Returns:
            str: Decimal representation of the Status Byte.
        """
        return self.query_raw("*STB?")

    def trigger(self) -> None:
        """
        Forces an immediate hardware trigger execution. Assumes the instrument 
        is pre-armed via its specific acquisition logic.
        """
        self.write_raw("*TRG")

    def self_test(self) -> str:
        """
        Initiates the hardware's internal self-diagnostic routines.

        Returns:
            str: "0" if passed, or an error code indicating hardware failure.
        """
        return self.query_raw("*TST?")

    def wait(self) -> None:
        """
        Halts further SCPI command execution until all pending physical actions 
        (e.g., stage movement, source sweeping) have fully completed.
        """
        self.write_raw("*WAI")

    def close(self) -> None:
        """
        Cleanly closes the transport layer connection and releases system bus resources.
        Must be called prior to script termination to prevent locked sockets/GPIB faults.
        """
        self.adapter.close()