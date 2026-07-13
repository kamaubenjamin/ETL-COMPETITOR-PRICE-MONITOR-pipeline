"""Provider-neutral identity resolution boundaries."""

from .contracts import (
    IdentityProvider,
    IdentityProviderResult,
    IdentityResolutionReason,
    IdentityResolutionStatus,
)
from .local import (
    LocalIdentityProvider,
    LocalProviderMode,
    create_local_demo_provider,
    local_demo_principals,
)

__all__ = [
    "IdentityProvider",
    "IdentityProviderResult",
    "IdentityResolutionReason",
    "IdentityResolutionStatus",
    "LocalIdentityProvider",
    "LocalProviderMode",
    "create_local_demo_provider",
    "local_demo_principals",
]
