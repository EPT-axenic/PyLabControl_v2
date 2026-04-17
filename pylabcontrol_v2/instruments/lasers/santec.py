import re
from pylabcontrol_v2.instruments.lasers import TLS
from pylabcontrol_v2.utils.unit_manager import u

class TSL210(TLS):
    def __init__(self, config, adapter):
        super().__init__(config, adapter)
        
        # Reaching into your VISAAdapter's 'inst' attribute
        # TSL-210 legacy requires CRLF (\r\n) to process commands correctly
        self.adapter.inst.read_termination = '\r\n'
        self.adapter.inst.write_termination = '\r\n'
        
        # Handshake: Silence headers so we get raw numbers
        self.adapter.write("SU0") # Status off
        self.adapter.write("HD0") # Header off
        
        self.log.info(f"[{self.instrument_id}] TSL-210 Legacy Handshake Complete (CRLF + SU0/HD0)")

    def _clean_response(self, raw_res):
        clean = re.sub(r'[^0-9.\-]', '', raw_res)
        if clean.count('.') > 1:
            return clean.split('.')[-1]
        return clean
    
    # --- Operating Mode (APC vs ACC) ---
    @property
    def control_mode(self):
        """Reads the 4th digit of the SU status string to determine mode."""
        res = self.adapter.query("SU").strip()
        # Ensure the string is long enough to check the 4th digit
        if len(res) >= 5:
            # Format is usually -000000. 4th digit from the right (index 3 if we drop the sign)
            # Manual Pg 65: 4th digit '1' indicates ACC mode. [cite: 1243]
            digits = res.replace("-", "")
            if len(digits) == 6 and digits[2] == '1':
                return "ACC"
        return "APC"

    @control_mode.setter
    def control_mode(self, mode):
        mode = self.validate_state(mode, ["APC", "ACC"], context="control_mode")
        # Manual Pg 62: AO = ACC mode, AF = APC mode [cite: 1176]
        cmd = "AO" if mode == "ACC" else "AF"
        self.adapter.write(cmd)

    @property
    def wavelength(self):
        cmd = self.config.scpi_commands.get("get_wavelength")
        res = self.adapter.query(cmd)
        val = self._clean_response(res)
        return self.validate_level(val, "nm", context="wavelength")

    @wavelength.setter
    def wavelength(self, value):
        qty = self.validate_level(value, "nm", context="wavelength")
        cmd = self.config.scpi_commands.get("set_wavelength")
        self.adapter.write(f"{cmd}{qty.magnitude:.3f}")

    @property
    def power(self):
        cmd = self.config.scpi_commands.get("get_power")
        res = self.adapter.query(cmd)
        val = self._clean_response(res)
        return self.validate_level(val, "dBm", context="power")

    @power.setter
    def power(self, value):
        qty = self.validate_level(value, "dBm", context="power")
        cmd = self.config.scpi_commands.get("set_power")
        # Force APC mode, then send power command with a space
        self.adapter.write("AF") 
        self.adapter.write(f"{cmd} {qty.magnitude:.2f}")

    @property
    def output(self):
        res = self.adapter.query("SU").strip()
        self.log.debug(f"[{self.instrument_id}] Raw SU response: '{res}'")
        return "ON" if res.startswith("-") else "OFF"

    @output.setter
    def output(self, value):
        state = self.validate_state(value, ["ON", "OFF"], context="output")
        cmd = "LO" if state == "ON" else "LF"
        self.adapter.write(cmd)