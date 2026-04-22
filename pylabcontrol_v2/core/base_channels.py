from typing import Any, Dict, TYPE_CHECKING
from pylabcontrol_v2.core.base_instrument import BaseInstrument

if TYPE_CHECKING:
    from pylabcontrol_v2.core.base_instrument import BaseInstrument

class ChannelBase(BaseInstrument):
    """
    Proxy driver representing a discrete physical channel of a hardware device.

    This class provides a unit-aware, descriptor-driven interface for sub-components 
    (channels) of a larger hardware device[cite: 200]. It inherits the parent's 
    configuration and adapter while appending its specific channel coordinate to 
    the routing path for Nodal Injection[cite: 151, 166].

    Attributes:
        channel_id (Any): The identifier for this channel (e.g., 1, 2, or 'A', 'B').
        _parent (BaseInstrument): The hardware device or module that owns this channel.
        routing_kwargs (Dict[str, Any]): Topological coordinates for SCPI formatting.

    Engineering Context:
        Channels are implemented as "Transparent Proxies." They do not maintain 
        their own I/O locks or adapters[cite: 154]. Instead, they delegate all 
        raw transport requests to their parent. This recursion ensures that if 
         a channel is part of a mainframe module, its I/O is automatically 
        wrapped in the chassis-level Mutex lock[cite: 175]. If it is a channel 
        of a standalone instrument, it bypasses unnecessary locking for 
        maximum performance[cite: 156].
    """
    
    def __init__(self, parent: 'BaseInstrument', channel_id: Any) -> None:
        """
        Initializes the channel proxy and merges topological coordinates.

        Args:
            parent (BaseInstrument): The parent instrument or module owning this channel.
            channel_id (Any): The physical channel identifier (numeric or string).
        """
        self._parent = parent
        self.channel_id = channel_id
        
        # Inherit the validated config and adapter from the parent [cite: 91, 92]
        super().__init__(adapter=self._parent.adapter, config=self._parent.config)
        
        # RECURSIVE ROUTING: Merge this channel ID with the parent's existing coordinates.
        # This handles Slot -> Channel and Standalone -> Channel mapping automatically.
        self.routing_kwargs = {**self._parent.routing_kwargs, "channel": self.channel_id}

    def write_raw(self, command: str) -> None:
        """
        Delegates raw transmission to the parent to maintain the I/O chain.
        
        Args:
            command (str): The fully formatted SCPI string.

        Engineering Context:
            By calling the parent's raw method rather than the adapter directly, 
            we ensure that any thread-safety logic (Mutex locks) defined in the 
            parent or grandparent is respected[cite: 156, 175].
        """
        if hasattr(self._parent, 'write_raw'):
            self._parent.write_raw(command)
        else:
            # Fallback to direct adapter if parent is a primitive BaseInstrument
            self.adapter.write(command)

    def query_raw(self, command: str) -> str:
        """
        Delegates atomic query to the parent to maintain the I/O chain.

        Args:
            command (str): The SCPI query string.

        Returns:
            str: The raw hardware response.
        """
        if hasattr(self._parent, 'query_raw'):
            return self._parent.query_raw(command)
        return self.adapter.query(command)