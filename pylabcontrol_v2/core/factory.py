import importlib
import logging
from pylabcontrol_v2.utils.config_loader import ConfigLoader
from pylabcontrol_v2.adapters.visa_adapter import VISAAdapter
from pylabcontrol_v2.adapters.tcp_adapter import TCPAdapter
from pylabcontrol_v2.adapters.mock_adapter import MockAdapter

logger = logging.getLogger("pylabcontrol.factory")

def load_instrument(category, brand, model, address, **kwargs):
    """
    Orchestrates the 3-Tier Initialization [cite: 54-55].
    """
    # 1. Load the Configuration Model first (Hierarchical)
    config = ConfigLoader.load_config(category, brand, model)

    # 2. Select Adapter based on address string
    if "MOCK" in address.upper():
        adapter = MockAdapter(address)
    elif "::" in address:
        adapter = VISAAdapter(address)
    else:
        adapter = TCPAdapter(address)

    # 3. Dynamic Driver Discovery
    module_path = f"pylabcontrol.instruments.{category}.{brand.lower()}"
    class_name = model.upper()

    try:
        module = importlib.import_module(module_path)
        InstrumentClass = getattr(module, class_name)
        
        # 4. Inject Config + Adapter into the Instrument 
        return InstrumentClass(adapter=adapter, config=config, **kwargs)

    except (ImportError, AttributeError) as e:
        logger.error(f"Failed to load driver for {brand} {model}: {e}")
        raise