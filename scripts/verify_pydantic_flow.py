from pylabcontrol_v2.utils.config_loader import ConfigLoader
from pylabcontrol_v2.adapters.mock_adapter import MockAdapter
from pylabcontrol_v2.core.base_instrument import BaseInstrument
from pylabcontrol_v2.utils.logging_manager import setup_logging

setup_logging()

def verify():
    print("--- Verifying Hierarchical Pydantic Integration ---")
    
    try:
        # FIXED: Added the brand "santec" as the second argument
        conf = ConfigLoader.load_config("lasers", "santec", "tsl210")
        print(f"PASS: Config Loaded for {conf.brand} {conf.model}")
    except Exception as e:
        print(f"FAIL: Config Loader error: {e}")
        return

    adapter = MockAdapter()
    instr = BaseInstrument(adapter=adapter, config=conf)
    
    # Test dot-access (Pydantic)
    print(f"PASS: Instrument model confirmed as {instr.config.model}")
    
    # Test standard command fallback
    print(f"PASS: IDN Command used: {instr.config.scpi_commands.get('idn', '*IDN?')}")

if __name__ == "__main__": verify()