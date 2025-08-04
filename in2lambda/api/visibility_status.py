from enum import Enum

class VisibilityStatus(Enum):
    """Enum representing the visibility status of a question or set."""
    OPEN = "OPEN"
    HIDE = "HIDE"
    OPEN_WITH_WARNINGS = "OPEN_WITH_WARNINGS"

    def __str__(self):
        return self.value
    
class VisibilityController:
    """Controller for managing visibility status with easy-to-use methods."""
    
    def __init__(self, initial_status: VisibilityStatus = VisibilityStatus.OPEN):
        self._status = initial_status
    
    @property
    def status(self) -> VisibilityStatus:
        return self._status
    
    def to_open(self):
        """Change status to OPEN."""
        self._status = VisibilityStatus.OPEN
        return self
    
    def to_hide(self):
        """Change status to HIDE."""
        self._status = VisibilityStatus.HIDE
        return self
    
    def to_open_with_warnings(self):
        """Change status to OPEN_WITH_WARNINGS."""
        self._status = VisibilityStatus.OPEN_WITH_WARNINGS
        return self
    
    def __str__(self):
        return str(self._status)