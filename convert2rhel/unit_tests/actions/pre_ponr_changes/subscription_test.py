# Copyright(C) 2023 Red Hat, Inc.
#
# This program is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with this program.  If not, see <https://www.gnu.org/licenses/>.

__metaclass__ = type

import pytest
import six

from convert2rhel import actions, cert, pkghandler, repo, subscription, toolopts, unit_tests
from convert2rhel.actions import STATUS_CODE
from convert2rhel.actions.pre_ponr_changes.subscription import PreSubscription, SubscribeSystem


six.add_move(six.MovedModule("mock", "mock", "unittest.mock"))
from six.moves import mock


@pytest.fixture
def pre_subscription_instance():
    return PreSubscription()


class SystemCertMock:
    def __init__(self):
        pass

    def __call__(self, *args, **kwds):
        return self

    def install(self):
        pass


def test_pre_subscription_dependency_order(pre_subscription_instance):
    expected_dependencies = ("REMOVE_EXCLUDED_PACKAGES",)

    assert expected_dependencies == pre_subscription_instance.dependencies


def test_pre_subscription_no_rhsm_option_detected(pre_subscription_instance, monkeypatch, caplog):
    monkeypatch.setattr(toolopts.tool_opts, "no_rhsm", True)
    expected = set(
        (
            actions.ActionMessage(
                level="WARNING",
                id="PRE_SUBSCRIPTION_CHECK_SKIP",
                title="Pre-subscription check skip",
                description="Detected --no-rhsm option. Skipping.",
                diagnosis=None,
                remediation=None,
            ),
        )
    )
    pre_subscription_instance.run()

    assert "Detected --no-rhsm option. Skipping" in caplog.records[-1].message
    assert pre_subscription_instance.result.level == STATUS_CODE["SUCCESS"]
    assert expected.issuperset(pre_subscription_instance.messages)
    assert expected.issubset(pre_subscription_instance.messages)


def test_pre_subscription_run(pre_subscription_instance, monkeypatch):
    monkeypatch.setattr(pkghandler, "install_gpg_keys", mock.Mock())
    monkeypatch.setattr(subscription, "download_rhsm_pkgs", mock.Mock())
    monkeypatch.setattr(subscription, "replace_subscription_manager", mock.Mock())
    monkeypatch.setattr(subscription, "verify_rhsm_installed", mock.Mock())
    monkeypatch.setattr(cert, "SystemCert", SystemCertMock())

    pre_subscription_instance.run()

    assert pre_subscription_instance.result.level == STATUS_CODE["SUCCESS"]
    assert pkghandler.install_gpg_keys.call_count == 1
    assert subscription.download_rhsm_pkgs.call_count == 1
    assert subscription.replace_subscription_manager.call_count == 1
    assert subscription.verify_rhsm_installed.call_count == 1


@pytest.mark.parametrize(
    ("exception", "expected_level"),
    (
        (
            SystemExit("Exiting..."),
            ("ERROR", "UNKNOWN_ERROR", "Unknown error", "The cause of this error is unknown", "Exiting..."),
        ),
    ),
)
def test_pre_subscription_exceptions(exception, expected_level, pre_subscription_instance, monkeypatch):
    # In the actual code, the exceptions can happen at different stages, but
    # since it is a unit test, it doesn't matter what function will raise the
    # exception we want.
    monkeypatch.setattr(pkghandler, "install_gpg_keys", mock.Mock(side_effect=exception))

    pre_subscription_instance.run()
    level, id, title, description, diagnosis = expected_level
    unit_tests.assert_actions_result(pre_subscription_instance, level=level, id=id, description=description)


