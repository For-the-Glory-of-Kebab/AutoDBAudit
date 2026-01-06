"""Aggregate repository facade for psremoting persistence."""

from .base import RepositoryBase
from .profiles_reader import ProfilesReader
from .profiles_writer import ProfilesWriter
from .attempts import AttemptsMixin
from .state import ServerStateMixin


class PSRemotingRepository(
    ProfilesReader,
    ProfilesWriter,
    AttemptsMixin,
    ServerStateMixin,
    RepositoryBase,
):
    """Facade combining profile, attempt, and server state persistence."""

    __slots__ = ()
