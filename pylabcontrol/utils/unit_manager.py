import pint
from typing import Union

class UnitManager:
    """
    The Single Source of Truth for all dimensional analysis.
    Wraps the 'pint' library for PyLabControl.
    """
    def __init__(self):
        self.u = pint.UnitRegistry()
        # Define common lab aliases if needed
        self.u.define('micro_watt = 1e-6 * watt = uW')
        self.u.define('nano_meter = 1e-9 * meter = nm')

    def normalise_unit_input(self, value: Union[float, int, str, pint.Quantity], 
                             target_unit: str, context: str = "") -> pint.Quantity:
        """
        Converts any input (string with unit, float, or Quantity) 
        into a standardized pint.Quantity in the target unit.
        """
        try:
            if isinstance(value, (int, float)):
                # Assume raw numbers are already in target units if not specified
                quantity = value * self.u(target_unit)
            elif isinstance(value, str):
                quantity = self.u(value)
            else:
                quantity = value

            # Convert to target unit (e.g., from '1550nm' to '1.55um' if requested)
            return quantity.to(target_unit)
        
        except Exception as e:
            raise ValueError(f"Unit conversion error in {context}: {e}")

# Global singleton instances
um = UnitManager()
u = um.u