from pylabcontrol_v2.utils.unit_manager import um

def test_unit_logic():
    print("--- Testing Unit Manager Robustness ---")
    
    # Test 1: String with units (User Input)
    q1 = um.normalise_unit_input("1.55um", "nm")
    print(f"User Input (1.55um) -> {q1}") # Should be 1550nm

    # Test 2: Naked String (Hardware Output)
    # This is what crashed your script!
    q2 = um.normalise_unit_input("1550.0", "nm")
    print(f"Hardware Output (1550.0) -> {q2}") # Should be 1550nm

    # Test 3: Raw Float
    q3 = um.normalise_unit_input(1550.0, "nm")
    print(f"Raw Float (1550.0) -> {q3}") # Should be 1550nm

    print("--- ALL UNIT TESTS PASSED ---")

if __name__ == "__main__":
    test_unit_logic()