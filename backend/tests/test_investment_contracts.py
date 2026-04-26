"""Tests for Investment Contracts CRUD, attachments, expiry alerts, and
permission enforcement.

Permission summary (per spec):
- project_director       — full CRUD
- contracts_manager      — full CRUD on contracts
- investment_manager     — full CRUD on contracts
- property_manager       — view contracts (read-only)
- field_team / contractor_user / citizen — 403 on every endpoint
"""
from datetime import date, timedelta

import pytest

from app.models.investment_contract import (
    InvestmentContract,
    InvestmentContractStatus,
    InvestmentType,
)
from app.models.investment_property import (
    InvestmentProperty,
    PropertyStatus,
    PropertyType,
)
from app.models.user import UserRole


# ---------------------------------------------------------------------------
# Fixtures / helpers
# ---------------------------------------------------------------------------


def _auth(token: str) -> dict:
    return {"Authorization": f"Bearer {token}"}


@pytest.fixture
def linked_property(db) -> InvestmentProperty:
    prop = InvestmentProperty(
        property_type=PropertyType.BUILDING,
        address="عقار اختبار - شارع الجامعة",
        status=PropertyStatus.AVAILABLE,
    )
    db.add(prop)
    db.commit()
    db.refresh(prop)
    return prop


def _payload(property_id: int, **overrides) -> dict:
    base = {
        "contract_number": "INV-2026-0001",
        "property_id": property_id,
        "investor_name": "شركة المستثمرون المتحدون",
        "investor_contact": "0992223344",
        "investment_type": "lease",
        "start_date": date.today().isoformat(),
        "end_date": (date.today() + timedelta(days=365)).isoformat(),
        "contract_value": "150000.00",
        "notes": "ملاحظات تجريبية",
    }
    base.update(overrides)
    return base


def _make_contract(
    db,
    prop: InvestmentProperty,
    *,
    end_in_days: int = 365,
    contract_number: str = "INV-CT-1",
    status: InvestmentContractStatus = InvestmentContractStatus.ACTIVE,
) -> InvestmentContract:
    today = date.today()
    c = InvestmentContract(
        contract_number=contract_number,
        property_id=prop.id,
        investor_name="مستثمر",
        investment_type=InvestmentType.LEASE,
        start_date=today - timedelta(days=30),
        end_date=today + timedelta(days=end_in_days),
        contract_value=100000,
        status=status,
    )
    db.add(c)
    db.commit()
    db.refresh(c)
    return c


# ---------------------------------------------------------------------------
# Director CRUD
# ---------------------------------------------------------------------------


