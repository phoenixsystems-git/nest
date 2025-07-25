"""
Thread-safe UI update utilities for Nest application.

Provides standardized patterns for updating UI elements from background threads
to ensure consistent behavior across all modules.
"""

import logging
from typing import Callable, Any, Optional

logger = logging.getLogger(__name__)

class ThreadSafeUIUpdater:
    """Utility class for thread-safe UI updates."""
    
    @staticmethod
    def safe_update(widget_or_app, callback: Callable[[], None]) -> None:
        """
        Safely schedule a UI update from a background thread.
        
        Args:
            widget_or_app: Widget or app instance with 'after' method
            callback: Function to execute on main thread
        """
        try:
            if hasattr(widget_or_app, 'after'):
                widget_or_app.after(0, callback)
                return
            
            if hasattr(widget_or_app, 'root') and hasattr(widget_or_app.root, 'after'):
                widget_or_app.root.after(0, callback)
                return
            
            if hasattr(widget_or_app, 'app') and hasattr(widget_or_app.app, 'after'):
                widget_or_app.app.after(0, callback)
                return
            
            logging.warning("No thread-safe update method available, using direct call")
            callback()
            
        except Exception as e:
            logging.error(f"Error scheduling thread-safe UI update: {e}")
            try:
                callback()
            except Exception as e2:
                logging.error(f"Critical UI update failure: {e2}")
    
    @staticmethod
    def safe_progress_update(widget_or_app, progress_var, message_var, 
                           progress_value: Optional[float] = None, 
                           message: Optional[str] = None) -> None:
        """
        Safely update progress indicators from background thread.
        
        Args:
            widget_or_app: Widget or app instance
            progress_var: Progress variable to update
            message_var: Message variable to update
            progress_value: Progress value (0-100)
            message: Status message
        """
        if progress_value is not None:
            progress_value = max(0, min(100, progress_value))
        
        if message is not None and len(str(message)) > 200:
            message = str(message)[:197] + "..."
        
        def update_callback():
            try:
                if progress_var and hasattr(progress_var, 'set') and progress_value is not None:
                    progress_var.set(progress_value)
                if message_var and hasattr(message_var, 'set') and message is not None:
                    message_var.set(str(message))
            except Exception as e:
                logging.error(f"Error updating progress indicators: {e}")
        
        ThreadSafeUIUpdater.safe_update(widget_or_app, update_callback)
