from pylabcontrol.instruments.lasers import TLS

class TSL210(TLS):
    """Santec TSL-210 Tunable Laser Driver."""
    brand = "Santec"
    model = "TSL210"
    
    # Standard IEEE 488.2 commands and TLS descriptors 
    # are automatically handled by the base classes and TOML.