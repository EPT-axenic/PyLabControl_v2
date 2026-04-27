from typing import List, Union
from pint import Quantity
from pylabcontrol_v2.instruments.optical_power_meters import OPM

class Newport1830C(OPM):
    """
    Concrete driver for the legacy Newport 1830C Power Meter.
    Translates PyLabControl V2's continuous physics vocabulary into 
    the discrete integer mapping required by the hardware.
    """

    # =========================================================================
    # PROPERTY INTERCEPTORS (The Translation Layer)
    # =========================================================================

    @property
    def power_unit(self) -> str:
        res = self.adapter.query(self._get_command("get_power_unit")).strip()
        # Hardware Map: 1=Watts, 2=dB, 3=dBm
        mapping = {"1": "W", "2": "DB", "3": "DBM"}
        return mapping.get(res, "W")

    @power_unit.setter
    def power_unit(self, value: str) -> None:
        state = self.validate_state(str(value).upper(), ["W", "DBM", "DB"], context="Power Unit")
        mapping = {"W": "1", "DB": "2", "DBM": "3"}
        self.adapter.write(self._get_command("set_power_unit").format(value=mapping[state]))

    @property
    def averaging_time(self) -> Quantity:
        res = self.adapter.query(self._get_command("get_averaging_time")).strip()
        # Hardware Map: 1=Slow, 2=Medium, 3=Fast. Map to estimated physics seconds.
        mapping = {"1": 10.0, "2": 1.0, "3": 0.01}
        return self.validate_level(mapping.get(res, 1.0), "s", context="Averaging Time")

    @averaging_time.setter
    def averaging_time(self, value: Union[float, str, Quantity]) -> None:
        qty = self.validate_level(value, "s", context="Averaging Time")
        # Invert the mapping: closest physical time to discrete hardware state
        if qty.magnitude < 0.1:
            val = "3" # Fast
        elif qty.magnitude < 5.0:
            val = "2" # Medium
        else:
            val = "1" # Slow
            
        self.adapter.write(self._get_command("set_averaging_time").format(value=val))

    @property
    def auto_range(self) -> str:
        """The 1830C uses Range '0' for Auto."""
        res = self.adapter.query(self._get_command("get_range")).strip()
        return "ON" if res == "0" else "OFF"

    @auto_range.setter
    def auto_range(self, value: str) -> None:
        state = self.validate_state(str(value), ["ON", "OFF", "1", "0"], context="Auto Range")
        if state in ["ON", "1"]:
            self.adapter.write("R0")
        else:
            # Revert to a safe, middle manual range if disabled
            self.adapter.write("R4")

    # =========================================================================
    # EXECUTION OVERRIDES (Handling Missing Capabilities)
    # =========================================================================

    def initiate(self) -> None:
        """The 1830C has no internal data buffer or standard trigger model."""
        self.log.warning(f"[{self.instrument_id}] Hardware buffering not supported by 1830C.")
        # Fails gracefully without throwing an error

    def fetch(self) -> List[Quantity]:
        """Degrades gracefully to a standard single-point read."""
        self.log.warning(f"[{self.instrument_id}] Fetch degrades to single Read on 1830C.")
        return self.read()