class TestDirectorCRUD:
    def test_create(self, client, director_token, linked_property):
        resp = client.post(
            "/investment-contracts/",
            json=_payload(linked_property.id),
            headers=_auth(director_token),
        )
        assert resp.status_code == 201, resp.text
        data = resp.json()
        assert data["contract_number"] == "INV-2026-0001"
        assert data["property_id"] == linked_property.id
        assert data["status"] == "active"
        assert data["is_active"] is True
        assert data["days_until_expiry"] == 365
        assert data["expiry_alert"] is None

    def test_create_rejects_unknown_property(self, client, director_token):
        resp = client.post(
            "/investment-contracts/",
            json=_payload(99999),
            headers=_auth(director_token),
        )
        assert resp.status_code == 400

    def test_create_rejects_inactive_property(
        self, client, director_token, db, linked_property
    ):
        linked_property.is_active = False
        db.commit()
        resp = client.post(
            "/investment-contracts/",
            json=_payload(linked_property.id),
            headers=_auth(director_token),
        )
        assert resp.status_code == 400

    def test_create_rejects_duplicate_number(
        self, client, director_token, linked_property, db
    ):
        _make_contract(db, linked_property, contract_number="DUP-1")
        resp = client.post(
            "/investment-contracts/",
            json=_payload(linked_property.id, contract_number="DUP-1"),
            headers=_auth(director_token),
        )
        assert resp.status_code == 400

    def test_create_rejects_end_before_start(
        self, client, director_token, linked_property
    ):
        resp = client.post(
            "/investment-contracts/",
            json=_payload(
                linked_property.id,
                start_date=date.today().isoformat(),
                end_date=(date.today() - timedelta(days=1)).isoformat(),
            ),
            headers=_auth(director_token),
        )
        assert resp.status_code == 422

    def test_list(self, client, director_token, db, linked_property):
        _make_contract(db, linked_property, contract_number="A1", end_in_days=10)
        _make_contract(db, linked_property, contract_number="A2", end_in_days=200)
        resp = client.get("/investment-contracts/", headers=_auth(director_token))
        assert resp.status_code == 200
        data = resp.json()
        assert data["total_count"] == 2

    def test_filter_by_property(self, client, director_token, db, linked_property):
        other = InvestmentProperty(
            property_type=PropertyType.LAND, address="أخرى",
            status=PropertyStatus.AVAILABLE,
        )
        db.add(other)
        db.commit()
        db.refresh(other)
        _make_contract(db, linked_property, contract_number="L-1")
        _make_contract(db, other, contract_number="L-2")

        resp = client.get(
            f"/investment-contracts/?property_id={linked_property.id}",
            headers=_auth(director_token),
        )
        assert resp.status_code == 200
        items = resp.json()["items"]
        assert len(items) == 1
        assert items[0]["contract_number"] == "L-1"

    def test_filter_by_investor(self, client, director_token, db, linked_property):
        a = _make_contract(db, linked_property, contract_number="I-1")
        a.investor_name = "Alpha LLC"
        b = _make_contract(db, linked_property, contract_number="I-2")
        b.investor_name = "Bravo Co"
        db.commit()

        resp = client.get(
            "/investment-contracts/?investor=Alpha", headers=_auth(director_token)
        )
        assert resp.status_code == 200
        items = resp.json()["items"]
        assert len(items) == 1
        assert items[0]["contract_number"] == "I-1"

    def test_filter_by_status(self, client, director_token, db, linked_property):
        _make_contract(db, linked_property, contract_number="S-1")
        _make_contract(
            db, linked_property, contract_number="S-2",
            status=InvestmentContractStatus.EXPIRED,
        )
        resp = client.get(
            "/investment-contracts/?status_filter=expired",
            headers=_auth(director_token),
        )
        assert resp.status_code == 200
        items = resp.json()["items"]
        assert len(items) == 1
        assert items[0]["status"] == "expired"

    def test_search_q(self, client, director_token, db, linked_property):
        a = _make_contract(db, linked_property, contract_number="SEARCH-AAA")
        b = _make_contract(db, linked_property, contract_number="OTHER-BBB")
        b.investor_name = "Hidden"
        db.commit()
        resp = client.get(
            "/investment-contracts/?q=SEARCH", headers=_auth(director_token)
        )
        assert resp.status_code == 200
        items = resp.json()["items"]
        assert len(items) == 1
        assert items[0]["contract_number"] == "SEARCH-AAA"

    def test_get_detail(self, client, director_token, db, linked_property):
        c = _make_contract(db, linked_property, contract_number="G-1")
        resp = client.get(
            f"/investment-contracts/{c.id}", headers=_auth(director_token)
        )
        assert resp.status_code == 200
        assert resp.json()["contract_number"] == "G-1"

    def test_get_404(self, client, director_token):
        resp = client.get(
            "/investment-contracts/99999", headers=_auth(director_token)
        )
        assert resp.status_code == 404

    def test_update(self, client, director_token, db, linked_property):
        c = _make_contract(db, linked_property, contract_number="U-1")
        resp = client.put(
            f"/investment-contracts/{c.id}",
            json={"status": "near_expiry", "notes": "تم التحديث"},
            headers=_auth(director_token),
        )
        assert resp.status_code == 200
        data = resp.json()
        assert data["status"] == "near_expiry"
        assert data["notes"] == "تم التحديث"

    def test_update_to_unknown_property_fails(
        self, client, director_token, db, linked_property
    ):
        c = _make_contract(db, linked_property, contract_number="U-2")
        resp = client.put(
            f"/investment-contracts/{c.id}",
            json={"property_id": 99999},
            headers=_auth(director_token),
        )
        assert resp.status_code == 400

    def test_update_duplicate_number_fails(
        self, client, director_token, db, linked_property
    ):
        a = _make_contract(db, linked_property, contract_number="A")
        _make_contract(db, linked_property, contract_number="B")
        resp = client.put(
            f"/investment-contracts/{a.id}",
            json={"contract_number": "B"},
            headers=_auth(director_token),
        )
        assert resp.status_code == 400

    def test_update_end_before_start_fails(
        self, client, director_token, db, linked_property
    ):
        c = _make_contract(db, linked_property, contract_number="U-3")
        resp = client.put(
            f"/investment-contracts/{c.id}",
            json={"end_date": (c.start_date - timedelta(days=1)).isoformat()},
            headers=_auth(director_token),
        )
        assert resp.status_code == 422

    def test_delete_soft(self, client, director_token, db, linked_property):
        c = _make_contract(db, linked_property, contract_number="D-1")
        resp = client.delete(
            f"/investment-contracts/{c.id}", headers=_auth(director_token)
        )
        assert resp.status_code == 200
        db.refresh(c)
        assert c.is_active is False
        assert c.status == InvestmentContractStatus.CANCELLED

        # Excluded from default list
        list_resp = client.get(
            "/investment-contracts/", headers=_auth(director_token)
        )
        assert list_resp.json()["total_count"] == 0


