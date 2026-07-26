class ProfileJobBuilderError(Exception):
    """Base class for expected user-facing failures."""


class InputError(ProfileJobBuilderError):
    """The source YAML does not satisfy the supported contract."""


class CommandError(ProfileJobBuilderError):
    """An external command failed."""
