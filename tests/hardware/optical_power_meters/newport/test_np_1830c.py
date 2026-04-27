import pytest
from pint import Quantity
from pylabcontrol_v2.instruments.optical_power_meters.newport.np_1830c import Newport1830C
from tests.hardware.optical_power_meters.test_base_opm import BaseOPMHardwareContract

class TestNewport1830CHardware(BaseOPMHardwareContract):
    """
    Vendor-Specific Certification Suite for the Newport 1830-C.
    Inherits all IEEE 488.2 mandatory tests from BaseOPMHardwareContract,
    but overrides the physical limitations of this legacy hardware.
    """

    # =========================================================================
    # HARDWARE FIXTURE (The Physical Connection)
    # =========================================================================
    
    @pytest.fixture(scope="class")
    def opm_hardware(self):
        """Setup and Teardown for the physical Newport."""
        address = "GPIB0::4::INSTR"
        
        print(f"\n[SETUP] Connecting to physical Newport 1830-C at {address}...")
        
        # ---------------------------------------------------------------------
        # THE V2 FACTORY METHOD
        # ---------------------------------------------------------------------
        from pylabcontrol_v2.core.factory import load_instrument
        
        # The factory automatically loads np_1830c.toml, detects the GPIB address,
        # attaches the VISAAdapter, and returns the specific Newport1830C class!
        opm = load_instrument(
            category="optical_power_meters",
            brand="newport",
            model="np_1830c",
            address=address
        )
        # ---------------------------------------------------------------------
        
        yield opm
        
        print("\n[TEARDOWN] Safely releasing Newport 1830-C...")
        opm.auto_range = "ON"
        opm.power_unit = "W"
        
        # Safely close the transport layer (BaseInstrument has a close() method)
        opm.close()

    # =========================================================================
    # CORE OVERRIDES (Handling Hardware Limitations)
    # =========================================================================

    @pytest.mark.hardware
    def test_core_initiate_and_fetch(self, opm_hardware):
        """
        OVERRIDE: The NP-1830C has no internal RAM for buffering.
        We skip the core certification for this specific feature.
        """
        pytest.skip("Hardware Limitation: NP-1830C does not support INIT/FETC buffering.")

    @pytest.mark.hardware
    def test_core_sample_count(self, opm_hardware):
        """OVERRIDE: Cannot set array buffer sizes on this instrument."""
        pytest.skip("Hardware Limitation: NP-1830C does not support sample counts.")

    @pytest.mark.hardware
    def test_core_averaging_time(self, opm_hardware):
        """
        OVERRIDE: The base test assumes continuous floating-point integration times.
        The Newport uses discrete F1, F2, F3 (Slow, Med, Fast) hardware filters.
        We must test that our Proxy's translation map works correctly.
        """
        # Test "Fast" Mapping (< 0.1s)
        opm_hardware.averaging_time = "10 ms"
        assert opm_hardware.averaging_time.to("s").magnitude == pytest.approx(0.01)
        
        # Test "Medium" Mapping (< 5.0s)
        opm_hardware.averaging_time = "1 s"
        assert opm_hardware.averaging_time.to("s").magnitude == pytest.approx(1.0)
        
        # Test "Slow" Mapping (> 5.0s)
        opm_hardware.averaging_time = "10 s"
        assert opm_hardware.averaging_time.to("s").magnitude == pytest.approx(10.0)

    # =========================================================================
    # PREMIUM SPECIFIC TESTS (The Newport Edge Cases)
    # =========================================================================

    @pytest.mark.hardware
    def test_specific_attenuator_toggle(self, opm_hardware):
        """CERTIFICATION: Proprietary Newport A0/A1 hardware filter toggle."""
        opm_hardware.attenuator_enabled = "ON"
        assert opm_hardware.attenuator_enabled == "ON"
        
        opm_hardware.attenuator_enabled = "OFF"
        assert opm_hardware.attenuator_enabled == "OFF"
        
    @pytest.mark.hardware
    def test_specific_auto_range_fallback(self, opm_hardware):
        """
        CERTIFICATION: The NP-1830C uses R0 for Auto-Range, but has no command 
        to turn it OFF. It must fall back to a manual range (e.g., R4).
        """
        opm_hardware.auto_range = "ON"
        assert opm_hardware.auto_range == "ON"
        
        # Disabling auto-range should trigger the proxy fallback logic
        opm_hardware.auto_range = "OFF"
        assert opm_hardware.auto_range == "OFF"
        
        # Verify it dropped into manual range mode (R1-R8)
        # Note: Depending on light levels, we just check it is not in mode "0" (Auto)
        current_range = opm_hardware.adapter.query("R?").strip()
        assert current_range != "0"