# ---------------------------------------------------------------------------
# Attachments
# ---------------------------------------------------------------------------


class TestAttachments:
    def test_typed_attachments_round_trip(
        self, client, director_token, linked_property
    ):
        payload = _payload(
            linked_property.id,
            contract_copy="/uploads/investment_contracts/cc.pdf",
            terms_booklet="/uploads/investment_contracts/tb.pdf",
            investor_id_copy="/uploads/investment_contracts/inv-id.pdf",
            owner_id_copy="/uploads/investment_contracts/own-id.pdf",
            ownership_proof="/uploads/investment_contracts/proof.pdf",
            handover_report="/uploads/investment_contracts/handover.pdf",
            additional_attachments=[
                "/uploads/investment_contracts/extra1.pdf",
                "/uploads/investment_contracts/extra2.pdf",
            ],
        )
        resp = client.post(
            "/investment-contracts/", json=payload, headers=_auth(director_token)
        )
        assert resp.status_code == 201, resp.text
        data = resp.json()
        assert data["contract_copy"].endswith("cc.pdf")
        assert data["terms_booklet"].endswith("tb.pdf")
        assert data["investor_id_copy"].endswith("inv-id.pdf")
        assert data["owner_id_copy"].endswith("own-id.pdf")
        assert data["ownership_proof"].endswith("proof.pdf")
        assert data["handover_report"].endswith("handover.pdf")
        assert isinstance(data["additional_attachments"], list)
        assert len(data["additional_attachments"]) == 2

    def test_attachments_persist_through_update(
        self, client, director_token, db, linked_property
    ):
        c = _make_contract(db, linked_property, contract_number="ATT-1")
        # Upload one attachment via PUT
        resp = client.put(
            f"/investment-contracts/{c.id}",
            json={"contract_copy": "/uploads/investment_contracts/x.pdf"},
            headers=_auth(director_token),
        )
        assert resp.status_code == 200
        assert resp.json()["contract_copy"].endswith("x.pdf")

        # Add additional attachments
        resp = client.put(
            f"/investment-contracts/{c.id}",
            json={
                "additional_attachments": [
                    "/uploads/investment_contracts/a.pdf",
                    "/uploads/investment_contracts/b.pdf",
                ]
            },
            headers=_auth(director_token),
        )
        assert resp.status_code == 200
        assert len(resp.json()["additional_attachments"]) == 2


# ---------------------------------------------------------------------------
# Expiry alerts
# ---------------------------------------------------------------------------


