"""
Module-level RBAC enforcement for the 3 strict-whitelist roles.

Per the role-access spec, three roles have a hard module whitelist:

  * complaints_officer (رئيس القسم الفني):
        ALLOWED → complaints, tasks, teams.
        FORBIDDEN → contracts, investment-contracts, contract-intelligence,
        investment-properties, violations, reports, settings, users.

  * contracts_manager (مدير العقود):
        ALLOWED → manual/operational contracts, investment-contracts,
        contract-intelligence, investment-properties.
        FORBIDDEN → complaints, tasks, teams, users, settings, reports,
        violations.

  * investment_manager (مكتب الاستثمار):
        ALLOWED → investment-properties, investment-contracts,
        contract-intelligence.
        FORBIDDEN → complaints, tasks, teams, manual-contracts/contracts,
        users, settings, reports.

These tests pin the backend route guards so a future refactor can't
silently widen access.
"""
from __future__ import annotations

import pytest

from app.models.user import UserRole
from tests.conftest import _create_user, _login


# ---------------------------------------------------------------------------
# Per-role token fixtures
# ---------------------------------------------------------------------------

@pytest.fixture()
def complaints_officer_user(db):
    return _create_user(db, "test_co", UserRole.COMPLAINTS_OFFICER)


@pytest.fixture()
def complaints_officer_token(client, complaints_officer_user):
    return _login(client, "test_co")


@pytest.fixture()
def contracts_manager_user(db):
    return _create_user(db, "test_cm", UserRole.CONTRACTS_MANAGER)


@pytest.fixture()
def contracts_manager_token(client, contracts_manager_user):
    return _login(client, "test_cm")


@pytest.fixture()
def investment_manager_user(db):
    return _create_user(db, "test_im", UserRole.INVESTMENT_MANAGER)


@pytest.fixture()
def investment_manager_token(client, investment_manager_user):
    return _login(client, "test_im")


def _hdr(token: str) -> dict:
    return {"Authorization": f"Bearer {token}"}


# ---------------------------------------------------------------------------
# Allowed endpoints — must NOT 403
# ---------------------------------------------------------------------------

class TestComplaintsOfficerAllowed:
    """complaints_officer can access complaints, tasks, teams."""

    def test_can_list_complaints(self, client, complaints_officer_token):
        resp = client.get("/complaints/", headers=_hdr(complaints_officer_token))
        assert resp.status_code == 200, resp.text

    def test_can_list_tasks(self, client, complaints_officer_token):
        resp = client.get("/tasks/", headers=_hdr(complaints_officer_token))
        assert resp.status_code == 200, resp.text

    def test_can_list_teams(self, client, complaints_officer_token):
        resp = client.get("/teams/", headers=_hdr(complaints_officer_token))
        assert resp.status_code == 200, resp.text


class TestContractsManagerAllowed:
    """contracts_manager can access contracts/intel/investment endpoints."""

    def test_can_list_contracts(self, client, contracts_manager_token):
        resp = client.get("/contracts/", headers=_hdr(contracts_manager_token))
        assert resp.status_code == 200, resp.text

    def test_can_list_investment_contracts(self, client, contracts_manager_token):
        resp = client.get("/investment-contracts/", headers=_hdr(contracts_manager_token))
        assert resp.status_code == 200, resp.text

    def test_can_list_investment_properties(self, client, contracts_manager_token):
        resp = client.get("/investment-properties/", headers=_hdr(contracts_manager_token))
        assert resp.status_code == 200, resp.text

    def test_can_access_contract_intelligence(self, client, contracts_manager_token):
        # Use a known endpoint of the intelligence module.
        resp = client.get("/contract-intelligence/queue", headers=_hdr(contracts_manager_token))
        assert resp.status_code == 200, resp.text


class TestInvestmentManagerAllowed:
    """investment_manager can access assets, investment contracts, intel."""

    def test_can_list_investment_properties(self, client, investment_manager_token):
        resp = client.get("/investment-properties/", headers=_hdr(investment_manager_token))
        assert resp.status_code == 200, resp.text

    def test_can_list_investment_contracts(self, client, investment_manager_token):
        resp = client.get("/investment-contracts/", headers=_hdr(investment_manager_token))
        assert resp.status_code == 200, resp.text

    def test_can_access_contract_intelligence(self, client, investment_manager_token):
        resp = client.get("/contract-intelligence/queue", headers=_hdr(investment_manager_token))
        assert resp.status_code == 200, resp.text


# ---------------------------------------------------------------------------
# Forbidden endpoints — must 403
# ---------------------------------------------------------------------------

class TestComplaintsOfficerForbidden:
    """complaints_officer must NOT reach contracts/assets/users/settings/reports."""

    @pytest.mark.parametrize(
        "path",
        [
            "/contracts/",
            "/investment-contracts/",
            "/investment-properties/",
            "/contract-intelligence/queue",
            "/violations/",
            "/reports/summary",
            "/settings/",
            "/users/",
        ],
    )
    def test_forbidden(self, client, complaints_officer_token, path):
        resp = client.get(path, headers=_hdr(complaints_officer_token))
        assert resp.status_code == 403, f"{path}: {resp.status_code} {resp.text}"


class TestContractsManagerForbidden:
    """contracts_manager must NOT reach complaints/tasks/teams/users/settings/reports."""

    @pytest.mark.parametrize(
        "path",
        [
            "/complaints/",
            "/tasks/",
            "/teams/",
            "/violations/",
            "/reports/summary",
            "/settings/",
            "/users/",
        ],
    )
    def test_forbidden(self, client, contracts_manager_token, path):
        resp = client.get(path, headers=_hdr(contracts_manager_token))
        assert resp.status_code == 403, f"{path}: {resp.status_code} {resp.text}"


class TestInvestmentManagerForbidden:
    """investment_manager must NOT reach complaints/tasks/teams/operational
    contracts/users/settings/reports."""

    @pytest.mark.parametrize(
        "path",
        [
            "/complaints/",
            "/tasks/",
            "/teams/",
            "/contracts/",
            "/violations/",
            "/reports/summary",
            "/settings/",
            "/users/",
        ],
    )
    def test_forbidden(self, client, investment_manager_token, path):
        resp = client.get(path, headers=_hdr(investment_manager_token))
        assert resp.status_code == 403, f"{path}: {resp.status_code} {resp.text}"


class TestSettingsWriteRestriction:
    """Only project_director may PUT /settings/. The 3 restricted roles must 403."""

    @pytest.mark.parametrize("token_fixture", [
        "complaints_officer_token",
        "contracts_manager_token",
        "investment_manager_token",
    ])
    def test_settings_put_forbidden(self, client, request, token_fixture):
        token = request.getfixturevalue(token_fixture)
        resp = client.put(
            "/settings/",
            json={"items": [{"key": "k", "value": "v", "value_type": "string", "category": "c"}]},
            headers=_hdr(token),
        )
        assert resp.status_code == 403, resp.text
