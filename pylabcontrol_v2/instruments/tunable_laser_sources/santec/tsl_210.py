import re
import time
from typing import Optional, Union, Any, Dict
from pint import Quantity
from pylabcontrol_v2.instruments.tunable_laser_sources import TLS

class TSL210(TLS):
    """
    Concrete driver for the Santec TSL-210 Tunable Laser Source.

    This class serves as an Explicit Proxy to handle legacy Santec quirks, 
    including mechanical settling times, multi-command power sequences, 
    and non-standard SCPI response formatting[cite: 310]. It implements 
    full-capability support for Fine Tuning, Coherence Control, and 
    hardware status parsing.
    """

    def __init__(self, config: Any, adapter: Any) -> None:
        """
        Initializes the TSL210 driver and applies hardware-specific setup.

        Args:
            config (InstrumentConfig): The validated TOML configuration schema.
            adapter (BaseAdapter): The communication transport layer (VISA, TCP, or Mock).
        """
        super().__init__(config, adapter)
        
        # 1. ADAPTER AGNOSTICISM: Only tweak VISA backends if they exist [cite: 310]
        if hasattr(self.adapter, 'inst'):
            self.adapter.inst.read_termination = '\r\n'
            self.adapter.inst.write_termination = '\r\n'
        
        # Initialize internal hardware state to known standard modes
        self.adapter.write("SU0")
        self.adapter.write("HD0")
        
        # Internal trackers for the polling loop (The "Intent" memory) [cite: 317]
        self._target_wl: Optional[float] = None
        self._target_pwr: Optional[float] = None
        self._target_output: Optional[str] = None

    @property
    def status_report(self) -> Dict[str, Any]:
        """
        Parses the 6-digit 'SU' string into a diagnostic dictionary.

        The format follows the manual specification: [-/none][6][5][4][3][2][1]
        representing state flags like coherence, fine tuning, and errors .

        Returns:
            Dict[str, Any]: A dictionary containing parsed boolean states for 
                'ld_on', 'coherence_on', 'fine_tuning_on', 'acc_mode', 
                'temp_error', and the 'raw_status' string.
        """
        raw = self.adapter.query("SU").strip()
        # Handle the leading '-' for LD ON
        is_on = raw.startswith("-")
        digits = raw.replace("-", "")
        
        # Guard against short strings
        padded = digits.zfill(6)
        
        return {
            "ld_on": is_on,
            "coherence_on": padded[0] == "1",
            "fine_tuning_on": padded[1] == "1",
            "acc_mode": padded[2] == "1",
            "temp_error": padded[3] == "1",
            "raw_status": raw
        }

    # --- Properties with Target Tracking ---

    @property
    def wavelength(self) -> Quantity:
        """
        Queries the current wavelength and returns a normalized Quantity.

        Returns:
            Quantity: The current wavelength as a Pint Quantity in nanometers[cite: 321].
        """
        cmd = self.config.scpi_commands.get("get_wavelength", "WA?")
        res = self.adapter.query(cmd)
        return self.validate_level(self._clean_response(res), "nm", context="wavelength")

    @wavelength.setter
    def wavelength(self, value: Union[float, str, Quantity]) -> None:
        """
        Sets the target wavelength and stashes the intent for polling.

        Note: Setting a new wavelength automatically resets Fine Tuning to 0.

        Args:
            value (Union[float, str, Quantity]): The target wavelength (e.g., 1550, "1550nm").
        """
        qty = self.validate_level(value, "nm", context="wavelength")
        self._target_wl = qty.magnitude 
        
        # SCHEMA INTEGRITY: Fetch the template from the TOML and inject
        cmd_template = self.config.scpi_commands.get("set_wavelength", "WA {value}")
        self.adapter.write(cmd_template.format(value=f"{self._target_wl:.3f}"))

    @property
    def power(self) -> Quantity:
        """
        Queries the current optical power and returns a normalized Quantity.

        Returns:
            Quantity: The current power as a Pint Quantity in dBm[cite: 322].
        """
        cmd = self.config.scpi_commands.get("get_power", "OP?")
        res = self.adapter.query(cmd)
        return self.validate_level(self._clean_response(res), "dBm", context="power")

    @power.setter
    def power(self, value: Union[float, str, Quantity]) -> None:
        """
        Sets the target power using the mandatory Santec 'AF' sequence.

        Args:
            value (Union[float, str, Quantity]): The target power magnitude in dBm.
        """
        qty = self.validate_level(value, "dBm", context="power")
        self._target_pwr = qty.magnitude 
        
        cmd_template = self.config.scpi_commands.get("set_power", "OP {value}")
        self.adapter.write("AF") # Santec specific auto-filter trigger [cite: 317]
        self.adapter.write(cmd_template.format(value=f"{self._target_pwr:.2f}"))

    @property
    def output(self) -> str:
        """
        Queries the laser output status (ON/OFF).

        Returns:
            str: 'ON' if hardware returns a negative status, else 'OFF'[cite: 318].
        """
        cmd = self.config.scpi_commands.get("get_output_status", "SU")
        res = self.adapter.query(cmd).strip()
        return "ON" if res.startswith("-") else "OFF"

    @output.setter
    def output(self, value: str) -> None:
        """
        Sets the laser output state.

        Args:
            value (str): The targeted state ('ON' or 'OFF').
        """
        state = self.validate_state(value, ["ON", "OFF"], context="output")
        self._target_output = state 
        
        # Map human intent to hardware string templates [cite: 318]
        cmd_template = self.config.scpi_commands.get("set_output_status", "L{value}")
        hw_val = "O" if state == "ON" else "F"
        self.adapter.write(cmd_template.format(value=hw_val))

    # --- UNIQUE HARDWARE FUNCTIONS ---

    @property
    def control_mode(self) -> str:
        """
        Queries the current control mode (ACC or APC).

        Returns:
            str: 'ACC' if in constant current mode, else 'APC' (constant power).
        """
        return "ACC" if self.status_report["acc_mode"] else "APC"

    @control_mode.setter
    def control_mode(self, value: str) -> None:
        """
        Toggles between APC and ACC modes.

        Args:
            value (str): The target mode ('APC' or 'ACC').
        """
        mode = self.validate_state(value, ["APC", "ACC"], context="control_mode")
        cmd = self.config.scpi_commands.get("set_acc_mode") if mode == "ACC" else \
              self.config.scpi_commands.get("set_apc_mode")
        self.adapter.write(cmd)

    @property
    def fine_tuning(self) -> float:
        """
        Queries the PZT-based fine tuning offset.

        Returns:
            float: The fine tuning amount in the range [-100, 100].
        """
        res = self.adapter.query(self.config.scpi_commands.get("get_fine_tuning"))
        return float(self._clean_response(res))

    @fine_tuning.setter
    def fine_tuning(self, value: float) -> None:
        """
        Sets the fine tuning offset.

        Args:
            value (float): The target offset value.
        """
        cmd_template = self.config.scpi_commands.get("set_fine_tuning")
        self.adapter.write(cmd_template.format(value=f"{value:.2f}"))

    @property
    def ld_current(self) -> Quantity:
        """
        Queries the current LD injection current.

        Returns:
            Quantity: The current injection current in mA.
        """
        res = self.adapter.query(self.config.scpi_commands.get("get_ld_current"))
        return self.validate_level(self._clean_response(res), "mA", context="ld_current")

    @ld_current.setter
    def ld_current(self, value: Any) -> None:
        """
        Sets the LD injection current directly and forces ACC mode.

        Args:
            value (Union[float, str, Quantity]): The target current value.
        """
        self.control_mode = "ACC"
        qty = self.validate_level(value, "mA", context="ld_current")
        cmd_template = self.config.scpi_commands.get("set_ld_current")
        self.adapter.write(cmd_template.format(value=f"{qty.magnitude:.2f}"))

    @property
    def coherence_control(self) -> bool:
        """
        Queries the coherence control (spectrum broadening) status.

        Returns:
            bool: True if coherence control is active.
        """
        return self.status_report["coherence_on"]

    @coherence_control.setter
    def coherence_control(self, value: bool) -> None:
        """
        Toggles coherence control ON or OFF.

        Args:
            value (bool): The target state.
        """
        cmd = self.config.scpi_commands.get("set_coherence_on") if value else \
              self.config.scpi_commands.get("set_coherence_off")
        self.adapter.write(cmd)

    # --- REFINED HANDSHAKE ---

    def wait_until_ready(self, timeout: float = 20.0) -> bool:
        """
        Polls the hardware until temperature stabilizes and targets are met.

        This handshake monitors both the hardware temperature error bit
        and the discrepancy between set targets and current readings[cite: 311].

        Args:
            timeout (float): Maximum seconds to wait before timing out.

        Returns:
            bool: True if the hardware is stable and at targets, False on timeout.
        """
        start_time = time.time()
        while (time.time() - start_time) < timeout:
            status = self.status_report
            
            # Check 1: Temperature Stability
            if status["temp_error"]:
                time.sleep(0.5)
                continue
            
            # Check 2: Targets (Wavelength/Power/Output) [cite: 311]
            if self._target_wl and abs(self.wavelength.magnitude - self._target_wl) > 0.005:
                time.sleep(0.2)
                continue

            return True
        return False

    def _clean_response(self, raw_res: str) -> str:
        """
        Extracts the numerical magnitude from legacy hardware strings.

        Uses regex to safely preserve scientific notation while stripping 
        alphabetical units or dirty characters[cite: 319].

        Args:
            raw_res (str): The raw response from the hardware.

        Returns:
            str: A numeric string, or "0" if no match is found.
        """
        match = re.search(r'([+-]?\d+(?:\.\d+)?(?:[eE][+-]?\d+)?)', raw_res)
        return match.group(1) if match else "0"