@pytest.mark.parametrize(
    ("exception", "expected_level"),
    (
        (
            subscription.UnregisterError,
            (
                "ERROR",
                "UNABLE_TO_REGISTER",
                "System unregistration failure",
                "The system is already registered with subscription-manager",
                "Failed to unregister the system:",
                "You may want to unregister the system manually",
            ),
        ),
    ),
)
def test_pre_subscription_exceptions_with_remediation(
    exception, expected_level, pre_subscription_instance, monkeypatch
):
    # In the actual code, the exceptions can happen at different stages, but
    # since it is a unit test, it doesn't matter what function will raise the
    # exception we want.
    monkeypatch.setattr(pkghandler, "install_gpg_keys", mock.Mock(side_effect=exception))

    pre_subscription_instance.run()
    level, id, title, description, diagnosis, remediation = expected_level
    unit_tests.assert_actions_result(
        pre_subscription_instance,
        level=level,
        id=id,
        description=description,
        diagnosis=diagnosis,
    )


@pytest.fixture
def subscribe_system_instance():
    return SubscribeSystem()


def test_subscribe_system_dependency_order(subscribe_system_instance):
    expected_dependencies = (
        "REMOVE_REPOSITORY_FILES_PACKAGES",
        "PRE_SUBSCRIPTION",
    )

    assert expected_dependencies == subscribe_system_instance.dependencies


def test_subscribe_system_no_rhsm_option_detected(subscribe_system_instance, monkeypatch, caplog):
    monkeypatch.setattr(toolopts.tool_opts, "no_rhsm", True)
    expected = set(
        (
            actions.ActionMessage(
                level="WARNING",
                id="SUBSCRIPTION_CHECK_SKIP",
                title="Subscription check skip",
                description="Detected --no-rhsm option. Skipping.",
                diagnosis=None,
                remediation=None,
            ),
        )
    )
    subscribe_system_instance.run()
    assert "Detected --no-rhsm option. Skipping" in caplog.records[-1].message
    assert subscribe_system_instance.result.level == STATUS_CODE["SUCCESS"]
    assert expected.issuperset(subscribe_system_instance.messages)
    assert expected.issubset(subscribe_system_instance.messages)


def test_subscribe_system_run(subscribe_system_instance, monkeypatch):
    monkeypatch.setattr(subscription, "subscribe_system", mock.Mock())
    monkeypatch.setattr(repo, "get_rhel_repoids", mock.Mock())
    monkeypatch.setattr(subscription, "disable_repos", mock.Mock())
    monkeypatch.setattr(subscription, "enable_repos", mock.Mock())

    subscribe_system_instance.run()

    assert subscribe_system_instance.result.level == STATUS_CODE["SUCCESS"]
    assert subscription.subscribe_system.call_count == 1
    assert repo.get_rhel_repoids.call_count == 1
    assert subscription.disable_repos.call_count == 1
    assert subscription.enable_repos.call_count == 1


@pytest.mark.parametrize(
    ("exception", "expected_level"),
    (
        (
            SystemExit("Exiting..."),
            ("ERROR", "UNKNOWN_ERROR", "Unknown error", "The cause of this error is unknown", "Exiting..."),
        ),
        (
            ValueError,
            (
                "ERROR",
                "MISSING_REGISTRATION_COMBINATION",
                "Missing registration combination",
                "There are missing registration combinations",
                "One or more combinations were missing for subscription-manager parameters:",
            ),
        ),
        (
            IOError("/usr/bin/t"),
            (
                "ERROR",
                "MISSING_SUBSCRIPTION_MANAGER_BINARY",
                "Missing subscription-manager binary",
                "There is a missing subscription-manager binary",
                "Failed to execute command:",
            ),
        ),
    ),
)
def test_subscribe_system_exceptions(exception, expected_level, subscribe_system_instance, monkeypatch):
    # In the actual code, the exceptions can happen at different stages, but
    # since it is a unit test, it doesn't matter what function will raise the
    # exception we want.
    monkeypatch.setattr(subscription, "subscribe_system", mock.Mock(side_effect=exception))

    subscribe_system_instance.run()

    level, id, title, description, diagnosis = expected_level
    unit_tests.assert_actions_result(
        subscribe_system_instance, level=level, id=id, title=title, description=description, diagnosis=diagnosis
    )