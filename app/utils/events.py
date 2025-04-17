"""
Event system for Aerofly FS4 IGC Recorder.
Implements a Observer pattern to allow communication between components.
"""

from enum import Enum, auto
from typing import Dict, List, Any, Callable, Optional
from dataclasses import dataclass
import logging
import asyncio
import time
import uuid

# Configure logger
logger = logging.getLogger("aerofly_igc_recorder.events")


class EventType(Enum):
    """Enum defining the different types of events in the application"""
    # Connection events
    CONNECTION_ESTABLISHED = auto()
    CONNECTION_LOST = auto()
    DATA_RECEIVED = auto()
    
    # Recording events
    RECORDING_STARTED = auto()
    RECORDING_STOPPED = auto()
    POSITION_ADDED = auto()
    
    # UI events
    UI_INITIALIZED = auto()
    UI_CLOSED = auto()
    
    # System events
    SHUTDOWN_REQUESTED = auto()
    ERROR_OCCURRED = auto()
    
    # Settings events
    SETTINGS_CHANGED = auto()


@dataclass
class Event:
    """Represents an event in the application"""
    type: EventType
    data: Optional[Dict[str, Any]] = None
    source: Optional[str] = None
    timestamp: float = 0.0
    id: str = ""
    
    def __post_init__(self):
        """Initialize event with timestamp and ID if not provided"""
        if not self.timestamp:
            self.timestamp = time.time()
        if not self.id:
            self.id = str(uuid.uuid4())
        if not self.data:
            self.data = {}


class EventBus:
    """
    Centralized event bus that allows components to subscribe to and publish events.
    Implements the Singleton pattern to ensure only one instance exists.
    """
    _instance = None
    
    def __new__(cls):
        if cls._instance is None:
            cls._instance = super(EventBus, cls).__new__(cls)
            cls._instance._initialized = False
        return cls._instance
    
    def __init__(self):
        if self._initialized:
            return
            
        # Dictionary of event subscribers: {EventType: [callbacks]}
        self._subscribers: Dict[EventType, List[Callable[[Event], None]]] = {}
        
        # Event history for debugging (limited size)
        self._event_history: List[Event] = []
        self._max_history_size = 100
        
        # Lock for thread safety
        self._lock = asyncio.Lock()
        
        self._initialized = True
        logger.info("EventBus initialized")
    
    async def subscribe(self, event_type: EventType, callback: Callable[[Event], None]) -> None:
        """
        Subscribe to an event type with a callback function.
        
        Args:
            event_type: The type of event to subscribe to
            callback: Function to call when event occurs
        """
        async with self._lock:
            if event_type not in self._subscribers:
                self._subscribers[event_type] = []
            
            if callback not in self._subscribers[event_type]:
                self._subscribers[event_type].append(callback)
                logger.debug(f"Subscribed to {event_type.name}")
    
    async def unsubscribe(self, event_type: EventType, callback: Callable[[Event], None]) -> bool:
        """
        Unsubscribe from an event type.
        
        Args:
            event_type: The type of event to unsubscribe from
            callback: The callback function to remove
            
        Returns:
            bool: True if successfully unsubscribed, False otherwise
        """
        async with self._lock:
            if event_type in self._subscribers and callback in self._subscribers[event_type]:
                self._subscribers[event_type].remove(callback)
                logger.debug(f"Unsubscribed from {event_type.name}")
                return True
            return False
    
    async def publish(self, event: Event) -> None:
        """
        Publish an event to all subscribers.
        
        Args:
            event: The event to publish
        """
        # Add event to history
        self._add_to_history(event)
        
        # Get subscribers for this event type
        subscribers = []
        async with self._lock:
            if event.type in self._subscribers:
                subscribers = self._subscribers[event.type].copy()
        
        # Notify all subscribers
        if subscribers:
            logger.debug(f"Publishing event {event.type.name} to {len(subscribers)} subscribers")
            for callback in subscribers:
                try:
                    if asyncio.iscoroutinefunction(callback):
                        # Schedule async callbacks without awaiting them
                        asyncio.create_task(callback(event))
                    else:
                        # Call sync callbacks directly
                        callback(event)
                except Exception as e:
                    logger.error(f"Error in event subscriber: {e}")
        else:
            logger.debug(f"No subscribers for event {event.type.name}")
    
    def _add_to_history(self, event: Event) -> None:
        """Add an event to the history, maintaining maximum size"""
        self._event_history.append(event)
        if len(self._event_history) > self._max_history_size:
            self._event_history.pop(0)
    
    def get_event_history(self) -> List[Event]:
        """Get a copy of the event history"""
        return self._event_history.copy()
    
    def clear_history(self) -> None:
        """Clear the event history"""
        self._event_history.clear()


# Create global event bus instance
event_bus = EventBus()


# Helper functions for common event operations
async def publish_event(
    event_type: EventType, 
    data: Optional[Dict[str, Any]] = None, 
    source: Optional[str] = None
) -> Event:
    """
    Helper function to create and publish an event.
    
    Args:
        event_type: The type of event to publish
        data: Optional data to include with the event
        source: Optional source identifier
        
    Returns:
        Event: The published event
    """
    event = Event(type=event_type, data=data, source=source)
    await event_bus.publish(event)
    return event
