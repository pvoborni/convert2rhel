import os.path

import pytest


def _check_enabled_repos_rhel8(enabled_repos):
    """Helper function to assert RHEL repositories."""
    baseos_repo = "rhel-8-for-x86_64-baseos-rpms"
    appstream_repo = "rhel-8-for-x86_64-appstream-rpms"

    assert baseos_repo in enabled_repos
    assert appstream_repo in enabled_repos


def _check_eus_enabled_repos_rhel8(enabled_repos):
    """Helper function to assert EUS repositories."""
    baseos_repo = "rhel-8-for-x86_64-baseos-eus-rpms"
    appstream_repo = "rhel-8-for-x86_64-appstream-eus-rpms"

    assert baseos_repo in enabled_repos
    assert appstream_repo in enabled_repos


@pytest.mark.enabled_repositories
def test_enabled_repositories(shell, system_release):
    """Verify, that the EUS repositories are enabled after conversion"""

    enabled_repos = shell("yum repolist").output

    try:
        if "redhat-8.6" in system_release:
            # Handle the special test case scenario where we do not use the
            # premium account with EUS repositories
            if os.path.exists("/non_eus_repos_used"):
                _check_enabled_repos_rhel8(enabled_repos)
            else:
                _check_eus_enabled_repos_rhel8(enabled_repos)
        elif "redhat-8.5" in system_release:
            _check_enabled_repos_rhel8(enabled_repos)
        elif "redhat-7.9" in system_release:
            assert "rhel-7-server-rpms/7Server/x86_64" in enabled_repos
    finally:
        # We need to unregister the system after the conversion
        shell("subscription-manager unregister")