class TestExpiryAlerts:
    def test_expiry_buckets_in_response(
        self, client, director_token, db, linked_property
    ):
        # 25 days → "30" bucket, 50 days → "60", 80 days → "90", 200 days → None
        c25 = _make_contract(db, linked_property, contract_number="E-25", end_in_days=25)
        c50 = _make_contract(db, linked_property, contract_number="E-50", end_in_days=50)
        c80 = _make_contract(db, linked_property, contract_number="E-80", end_in_days=80)
        c200 = _make_contract(db, linked_property, contract_number="E-200", end_in_days=200)

        for cid, expected in (
            (c25.id, "30"), (c50.id, "60"), (c80.id, "90"), (c200.id, None),
        ):
            resp = client.get(
                f"/investment-contracts/{cid}", headers=_auth(director_token)
            )
            assert resp.json()["expiry_alert"] == expected, resp.text

    def test_expired_bucket_for_past_end_date(
        self, client, director_token, db, linked_property
    ):
        c = _make_contract(db, linked_property, contract_number="EXP-1", end_in_days=-5)
        resp = client.get(
            f"/investment-contracts/{c.id}", headers=_auth(director_token)
        )
        data = resp.json()
        assert data["expiry_alert"] == "expired"
        assert data["days_until_expiry"] == -5

    def test_expiring_endpoint_default_within_90(
        self, client, director_token, db, linked_property
    ):
        _make_contract(db, linked_property, contract_number="X-25", end_in_days=25)
        _make_contract(db, linked_property, contract_number="X-100", end_in_days=100)
        _make_contract(db, linked_property, contract_number="X-200", end_in_days=200)
        _make_contract(db, linked_property, contract_number="X-EXP", end_in_days=-3)

        resp = client.get(
            "/investment-contracts/expiring", headers=_auth(director_token)
        )
        assert resp.status_code == 200
        nums = {row["contract_number"] for row in resp.json()}
        # Contains X-25 (within 90) and X-EXP (expired, included by default).
        assert "X-25" in nums
        assert "X-EXP" in nums
        assert "X-100" not in nums
        assert "X-200" not in nums

    def test_expiring_endpoint_within_30(
        self, client, director_token, db, linked_property
    ):
        _make_contract(db, linked_property, contract_number="W30-25", end_in_days=25)
        _make_contract(db, linked_property, contract_number="W30-50", end_in_days=50)
        resp = client.get(
            "/investment-contracts/expiring?within_days=30&include_expired=false",
            headers=_auth(director_token),
        )
        assert resp.status_code == 200
        nums = {row["contract_number"] for row in resp.json()}
        assert "W30-25" in nums
        assert "W30-50" not in nums

    def test_expiring_excludes_cancelled(
        self, client, director_token, db, linked_property
    ):
        cancelled = _make_contract(
            db, linked_property, contract_number="C-1", end_in_days=10,
            status=InvestmentContractStatus.CANCELLED,
        )
        resp = client.get(
            "/investment-contracts/expiring", headers=_auth(director_token)
        )
        nums = {row["contract_number"] for row in resp.json()}
        assert "C-1" not in nums

    def test_dashboard_stats_buckets(
        self, client, director_token, db, linked_property
    ):
        _make_contract(db, linked_property, contract_number="DS-25", end_in_days=25)
        _make_contract(db, linked_property, contract_number="DS-50", end_in_days=50)
        _make_contract(db, linked_property, contract_number="DS-80", end_in_days=80)
        _make_contract(db, linked_property, contract_number="DS-EXP", end_in_days=-2)

        resp = client.get("/dashboard/stats", headers=_auth(director_token))
        assert resp.status_code == 200, resp.text
        data = resp.json()
        # Cumulative buckets: within_30 ⊆ within_60 ⊆ within_90.
        assert data["investment_contracts_within_30"] >= 1
        assert data["investment_contracts_within_60"] >= 2
        assert data["investment_contracts_within_90"] >= 3
        assert data["investment_contracts_expired"] >= 1
        assert data["total_investment_contracts"] >= 4


# ---------------------------------------------------------------------------
# Per-role permissions
# ---------------------------------------------------------------------------


class TestContractsManagerPermissions:
    def test_can_create_and_delete(self, client, db, linked_property):
        from tests.conftest import _create_user, _login
        _create_user(db, "ic_cm", UserRole.CONTRACTS_MANAGER)
        token = _login(client, "ic_cm")

        resp = client.post(
            "/investment-contracts/",
            json=_payload(linked_property.id, contract_number="CM-1"),
            headers=_auth(token),
        )
        assert resp.status_code == 201
        cid = resp.json()["id"]

        # Update
        resp = client.put(
            f"/investment-contracts/{cid}",
            json={"notes": "تم التعديل"},
            headers=_auth(token),
        )
        assert resp.status_code == 200

        # Delete
        resp = client.delete(
            f"/investment-contracts/{cid}", headers=_auth(token)
        )
        assert resp.status_code == 200


