"""Connection plan container for direct attempts."""

from dataclasses import dataclass
from typing import Union

from ...models import AuthMethod, Protocol


@dataclass(frozen=True)
class ConnectionPlan:
    """Connection attempt configuration container."""

    server_name: str
    auth_method: Union[AuthMethod, str]
    protocol: Union[Protocol, str]
    port: int
