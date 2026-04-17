import os
import toml
from pylabcontrol_v2.core.models import InstrumentConfig

class ConfigLoader:
    """
    V2 ConfigLoader: Navigates a hierarchical config tree.
    Path: configs/{category}/{brand}/{model}.toml
    """
    # Root configs directory
    CONFIG_ROOT = os.path.normpath(
        os.path.join(os.path.dirname(__file__), "..", "..", "configs")
    )

    @staticmethod
    def load_config(category: str, brand: str, model: str) -> InstrumentConfig:
        """
        Loads and validates a TOML config from the brand-specific subfolder.
        """
        # New hierarchical path construction
        config_path = os.path.join(
            ConfigLoader.CONFIG_ROOT, 
            category.lower(), 
            brand.lower(), 
            f"{model.lower()}.toml"
        )

        if not os.path.exists(config_path):
            raise FileNotFoundError(f"Hardware config not found at: {config_path}")

        try:
            raw_data = toml.load(config_path)
            # Pydantic hydrates and validates the raw dictionary [cite: 62]
            return InstrumentConfig(**raw_data)
        except toml.TomlDecodeError as e:
            raise ValueError(f"TOML Syntax Error in {model}: {e}")
        except Exception as e:
            raise ValueError(f"Configuration error for {brand} {model}: {e}")

    @staticmethod
    def format_command(template: str, **kwargs) -> str:
        """Simple helper to fill {val} or {ch} placeholders."""
        try:
            return template.format(**kwargs)
        except KeyError as e:
            raise ValueError(f"Missing expected SCPI parameter: {e}")