class TestInvestmentManagerPermissions:
    def test_can_crud(self, client, db, linked_property):
        from tests.conftest import _create_user, _login
        _create_user(db, "ic_im", UserRole.INVESTMENT_MANAGER)
        token = _login(client, "ic_im")

        resp = client.post(
            "/investment-contracts/",
            json=_payload(linked_property.id, contract_number="IM-1"),
            headers=_auth(token),
        )
        assert resp.status_code == 201
        cid = resp.json()["id"]

        resp = client.put(
            f"/investment-contracts/{cid}",
            json={"investor_name": "مستثمر معدل"},
            headers=_auth(token),
        )
        assert resp.status_code == 200

        resp = client.get(
            f"/investment-contracts/{cid}", headers=_auth(token)
        )
        assert resp.status_code == 200

        resp = client.delete(
            f"/investment-contracts/{cid}", headers=_auth(token)
        )
        assert resp.status_code == 200


class TestPropertyManagerPermissions:
    def test_view_only(self, client, db, linked_property):
        from tests.conftest import _create_user, _login
        _create_user(db, "ic_pm", UserRole.PROPERTY_MANAGER)
        token = _login(client, "ic_pm")

        c = _make_contract(db, linked_property, contract_number="PM-VIEW")

        # List allowed
        resp = client.get("/investment-contracts/", headers=_auth(token))
        assert resp.status_code == 200
        assert resp.json()["total_count"] == 1

        # Get allowed
        resp = client.get(
            f"/investment-contracts/{c.id}", headers=_auth(token)
        )
        assert resp.status_code == 200

        # Expiring allowed
        resp = client.get(
            "/investment-contracts/expiring", headers=_auth(token)
        )
        assert resp.status_code == 200

    def test_cannot_write(self, client, db, linked_property):
        from tests.conftest import _create_user, _login
        _create_user(db, "ic_pm_w", UserRole.PROPERTY_MANAGER)
        token = _login(client, "ic_pm_w")

        c = _make_contract(db, linked_property, contract_number="PM-W")

        resp = client.post(
            "/investment-contracts/",
            json=_payload(linked_property.id, contract_number="PM-W2"),
            headers=_auth(token),
        )
        assert resp.status_code == 403

        resp = client.put(
            f"/investment-contracts/{c.id}",
            json={"notes": "x"},
            headers=_auth(token),
        )
        assert resp.status_code == 403

        resp = client.delete(
            f"/investment-contracts/{c.id}", headers=_auth(token)
        )
        assert resp.status_code == 403


class TestForbiddenRoles:
    @pytest.mark.parametrize(
        "username,role",
        [
            ("ic_field", UserRole.FIELD_TEAM),
            ("ic_contractor", UserRole.CONTRACTOR_USER),
            ("ic_citizen", UserRole.CITIZEN),
        ],
    )
    def test_no_access(self, client, db, linked_property, username, role):
        from tests.conftest import _create_user, _login
        _create_user(db, username, role)
        token = _login(client, username)

        c = _make_contract(db, linked_property, contract_number=f"FB-{username}")

        # Every endpoint must 403
        resp = client.get("/investment-contracts/", headers=_auth(token))
        assert resp.status_code == 403

        resp = client.get(
            f"/investment-contracts/{c.id}", headers=_auth(token)
        )
        assert resp.status_code == 403

        resp = client.get(
            "/investment-contracts/expiring", headers=_auth(token)
        )
        assert resp.status_code == 403

        resp = client.post(
            "/investment-contracts/",
            json=_payload(linked_property.id, contract_number=f"FB-NEW-{username}"),
            headers=_auth(token),
        )
        assert resp.status_code == 403

        resp = client.put(
            f"/investment-contracts/{c.id}", json={"notes": "x"}, headers=_auth(token)
        )
        assert resp.status_code == 403

        resp = client.delete(
            f"/investment-contracts/{c.id}", headers=_auth(token)
        )
        assert resp.status_code == 403
