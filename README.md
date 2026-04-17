# PyLabControl V2: The Bedrock Framework
PyLabControl V2 is a professional-grade lab automation framework designed to decouple high-level instrument logic from low-level hardware communication. By utilizing Python Descriptors, Pydantic models, and a hierarchical configuration system, V2 eliminates boilerplate code and ensures "Hardware Agnostic" automation.


# 🏗 The 3-Tier Architecture

The framework is organized into three distinct layers to ensure that changing a physical connection or swapping a brand requires zero changes to your automation logic.
* **Tier 1: Adapters (The "Pipes")**: Handles raw string transport. Whether you are using GPIB, Ethernet, or a Simulation, the interface remains identical.

* **Tier 2: Descriptors (The "Nouns")**: Handles state management. This layer intercepts property access to perform unit conversion, limit checking, and SCPI mapping.

* **Tier 3: Logic Core (The "Verbs")**: Standardizes instrument behavior. It provides a consistent set of commands for common operations across all supported hardware.


# 📂 Project Structure

```
PyLabControl_v2/
├── configs/                    # Hardware Maps (The "Vocabulary")
│   └── lasers/
│       └── santec/
│           └── tsl210.toml     # Model-specific limits and SCPI strings
├── pylabcontrol/               # Main Library Root
│   ├── adapters/               # Tier 1: Transport Layers
│   ├── core/                   # Tier 2 & 3: The Engine
│   ├── instruments/            # Driver Category Bases and Model Drivers
│   └── utils/                  # Shared Services (Units, Logging, Configs)
├── scripts/                    # Verification and Test Scripts
└── setup.py                    # Package installation for 'pip install -e .
```


# 🛠 Script-by-Script Breakdown

## 1. Core Engine (`pylabcontrol/core/`)
* `models.py`: The **Pydantic Blueprint**. Defines the strict schema for every instrument configuration. It ensures that a TOML file is valid and contains required sections before the hardware is ever contacted.

* `descriptors.py`: The **Parameter Engine**. Uses `InstrumentParameter` and `MetricParameter` to intercept property access. When you set a value, this script handles the validation, unit normalization, and SCPI command generation.

* `base_instrument.py`: The **Logic Parent**. Provides standardized methods for common IEEE 488.2 actions such as querying identification strings, resetting hardware, and clearing status registers.

* `factory.py`: The **Orchestrator**. Dynamically discovers and loads the correct driver, injects the validated TOML config, and attaches the appropriate hardware adapter based on the address string.
    
## 2. Adapters (`pylabcontrol/adapters/`)
* `base_adapter.py`: The Abstract Base Class (ABC) defining the mandatory `write`, `read`, and `query` interface that every transport layer must implement.

* `visa_adapter.py`: Communicates with VISA-compliant instruments (GPIB, USB-TMC, TCPIP::INSTR) using the PyVISA backend.

* `tcp_adapter.py`: Handles raw Ethernet/Socket communication for instruments that do not use the VISA protocol.

* `mock_adapter.py`: A simulation layer that returns pre-defined strings, allowing for software development and testing without physical hardware.
    
## 3. Utilities (`pylabcontrol/utils/`)
* `config_loader.py`: Navigates the hierarchical `configs/` directory to fetch TOML files and "hydrates" them into Pydantic models for the framework.

* `unit_manager.py`: Powered by Pint. Acts as the single source of truth for all dimensional analysis, handling unit conversion and normalization.

* `logging_manager.py`: A hierarchical logging system that categorizes system traffic into Transport, Validation, and Action tiers.

* `decorators.py`: Contains the `instrument_logger` which captures execution time and handles error logging for high-level instrument methods.


# 🚀 How the Code Works:

When you execute `laser.wavelength = "1550nm"` in a script, the following sequence occurs:

1. **Validation**: `MetricParameter.__set__` retrieves the `InstrumentConfig` for the specific device.

2. **Safety Check**: It compares the input against the `min` and `max` values defined in the instrument's TOML file.

3. **Normalization**: The `UnitManager` ensures the value is converted to the instrument's preferred base unit (e.g., nanometers).

4. **Translation**: The descriptor looks up the specific SCPI command for "set_wavelength" in the TOML (e.g., finding `"WA"` for a Santec laser).

5. **Dispatch**: The `Adapter` sends the final formatted string (e.g., `WA 1550.0`) to the physical hardware.


# 🔧 Installation & Usage
## 1. Install as an Editable Package
Navigate to the root directory and run:
```
pip install -e .
```

## 2. Standardized Initialization
```
from pylabcontrol.core.factory import load_instrument

# The Factory handles config loading, adapter selection, and driver injection

laser = load_instrument(
    category="lasers", 
    brand="santec", 
    model="tsl210", 
    address="GPIB0::1::INSTR"
)
```

## 3. Interactive Control
```
# Nouns: Unit-aware property access
laser.wavelength = "1550.5 nm" 
print(laser.wavelength)

# Verbs: Standardized action methods
laser.reset()
```

### Architect's Note: 
This framework is designed to move the complexity of the laboratory into configuration files. If you buy a new laser, you shouldn't have to write new Python code—you should only have to write a new TOML.