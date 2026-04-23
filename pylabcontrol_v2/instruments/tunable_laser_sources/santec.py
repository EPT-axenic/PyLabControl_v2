import re
import time
from pylabcontrol_v2.instruments.tunable_laser_sources import TLS

class TSL210(TLS):
    def __init__(self, config, adapter):
        super().__init__(config, adapter)
        self.adapter.inst.read_termination = '\r\n'
        self.adapter.inst.write_termination = '\r\n'
        
        self.adapter.write("SU0")
        self.adapter.write("HD0")
        
        # Internal trackers for the generic wait method
        self._target_wl = None
        self._target_pwr = None
        self._target_output = None

    def wait_until_ready(self, timeout=15.0, tolerance_nm=0.005, tolerance_db=0.05):
        """
        Generic handshake: Checks all parameters against their last set targets.
        Returns True when settled, False on timeout.
        """
        start_time = time.time()
        self.log.info(f"[{self.instrument_id}] Waiting for hardware to settle...")

        while (time.time() - start_time) < timeout:
            # Check 1: Wavelength (Mechanical)
            if self._target_wl is not None:
                current_wl = self.wavelength.magnitude
                if abs(current_wl - self._target_wl) > tolerance_nm:
                    time.sleep(0.2)
                    continue

            # Check 2: Power (APC Loop)
            if self._target_pwr is not None:
                current_pwr = self.power.magnitude
                if abs(current_pwr - self._target_pwr) > tolerance_db:
                    time.sleep(0.1)
                    continue

            # Check 3: Output (Relay/Protection Circuit)
            if self._target_output is not None:
                if self.output != self._target_output:
                    time.sleep(0.2)
                    continue

            # If we reach here, all set targets are matched
            self.log.info(f"[{self.instrument_id}] Hardware READY.")
            return True

        self.log.warning(f"[{self.instrument_id}] Wait timed out!")
        return False

    # --- Properties with Target Tracking ---

    @property
    def wavelength(self):
        res = self.adapter.query(self.config.scpi_commands.get("get_wavelength"))
        return self.validate_level(self._clean_response(res), "nm", context="wavelength")

    @wavelength.setter
    def wavelength(self, value):
        qty = self.validate_level(value, "nm", context="wavelength")
        self._target_wl = qty.magnitude # Store intent
        self.adapter.write(f"WA {self._target_wl:.3f}")

    @property
    def power(self):
        res = self.adapter.query(self.config.scpi_commands.get("get_power"))
        return self.validate_level(self._clean_response(res), "dBm", context="power")

    @power.setter
    def power(self, value):
        qty = self.validate_level(value, "dBm", context="power")
        self._target_pwr = qty.magnitude # Store intent
        self.adapter.write("AF") 
        self.adapter.write(f"OP {self._target_pwr:.2f}")

    @property
    def output(self):
        res = self.adapter.query("SU").strip()
        return "ON" if res.startswith("-") else "OFF"

    @output.setter
    def output(self, value):
        state = self.validate_state(value, ["ON", "OFF"], context="output")
        self._target_output = state # Store intent
        cmd = "LO" if state == "ON" else "LF"
        self.adapter.write(cmd)

    def _clean_response(self, raw_res):
        clean = re.sub(r'[^0-9.\-]', '', raw_res)
        if clean.count('.') > 1:
            return clean.split('.')[-1]
        return clean