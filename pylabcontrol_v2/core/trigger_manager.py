from typing import Union
from pint import Quantity

class TriggerManager:
    """
    Universal Trigger Subsystem.
    Attached to instrument base classes via Composition.
    Handles the IEEE 488.2 standard trigger model (Source, Delay, Count, *TRG).
    """
    def __init__(self, instrument):
        self.instr = instrument
        self.config = instrument.config.get("trigger", {})
        self.scpi = self.config.get("scpi_commands", {})
        self.limits = self.config.get("limits", {})
        self.validation = self.config.get("validation", {})

    def _get_cmd(self, key: str) -> str:
        cmd = self.scpi.get(key)
        if not cmd:
            raise NotImplementedError(
                f"Trigger capability '{key}' is not supported by {self.instr.model}."
            )
        return cmd

    @property
    def source(self) -> str:
        """The trigger source (e.g., IMM, EXT, BUS, TIM)."""
        return self.instr.adapter.query(self._get_cmd("get_source")).strip()

    @source.setter
    def source(self, value: str) -> None:
        allowed = self.validation.get("sources", [])
        state = self.instr.validate_state(value, allowed, context="Trigger Source")
        self.instr.adapter.write(self._get_cmd("set_source").format(value=state))

    @property
    def delay(self) -> Quantity:
        """Wait time between receiving the trigger and executing the action."""
        res = self.instr.adapter.query(self._get_cmd("get_delay"))
        return self.instr.validate_level(float(res), "s", context="Trigger Delay")

    @delay.setter
    def delay(self, value: Union[float, str, Quantity]) -> None:
        qty = self.instr.validate_level(value, "s", context="Trigger Delay")
        self.instr.adapter.write(self._get_cmd("set_delay").format(value=qty.magnitude))

    @property
    def count(self) -> int:
        """Number of triggers to accept before returning to IDLE state."""
        res = self.instr.adapter.query(self._get_cmd("get_count"))
        return int(float(res))

    @count.setter
    def count(self, value: int) -> None:
        val = self.instr.validate_level(value, "", context="Trigger Count")
        self.instr.adapter.write(self._get_cmd("set_count").format(value=int(val.magnitude)))

    def fire(self) -> None:
        """Sends a software trigger over the bus (*TRG)."""
        self.instr.log.info(f"[{self.instr.instrument_id}] Firing software trigger (*TRG)...")
        self.instr.adapter.write(self._get_cmd("fire"))

    def abort(self) -> None:
        """Cancels a pending trigger wait and forces the hardware back to IDLE."""
        self.instr.log.warning(f"[{self.instr.instrument_id}] Aborting trigger sequence!")
        self.instr.adapter.write(self._get_cmd("abort"))