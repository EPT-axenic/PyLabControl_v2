import importlib
import logging
from typing import Any, Dict

from pylabcontrol_v2.utils.config_loader import ConfigLoader
from pylabcontrol_v2.adapters.visa_adapter import VISAAdapter
from pylabcontrol_v2.adapters.tcp_adapter import TCPAdapter
from pylabcontrol_v2.adapters.mock_adapter import MockAdapter
from pylabcontrol_v2.core.base_mainframe import ChassisBase
from pylabcontrol_v2.core.base_instrument import BaseInstrument

logger = logging.getLogger("pylabcontrol_v2.factory")

def load_instrument(
    category: str, 
    brand: str, 
    model: str, 
    address: str = "MOCK", 
    **kwargs: Any
) -> BaseInstrument:
    """
    Orchestrates the dynamic instantiation of physical hardware control drivers.

    This factory implements the Tier-3 initialization pipeline. It enforces the 
    separation of physical topology (Adapters) from software intent (Descriptors) 
    by dynamically binding a runtime-selected transport layer to a TOML-defined 
    configuration schema. 

    Args:
        category (str): The functional taxonomy of the instrument (e.g., 'lasers', 'mainframes', 'modules').
        brand (str): The manufacturer string, used for directory traversal (e.g., 'santec', 'agilent').
        model (str): The specific hardware model, corresponding to the TOML filename and target class name (e.g., 'TSL210').
        address (str, optional): The physical transport routing address (e.g., 'GPIB0::20::INSTR', 'TCPIP::192.168.1.5::INSTR'). Defaults to "MOCK".
        **kwargs: Arbitrary keyword arguments passed to the specific instrument constructor.

    Returns:
        BaseInstrument: A fully instantiated, connection-ready driver. This will be a specialized 
        concrete subclass (e.g., `TSL210`), a topological multiplexer (`ChassisBase`), or the 
        generic `BaseInstrument` fallback if no custom logic is required.

    Raises:
        ValueError: If the required TOML configuration cannot be found or parsed.
        ImportError: If a specialized driver file exists but contains syntactical errors.
        
    Engineering Context:
        To maintain an infinitely scalable, hardware-agnostic ecosystem, this factory prioritizes 
        configuration-driven instantiation. If a specialized Python driver file (e.g., `santec.py`) 
        is not found (`ModuleNotFoundError`), the system assumes the instrument is fully abstracted 
        via its TOML and safely falls back to returning a generic `BaseInstrument`.
    """
    
    # 1. Load the Configuration Model first (Hierarchical Schema Validation)
    config = ConfigLoader.load_config(category, brand, model)

    # 2. Transport Layer Abstraction
    address_upper = address.upper()
    if "MOCK" in address_upper:
        adapter = MockAdapter(address)
    elif "::" in address_upper:
        adapter = VISAAdapter(address)
    else:
        adapter = TCPAdapter(address)

    # 3. Topological Routing (The Mainframe Intercept)
    if category.lower() == "mainframes":
        # ChassisBase handles dynamic runtime discovery of its own slots internally
        logger.info(f"Instantiating Mainframe Multiplexer for {brand.upper()} {model.upper()}")
        return ChassisBase(config=config, adapter=adapter, **kwargs)

    # 4. Dynamic Concrete Driver Discovery
    module_path = f"pylabcontrol_v2.instruments.{category.lower()}.{brand.lower()}"
    class_name = model.upper()

    try:
        # Attempt to load a vendor-specific override class (e.g., TSL210)
        module = importlib.import_module(module_path)
        InstrumentClass = getattr(module, class_name)
        logger.debug(f"Vendor-specific class loaded: {class_name} from {module_path}")
        return InstrumentClass(config=config, adapter=adapter, **kwargs)

    except ModuleNotFoundError:
        # ARCHITECTURAL SAFEGUARD: 
        # No vendor-specific file exists. Rely entirely on the TOML + BaseInstrument.
        logger.info(
            f"No specific driver found at {module_path}. "
            f"Falling back to universal BaseInstrument for {brand.upper()} {class_name}."
        )
        return BaseInstrument(config=config, adapter=adapter, **kwargs)
        
    except AttributeError:
        # The file exists, but the specific class name (e.g., TSL210) is missing inside it.
        logger.warning(
            f"Module {module_path} found, but class {class_name} is missing. "
            f"Falling back to universal BaseInstrument."
        )
        return BaseInstrument(config=config, adapter=adapter, **kwargs)
        
    except ImportError as e:
        # CRITICAL FAILURE: The file exists but is broken (syntax error, circular import).
        # We must NOT silently fail back to BaseInstrument here, as the user intended 
        # custom logic to run but it crashed.
        logger.error(f"Critical syntax or import error in {module_path}: {e}")
        raise