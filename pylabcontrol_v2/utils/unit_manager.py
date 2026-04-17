import math
import re
from pint import UnitRegistry, Quantity

import math
import re
from pint import UnitRegistry, Quantity

class UnitManager:
    def __init__(self):
        # autoconvert helps dBm play nicely
        self.ureg = UnitRegistry(autoconvert_offset_to_baseunit=True)
        self.ureg.formatter.default_format = ".4f"

    def normalise_unit_input(self, val, target_unit, context="") -> Quantity:
        """
        Standardizes input into a Pint Quantity and converts to the target unit.
        Supports naked numbers (assumes target_unit) and strings with/without spaces.
        """
        try:
            # Case A: Input is already a Pint Quantity (e.g., from another calculation)
            if isinstance(val, Quantity):
                return val.to(target_unit)

            # Case B: Input is a naked number (int or float)
            # laser.wavelength = 1550 -> becomes 1550 nm
            if isinstance(val, (int, float)):
                return self.ureg.Quantity(val, target_unit)

            # Case C: Input is a string 
            # Supports "1.55 um", "1550nm", "1550", "5.0 dBm"
            if isinstance(val, str):
                # Regex extracts the number part and the unit part separately
                # mag_match handles signs, decimals, and scientific notation
                match = re.match(r"^\s*([+-]?\d+(?:\.\d+)?(?:[eE][+-]?\d+)?)\s*(.*)$", val)
                
                if not match:
                    # Fallback: Let Pint try to parse if regex fails (e.g. "speed_of_light")
                    q = self.ureg.Quantity(val)
                else:
                    mag_str, unit_str = match.groups()
                    mag = float(mag_str)
                    u_str = unit_str.strip()

                    if u_str:
                        # User provided a unit (e.g., "um" or "dBm")
                        # Using the (value, unit) constructor avoids the OffsetUnitCalculusError
                        q = self.ureg.Quantity(mag, u_str)
                    else:
                        # No unit in string (e.g., "1550") -> use the target_unit
                        q = self.ureg.Quantity(mag, target_unit)

                # Final step: Convert to target unit (e.g., um -> nm)
                return q.to(target_unit)

            raise TypeError(f"Unsupported input type {type(val)}")

        except Exception as e:
            # Re-wrap the error with context so the logs show WHICH property failed
            raise ValueError(f"Unit conversion error in {context}: {e}")

    # --- Physical Helpers (The useful parts of your V1) ---

    def freq_to_wave(self, freq_qty: Quantity) -> Quantity:
        """Convert Frequency (Hz) to Wavelength (m)."""
        c = self.ureg.speed_of_light
        return (c / freq_qty).to('nm')

    def dbm_to_mw(self, dbm_val: float) -> Quantity:
        """Standard lab conversion: dBm -> mW."""
        mw_val = 10**(dbm_val / 10)
        return self.ureg.Quantity(mw_val, 'mW')

    def mw_to_dbm(self, mw_qty: Quantity) -> Quantity:
        """Standard lab conversion: mW -> dBm."""
        mag = mw_qty.to('mW').magnitude
        return self.ureg.Quantity(10 * math.log10(mag), 'dBm')

# Global Instance for logic
um = UnitManager()

# Global Alias for the registry (Required by base_instrument.py and others)
u = um.ureg