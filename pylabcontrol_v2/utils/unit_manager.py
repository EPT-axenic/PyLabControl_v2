import math
import re
from pint import UnitRegistry, Quantity

class UnitManager:
    def __init__(self):
        # 1. Bring back autoconvert from V1 to make offset units (dBm) play nicely
        self.ureg = UnitRegistry(autoconvert_offset_to_baseunit=True)
        self.ureg.formatter.default_format = ".4f"

    def normalise_unit_input(self, val, target_unit, context="") -> Quantity:
        """
        Robustly converts any input to a Pint Quantity.
        Bypasses Pint's string parser entirely for safe Offset Unit handling.
        """
        try:
            # 1. Already a Quantity? Just convert.
            if isinstance(val, Quantity):
                return val.to(target_unit)

            # 2. Naked number? Wrap it in the target unit.
            if isinstance(val, (int, float)):
                return self.ureg.Quantity(val, target_unit)

            # 3. String Input (The culprit)
            if isinstance(val, str):
                # Regex to cleanly separate "1550.5" and "nm", or "-5.0" and "dBm"
                match = re.match(r"^\s*([+-]?\d+(?:\.\d+)?(?:[eE][+-]?\d+)?)\s*(.*)$", val)
                
                if match:
                    mag_str, unit_str = match.groups()
                    mag = float(mag_str)
                    
                    # If the user provided a unit (e.g., "dBm"), use it
                    if unit_str:
                        # Passing (5.0, 'dBm') explicitly bypasses the math parser!
                        q = self.ureg.Quantity(mag, unit_str)
                    else:
                        # User just passed "5.0", assume target_unit
                        q = self.ureg.Quantity(mag, target_unit)
                        
                    return q.to(target_unit)
                else:
                    # Fallback for weird strings, let Pint try its best
                    parsed = self.ureg(val)
                    if not isinstance(parsed, Quantity):
                        parsed = self.ureg.Quantity(parsed, target_unit)
                    return parsed.to(target_unit)

            raise TypeError(f"Unsupported input type: {type(val)}")

        except Exception as e:
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