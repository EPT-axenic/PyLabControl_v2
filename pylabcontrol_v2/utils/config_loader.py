import toml
import importlib.resources as pkg_resources
from pathlib import Path
from pylabcontrol_v2.core.models import InstrumentConfig

class ConfigLoader:
    """
    V2 ConfigLoader: Dual-Path Resolution.
    1. Checks User Overrides: ~/.pylabcontrol/configs/...
    2. Falls back to Internal Package Data: pylabcontrol_v2/configs/...
    """
    
    # Define the User's local override directory (OS Agnostic: works on Win/Mac/Linux)
    USER_CONFIG_ROOT = Path.home() / ".pylabcontrol" / "configs"

    @staticmethod
    def load_config(category: str, brand: str, model: str) -> InstrumentConfig:
        """
        Loads and validates a TOML config, prioritizing user overrides.
        """
        file_name = f"{model.lower()}.toml"
        category_lower = category.lower()
        brand_lower = brand.lower()

        raw_toml = None
        config_source = ""

        # ---------------------------------------------------------------------
        # PATH 1: USER OVERRIDES (Local File System)
        # ---------------------------------------------------------------------
        user_path = ConfigLoader.USER_CONFIG_ROOT / category_lower / brand_lower / file_name
        
        if user_path.exists():
            raw_toml = user_path.read_text(encoding="utf-8")
            config_source = str(user_path)
            
        # ---------------------------------------------------------------------
        # PATH 2: INTERNAL PACKAGE DATA (pip installed)
        # ---------------------------------------------------------------------
        else:
            try:
                # importlib.resources natively navigates the installed package zip/folder
                resource_path = (pkg_resources.files("pylabcontrol_v2") 
                                 / "configs" 
                                 / category_lower 
                                 / brand_lower 
                                 / file_name)
                
                raw_toml = resource_path.read_text(encoding="utf-8")
                config_source = f"Package Data ({resource_path})"
                
            except FileNotFoundError:
                raise FileNotFoundError(
                    f"Hardware config for {brand} {model} not found in "
                    f"User Overrides ({ConfigLoader.USER_CONFIG_ROOT}) or Internal Package."
                )

        # ---------------------------------------------------------------------
        # HYDRATION & VALIDATION
        # ---------------------------------------------------------------------
        try:
            raw_data = toml.loads(raw_toml)
            # Pydantic hydrates and validates the raw dictionary
            return InstrumentConfig(**raw_data)
        except toml.TomlDecodeError as e:
            raise ValueError(f"TOML Syntax Error in {config_source}: {e}")
        except Exception as e:
            raise ValueError(f"Configuration error for {brand} {model} from {config_source}: {e}")

    @staticmethod
    def format_command(template: str, **kwargs) -> str:
        """Simple helper to fill {val} or {ch} placeholders."""
        try:
            return template.format(**kwargs)
        except KeyError as e:
            raise ValueError(f"Missing expected SCPI parameter: {e}")