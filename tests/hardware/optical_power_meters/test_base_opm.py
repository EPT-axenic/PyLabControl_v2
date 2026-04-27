import pytest
import time
from pint import Quantity

class BaseOPMHardwareContract:
    """
    Universal Certification Contract for Optical Power Meters.
    Guarantees that any concrete OPM fully supports the IEEE 488.2 Core.
    """

    # =========================================================================
    # MEASUREMENT NOUNS (Continuous Physical Properties)
    # =========================================================================

    @pytest.mark.hardware
    def test_core_wavelength(self, opm_hardware):
        """CERTIFICATION: Wavelength parameter mapping and bounds."""
        target = "1310 nm"
        opm_hardware.wavelength = target
        result = opm_hardware.wavelength
        
        assert isinstance(result, Quantity)
        assert result.to("nm").magnitude == pytest.approx(1310.0, rel=1e-3)

    @pytest.mark.hardware
    def test_core_averaging_time(self, opm_hardware):
        """CERTIFICATION: Integration time mapping and unit conversion."""
        target = "100 ms"
        opm_hardware.averaging_time = target
        result = opm_hardware.averaging_time
        
        assert isinstance(result, Quantity)
        assert result.to("s").magnitude == pytest.approx(0.1, rel=1e-3)

    @pytest.mark.hardware
    def test_core_sample_count(self, opm_hardware):
        """CERTIFICATION: Hardware buffer sizing."""
        opm_hardware.sample_count = 10
        assert int(opm_hardware.sample_count) == 10

    # =========================================================================
    # CONFIGURATION ADJECTIVES (Discrete States)
    # =========================================================================

    @pytest.mark.hardware
    def test_core_power_unit(self, opm_hardware):
        """CERTIFICATION: Discrete unit toggling (Linear vs Logarithmic)."""
        opm_hardware.power_unit = "W"
        assert "W" in str(opm_hardware.power_unit).upper()
        
        opm_hardware.power_unit = "dBm"
        assert "DBM" in str(opm_hardware.power_unit).upper()

    @pytest.mark.hardware
    def test_core_auto_range(self, opm_hardware):
        """CERTIFICATION: Auto-range toggle state machine."""
        opm_hardware.auto_range = "ON"
        assert str(opm_hardware.auto_range).upper() in ["ON", "1"]
        
        opm_hardware.auto_range = "OFF"
        assert str(opm_hardware.auto_range).upper() in ["OFF", "0"]

    @pytest.mark.hardware
    def test_core_manual_range(self, opm_hardware):
        """CERTIFICATION: Manual hardware gain staging."""
        # We grab the first valid range from the TOML validation list dynamically
        # because Keysight ranges differ from Thorlabs ranges
        valid_ranges = opm_hardware.config.validation.get("range_modes", [])
        if valid_ranges:
            test_range = valid_ranges[0]
            opm_hardware.range_level = test_range
            assert str(opm_hardware.range_level).upper() == test_range.upper()

    # =========================================================================
    # HARDWARE ACTIONS
    # =========================================================================

    @pytest.mark.hardware
    def test_core_zeroing(self, opm_hardware):
        """CERTIFICATION: Dark-current zeroing routine."""
        try:
            opm_hardware.zero(wait=True)
            success = True
        except Exception as e:
            pytest.fail(f"Hardware zeroing raised an unexpected exception: {e}")
        assert success

    # =========================================================================
    # THE DATA ACQUISITION TRINITY
    # =========================================================================

    @pytest.mark.hardware
    def test_core_read_single(self, opm_hardware):
        """CERTIFICATION: Blocking single-point acquisition."""
        opm_hardware.sample_count = 1
        opm_hardware.power_unit = "dBm"
        
        data = opm_hardware.read()
        
        assert isinstance(data, list)
        assert len(data) == 1
        assert isinstance(data[0], Quantity)
        assert -200 < data[0].magnitude < 50 

    @pytest.mark.hardware
    def test_core_initiate_and_fetch(self, opm_hardware):
        """CERTIFICATION: Non-blocking buffered hardware array acquisition."""
        opm_hardware.sample_count = 5
        opm_hardware.averaging_time = "10 ms"
        
        opm_hardware.initiate()
        time.sleep(0.5)  # Yield thread while hardware acquires
        data = opm_hardware.fetch()
        
        assert isinstance(data, list)
        assert len(data) == 5
        assert isinstance(data[0], Quantity)