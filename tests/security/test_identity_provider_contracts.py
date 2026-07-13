from typing import runtime_checkable

import pytest

from src.security import anonymous_principal
from src.security.providers import (
    IdentityProvider,
    IdentityProviderResult,
    IdentityResolutionReason,
    IdentityResolutionStatus,
    create_local_demo_provider,
)


def test_provider_protocol_is_structural_and_read_only():
    provider = create_local_demo_provider()
    assert isinstance(provider, IdentityProvider)
    assert runtime_checkable is not None
    assert not hasattr(provider, "create")


def test_provider_results_are_immutable_and_json_safe():
    result = IdentityProviderResult(
        IdentityResolutionStatus.UNAUTHENTICATED,
        IdentityResolutionReason.ANONYMOUS_IDENTITY,
        anonymous_principal(),
        {"provider_mode": "test"},
    )
    assert result.to_dict()["principal"]["principal_type"] == "anonymous"
    with pytest.raises(Exception):
        result.status = IdentityResolutionStatus.RESOLVED


def test_provider_result_shape_rejects_inconsistent_principals():
    with pytest.raises(ValueError, match="authenticated principal"):
        IdentityProviderResult(
            IdentityResolutionStatus.RESOLVED,
            IdentityResolutionReason.IDENTITY_RESOLVED,
            anonymous_principal(),
        )


def test_provider_result_rejects_inconsistent_status_reason():
    with pytest.raises(ValueError, match="reason is invalid"):
        IdentityProviderResult(
            IdentityResolutionStatus.DENIED,
            IdentityResolutionReason.IDENTITY_RESOLVED,
        )
