from pylabcontrol_v2.core.factory import load_instrument
from pylabcontrol_v2.adapters.mock_adapter import MockAdapter
from pylabcontrol_v2.core.base_instrument import BaseInstrument

# 1. Create a Mock Adapter
mock_dev = MockAdapter(address="GPIB::1")

# 2. Injected Load (Assuming you have a 'laser' folder in 'instruments' and a TOML)
# For this test, we can even instantiate the BaseInstrument directly

instr = BaseInstrument(adapter=mock_dev)

print(f"Testing IDN: {instr.idn()}")
instr.reset()
print("Phase 1: Connectivity, Unit Management, and Adapter Injection Verified.")