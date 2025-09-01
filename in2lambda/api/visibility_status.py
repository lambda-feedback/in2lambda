from enum import Enum


class VisibilityStatus(Enum):
    """Enum representing the visibility status of a question or set."""

    OPEN = "OPEN"
    HIDE = "HIDE"
    OPEN_WITH_WARNINGS = "OPEN_WITH_WARNINGS"

    def __str__(self):
        """Return the string representation of the visibility status."""
        return self.value

    def __repr__(self) -> str:
        """Return a string representation for debugging."""
        return str(self)


class VisibilityController:
    """Controller for managing visibility status with easy-to-use methods."""

    def __init__(self, initial_status: VisibilityStatus = VisibilityStatus.OPEN):
        """Initialize the VisibilityController with a specific status."""
        self._status = initial_status

    @property
    def status(self) -> VisibilityStatus:
        """Return the current visibility status."""
        return self._status

    def to_open(self):
        """Change status to OPEN.

        Example:
            >>> vc = VisibilityController()
            >>> vc.to_open()
            >>> vc.status
            OPEN
        """
        self._status = VisibilityStatus.OPEN

    def to_hide(self):
        """Change status to HIDE.

        Example:
            >>> vc = VisibilityController()
            >>> vc.to_hide()
            >>> vc.status
            HIDE
        """
        self._status = VisibilityStatus.HIDE

    def to_open_with_warnings(self):
        """Change status to OPEN_WITH_WARNINGS.

        Example:
            >>> vc = VisibilityController()
            >>> vc.to_open_with_warnings()
            >>> vc.status
            OPEN_WITH_WARNINGS
        """
        self._status = VisibilityStatus.OPEN_WITH_WARNINGS

    def __str__(self):
        """Return the string representation of the visibility status."""
        return str(self._status)

    def __repr__(self) -> str:
        """Return a string representation for debugging."""
        return str(self)

    def to_dict(self):
        """Convert VisibilityController to dictionary for JSON serialization."""
        return {"status": str(self._status)}
