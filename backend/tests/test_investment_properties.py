"""
Tests for Investment Properties CRUD and permission enforcement.

Covers:
- project_director and property_manager create, list, filter, search,
  update, delete properties
- contracts_manager and investment_manager are read-only (view-only)
- field_team, contractor_user, citizen cannot access at all (403)
- validation: invalid property_type or status returns 422
"""
import pytest
from app.models.user import UserRole
from app.models.investment_property import InvestmentProperty, PropertyType, PropertyStatus


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _auth(token: str) -> dict:
    return {"Authorization": f"Bearer {token}"}


def _make_property_payload(**overrides) -> dict:
    payload = {
        "property_type": "building",
        "address": "شارع المدينة 10",
        "area": 250.5,
        "status": "available",
        "description": "عقار سكني",
        "owner_name": "أحمد محمد",
        "owner_info": "رقم الهاتف: 0991234567",
        "notes": "ملاحظات العقار",
    }
    payload.update(overrides)
    return payload


# ---------------------------------------------------------------------------
# Director CRUD
# ---------------------------------------------------------------------------

class TestDirectorCRUD:
    def test_director_creates_property(self, client, director_token):
        resp = client.post(
            "/investment-properties/",
            json=_make_property_payload(),
            headers=_auth(director_token),
        )
        assert resp.status_code == 201
        data = resp.json()
        assert data["property_type"] == "building"
        assert data["address"] == "شارع المدينة 10"
        assert data["status"] == "available"
        assert data["owner_name"] == "أحمد محمد"
        assert data["is_active"] is True

    def test_director_creates_property_with_attachments(self, client, director_token):
        payload = _make_property_payload(
            property_images=["/uploads/investment_contracts/a.jpg"],
            property_documents=["/uploads/investment_contracts/b.pdf"],
            owner_id_image="/uploads/investment_contracts/c.jpg",
            additional_attachments=["/uploads/investment_contracts/d.docx"],
        )
        resp = client.post(
            "/investment-properties/",
            json=payload,
            headers=_auth(director_token),
        )
        assert resp.status_code == 201
        data = resp.json()
        assert data["property_images"] == payload["property_images"]
        assert data["property_documents"] == payload["property_documents"]
        assert data["owner_id_image"] == payload["owner_id_image"]
        assert data["additional_attachments"] == payload["additional_attachments"]

    def test_director_lists_properties(self, client, director_token, db):
        db.add(InvestmentProperty(
            property_type=PropertyType.BUILDING,
            address="موقع 1",
            status=PropertyStatus.AVAILABLE,
        ))
        db.add(InvestmentProperty(
            property_type=PropertyType.LAND,
            address="موقع 2",
            status=PropertyStatus.INVESTED,
        ))
        db.commit()

        resp = client.get("/investment-properties/", headers=_auth(director_token))
        assert resp.status_code == 200
        data = resp.json()
        assert data["total_count"] == 2
        assert len(data["items"]) == 2

    def test_director_filters_by_type(self, client, director_token, db):
        db.add(InvestmentProperty(
            property_type=PropertyType.BUILDING,
            address="موقع 1",
            status=PropertyStatus.AVAILABLE,
        ))
        db.add(InvestmentProperty(
            property_type=PropertyType.LAND,
            address="موقع 2",
            status=PropertyStatus.AVAILABLE,
        ))
        db.commit()

        resp = client.get("/investment-properties/?type=building", headers=_auth(director_token))
        assert resp.status_code == 200
        data = resp.json()
        assert data["total_count"] == 1
        assert data["items"][0]["property_type"] == "building"

    def test_director_filters_by_status(self, client, director_token, db):
        db.add(InvestmentProperty(
            property_type=PropertyType.BUILDING,
            address="موقع 1",
            status=PropertyStatus.AVAILABLE,
        ))
        db.add(InvestmentProperty(
            property_type=PropertyType.LAND,
            address="موقع 2",
            status=PropertyStatus.INVESTED,
        ))
        db.commit()

        resp = client.get("/investment-properties/?status=invested", headers=_auth(director_token))
        assert resp.status_code == 200
        data = resp.json()
        assert data["total_count"] == 1
        assert data["items"][0]["status"] == "invested"

    def test_director_searches_properties(self, client, director_token, db):
        db.add(InvestmentProperty(
            property_type=PropertyType.RESTAURANT,
            address="شارع العلوي",
            owner_name="خالد علي",
            status=PropertyStatus.AVAILABLE,
        ))
        db.add(InvestmentProperty(
            property_type=PropertyType.SHOP,
            address="حي الأمين",
            owner_name="سامي عبدو",
            status=PropertyStatus.AVAILABLE,
        ))
        db.commit()

        resp = client.get("/investment-properties/?q=العلوي", headers=_auth(director_token))
        assert resp.status_code == 200
        data = resp.json()
        assert data["total_count"] == 1
        assert "العلوي" in data["items"][0]["address"]

    def test_director_gets_property_by_id(self, client, director_token, db):
        prop = InvestmentProperty(
            property_type=PropertyType.KIOSK,
            address="الكشك الرئيسي",
            status=PropertyStatus.AVAILABLE,
        )
        db.add(prop)
        db.commit()
        db.refresh(prop)

        resp = client.get(f"/investment-properties/{prop.id}", headers=_auth(director_token))
        assert resp.status_code == 200
        data = resp.json()
        assert data["id"] == prop.id
        assert data["property_type"] == "kiosk"

    def test_director_updates_property(self, client, director_token, db):
        prop = InvestmentProperty(
            property_type=PropertyType.BUILDING,
            address="العنوان القديم",
            status=PropertyStatus.AVAILABLE,
        )
        db.add(prop)
        db.commit()
        db.refresh(prop)

        resp = client.put(
            f"/investment-properties/{prop.id}",
            json={"address": "العنوان الجديد", "status": "invested"},
            headers=_auth(director_token),
        )
        assert resp.status_code == 200
        data = resp.json()
        assert data["address"] == "العنوان الجديد"
        assert data["status"] == "invested"

    def test_director_updates_property_attachments(self, client, director_token, db):
        prop = InvestmentProperty(
            property_type=PropertyType.BUILDING,
            address="العنوان القديم",
            status=PropertyStatus.AVAILABLE,
        )
        db.add(prop)
        db.commit()
        db.refresh(prop)

        payload = {
            "property_images": ["/uploads/investment_contracts/new-image.jpg"],
            "property_documents": ["/uploads/investment_contracts/new-doc.pdf"],
            "owner_id_image": "/uploads/investment_contracts/owner.jpg",
            "additional_attachments": ["/uploads/investment_contracts/extra.docx"],
        }
        resp = client.put(
            f"/investment-properties/{prop.id}",
            json=payload,
            headers=_auth(director_token),
        )
        assert resp.status_code == 200
        data = resp.json()
        assert data["property_images"] == payload["property_images"]
        assert data["property_documents"] == payload["property_documents"]
        assert data["owner_id_image"] == payload["owner_id_image"]
        assert data["additional_attachments"] == payload["additional_attachments"]

    def test_director_deletes_property(self, client, director_token, db):
        prop = InvestmentProperty(
            property_type=PropertyType.LAND,
            address="أرض للحذف",
            status=PropertyStatus.AVAILABLE,
        )
        db.add(prop)
        db.commit()
        db.refresh(prop)

        resp = client.delete(
            f"/investment-properties/{prop.id}",
            headers=_auth(director_token),
        )
        assert resp.status_code == 200
        assert resp.json()["message"] == "Investment property deleted successfully"

        # Property should be soft-deleted (is_active=False)
        db.refresh(prop)
        assert prop.is_active is False

    def test_soft_deleted_not_in_list(self, client, director_token, db):
        active = InvestmentProperty(
            property_type=PropertyType.BUILDING,
            address="نشط",
            status=PropertyStatus.AVAILABLE,
            is_active=True,
        )
        inactive = InvestmentProperty(
            property_type=PropertyType.LAND,
            address="محذوف",
            status=PropertyStatus.AVAILABLE,
            is_active=False,
        )
        db.add_all([active, inactive])
        db.commit()

        resp = client.get("/investment-properties/", headers=_auth(director_token))
        assert resp.status_code == 200
        data = resp.json()
        assert data["total_count"] == 1
        assert data["items"][0]["address"] == "نشط"


# ---------------------------------------------------------------------------
# Contracts Manager
# ---------------------------------------------------------------------------

class TestContractsManagerPermissions:
    """Per the property module spec, contracts_manager has READ-ONLY access
    to investment properties (write access is now reserved to project_director
    and property_manager). Contracts_manager retains full CRUD on contracts."""

    def test_contracts_manager_cannot_create(self, client, db):
        from tests.conftest import _create_user, _login
        _create_user(db, "test_cm", UserRole.CONTRACTS_MANAGER)
        token = _login(client, "test_cm")

        resp = client.post(
            "/investment-properties/",
            json=_make_property_payload(),
            headers=_auth(token),
        )
        assert resp.status_code == 403

    def test_contracts_manager_cannot_update(self, client, db):
        from tests.conftest import _create_user, _login
        _create_user(db, "test_cm2", UserRole.CONTRACTS_MANAGER)
        token = _login(client, "test_cm2")

        prop = InvestmentProperty(
            property_type=PropertyType.SHOP,
            address="محل للتحديث",
            status=PropertyStatus.AVAILABLE,
        )
        db.add(prop)
        db.commit()
        db.refresh(prop)

        resp = client.put(
            f"/investment-properties/{prop.id}",
            json={"status": "maintenance"},
            headers=_auth(token),
        )
        assert resp.status_code == 403

    def test_contracts_manager_cannot_delete(self, client, db):
        from tests.conftest import _create_user, _login
        _create_user(db, "test_cm3", UserRole.CONTRACTS_MANAGER)
        token = _login(client, "test_cm3")

        prop = InvestmentProperty(
            property_type=PropertyType.LAND,
            address="أرض لحذف",
            status=PropertyStatus.AVAILABLE,
        )
        db.add(prop)
        db.commit()
        db.refresh(prop)

        resp = client.delete(f"/investment-properties/{prop.id}", headers=_auth(token))
        assert resp.status_code == 403

    def test_contracts_manager_can_list(self, client, db):
        from tests.conftest import _create_user, _login
        _create_user(db, "test_cm_list", UserRole.CONTRACTS_MANAGER)
        token = _login(client, "test_cm_list")

        db.add(InvestmentProperty(
            property_type=PropertyType.BUILDING, address="بناء",
            status=PropertyStatus.AVAILABLE,
        ))
        db.commit()

        resp = client.get("/investment-properties/", headers=_auth(token))
        assert resp.status_code == 200
        assert resp.json()["total_count"] == 1


# ---------------------------------------------------------------------------
# Property Manager (full CRUD on properties)
# ---------------------------------------------------------------------------

class TestPropertyManagerPermissions:
    def test_property_manager_can_create(self, client, db):
        from tests.conftest import _create_user, _login
        _create_user(db, "test_pm", UserRole.PROPERTY_MANAGER)
        token = _login(client, "test_pm")

        resp = client.post(
            "/investment-properties/",
            json=_make_property_payload(),
            headers=_auth(token),
        )
        assert resp.status_code == 201

    def test_property_manager_can_list_and_filter(self, client, db):
        from tests.conftest import _create_user, _login
        _create_user(db, "test_pm_list", UserRole.PROPERTY_MANAGER)
        token = _login(client, "test_pm_list")

        db.add(InvestmentProperty(
            property_type=PropertyType.BUILDING, address="بناء 1",
            status=PropertyStatus.AVAILABLE,
        ))
        db.add(InvestmentProperty(
            property_type=PropertyType.LAND, address="أرض 1",
            status=PropertyStatus.INVESTED,
        ))
        db.commit()

        resp = client.get("/investment-properties/?type=building", headers=_auth(token))
        assert resp.status_code == 200
        assert resp.json()["total_count"] == 1

    def test_property_manager_can_update(self, client, db):
        from tests.conftest import _create_user, _login
        _create_user(db, "test_pm_upd", UserRole.PROPERTY_MANAGER)
        token = _login(client, "test_pm_upd")

        prop = InvestmentProperty(
            property_type=PropertyType.SHOP, address="محل قديم",
            status=PropertyStatus.AVAILABLE,
        )
        db.add(prop)
        db.commit()
        db.refresh(prop)

        resp = client.put(
            f"/investment-properties/{prop.id}",
            json={"status": "maintenance"},
            headers=_auth(token),
        )
        assert resp.status_code == 200
        assert resp.json()["status"] == "maintenance"

    def test_property_manager_can_delete(self, client, db):
        from tests.conftest import _create_user, _login
        _create_user(db, "test_pm_del", UserRole.PROPERTY_MANAGER)
        token = _login(client, "test_pm_del")

        prop = InvestmentProperty(
            property_type=PropertyType.LAND, address="أرض للحذف",
            status=PropertyStatus.AVAILABLE,
        )
        db.add(prop)
        db.commit()
        db.refresh(prop)

        resp = client.delete(f"/investment-properties/{prop.id}", headers=_auth(token))
        assert resp.status_code == 200


# ---------------------------------------------------------------------------
# Investment Manager (read-only on properties; will manage contracts later)
# ---------------------------------------------------------------------------

class TestInvestmentManagerPermissions:
    def test_investment_manager_can_list(self, client, db):
        from tests.conftest import _create_user, _login
        _create_user(db, "test_im_list", UserRole.INVESTMENT_MANAGER)
        token = _login(client, "test_im_list")

        db.add(InvestmentProperty(
            property_type=PropertyType.RESTAURANT, address="مطعم",
            status=PropertyStatus.AVAILABLE,
        ))
        db.commit()

        resp = client.get("/investment-properties/", headers=_auth(token))
        assert resp.status_code == 200
        assert resp.json()["total_count"] == 1

    def test_investment_manager_can_get_by_id(self, client, db):
        from tests.conftest import _create_user, _login
        _create_user(db, "test_im_get", UserRole.INVESTMENT_MANAGER)
        token = _login(client, "test_im_get")

        prop = InvestmentProperty(
            property_type=PropertyType.KIOSK, address="كشك",
            status=PropertyStatus.AVAILABLE,
        )
        db.add(prop)
        db.commit()
        db.refresh(prop)

        resp = client.get(f"/investment-properties/{prop.id}", headers=_auth(token))
        assert resp.status_code == 200

    def test_investment_manager_cannot_create(self, client, db):
        from tests.conftest import _create_user, _login
        _create_user(db, "test_im_create", UserRole.INVESTMENT_MANAGER)
        token = _login(client, "test_im_create")

        resp = client.post(
            "/investment-properties/",
            json=_make_property_payload(),
            headers=_auth(token),
        )
        assert resp.status_code == 403

    def test_investment_manager_cannot_update(self, client, db):
        from tests.conftest import _create_user, _login
        _create_user(db, "test_im_upd", UserRole.INVESTMENT_MANAGER)
        token = _login(client, "test_im_upd")

        prop = InvestmentProperty(
            property_type=PropertyType.BUILDING, address="عقار",
            status=PropertyStatus.AVAILABLE,
        )
        db.add(prop)
        db.commit()
        db.refresh(prop)

        resp = client.put(
            f"/investment-properties/{prop.id}",
            json={"status": "invested"},
            headers=_auth(token),
        )
        assert resp.status_code == 403

    def test_investment_manager_cannot_delete(self, client, db):
        from tests.conftest import _create_user, _login
        _create_user(db, "test_im_del", UserRole.INVESTMENT_MANAGER)
        token = _login(client, "test_im_del")

        prop = InvestmentProperty(
            property_type=PropertyType.LAND, address="أرض",
            status=PropertyStatus.AVAILABLE,
        )
        db.add(prop)
        db.commit()
        db.refresh(prop)

        resp = client.delete(
            f"/investment-properties/{prop.id}",
            headers=_auth(token),
        )
        assert resp.status_code == 403


# ---------------------------------------------------------------------------
# New roles can be created via /users/ (admin path)
# ---------------------------------------------------------------------------

class TestNewRolesAdminCreation:
    def test_director_creates_property_manager_user(self, client, director_token):
        resp = client.post(
            "/users/",
            json={
                "username": "new_pm",
                "full_name": "مسؤول الأصول",
                "password": "testpass123",
                "role": "property_manager",
            },
            headers=_auth(director_token),
        )
        assert resp.status_code == 200
        assert resp.json()["role"] == "property_manager"

    def test_director_creates_investment_manager_user(self, client, director_token):
        resp = client.post(
            "/users/",
            json={
                "username": "new_im",
                "full_name": "مسؤول الاستثمار",
                "password": "testpass123",
                "role": "investment_manager",
            },
            headers=_auth(director_token),
        )
        assert resp.status_code == 200
        assert resp.json()["role"] == "investment_manager"


# ---------------------------------------------------------------------------
# Field Team (forbidden from write operations)
# ---------------------------------------------------------------------------

class TestFieldTeamForbidden:
    def test_field_team_cannot_create(self, client, field_token):
        resp = client.post(
            "/investment-properties/",
            json=_make_property_payload(),
            headers=_auth(field_token),
        )
        assert resp.status_code == 403

    def test_field_team_cannot_update(self, client, field_token, db):
        prop = InvestmentProperty(
            property_type=PropertyType.BUILDING,
            address="عقار",
            status=PropertyStatus.AVAILABLE,
        )
        db.add(prop)
        db.commit()
        db.refresh(prop)

        resp = client.put(
            f"/investment-properties/{prop.id}",
            json={"status": "invested"},
            headers=_auth(field_token),
        )
        assert resp.status_code == 403

    def test_field_team_cannot_delete(self, client, field_token, db):
        prop = InvestmentProperty(
            property_type=PropertyType.LAND,
            address="أرض",
            status=PropertyStatus.AVAILABLE,
        )
        db.add(prop)
        db.commit()
        db.refresh(prop)

        resp = client.delete(
            f"/investment-properties/{prop.id}",
            headers=_auth(field_token),
        )
        assert resp.status_code == 403


# ---------------------------------------------------------------------------
# Contractor User (forbidden from create)
# ---------------------------------------------------------------------------

class TestContractorForbidden:
    def test_contractor_cannot_create(self, client, contractor_token):
        resp = client.post(
            "/investment-properties/",
            json=_make_property_payload(),
            headers=_auth(contractor_token),
        )
        assert resp.status_code == 403

    def test_contractor_cannot_update(self, client, contractor_token, db):
        prop = InvestmentProperty(
            property_type=PropertyType.SHOP,
            address="محل",
            status=PropertyStatus.AVAILABLE,
        )
        db.add(prop)
        db.commit()
        db.refresh(prop)

        resp = client.put(
            f"/investment-properties/{prop.id}",
            json={"status": "unfit"},
            headers=_auth(contractor_token),
        )
        assert resp.status_code == 403

    def test_contractor_cannot_delete(self, client, contractor_token, db):
        prop = InvestmentProperty(
            property_type=PropertyType.LAND,
            address="أرض ثانية",
            status=PropertyStatus.AVAILABLE,
        )
        db.add(prop)
        db.commit()
        db.refresh(prop)

        resp = client.delete(
            f"/investment-properties/{prop.id}",
            headers=_auth(contractor_token),
        )
        assert resp.status_code == 403


# ---------------------------------------------------------------------------
# Citizen (forbidden from all management endpoints)
# ---------------------------------------------------------------------------

class TestCitizenForbidden:
    def test_citizen_cannot_list(self, client, citizen_token):
        resp = client.get("/investment-properties/", headers=_auth(citizen_token))
        assert resp.status_code == 403

    def test_citizen_cannot_create(self, client, citizen_token):
        resp = client.post(
            "/investment-properties/",
            json=_make_property_payload(),
            headers=_auth(citizen_token),
        )
        assert resp.status_code == 403

    def test_citizen_cannot_get_by_id(self, client, citizen_token, db):
        prop = InvestmentProperty(
            property_type=PropertyType.BUILDING,
            address="عقار للمواطن",
            status=PropertyStatus.AVAILABLE,
        )
        db.add(prop)
        db.commit()
        db.refresh(prop)

        resp = client.get(f"/investment-properties/{prop.id}", headers=_auth(citizen_token))
        assert resp.status_code == 403


# ---------------------------------------------------------------------------
# Validation errors
# ---------------------------------------------------------------------------

class TestValidation:
    def test_invalid_property_type_returns_422(self, client, director_token):
        resp = client.post(
            "/investment-properties/",
            json=_make_property_payload(property_type="invalid_type"),
            headers=_auth(director_token),
        )
        assert resp.status_code == 422

    def test_invalid_status_returns_422(self, client, director_token):
        resp = client.post(
            "/investment-properties/",
            json=_make_property_payload(status="bad_status"),
            headers=_auth(director_token),
        )
        assert resp.status_code == 422

    def test_missing_required_address_returns_422(self, client, director_token):
        payload = {
            "property_type": "building",
            "status": "available",
        }
        resp = client.post(
            "/investment-properties/",
            json=payload,
            headers=_auth(director_token),
        )
        assert resp.status_code == 422

    def test_missing_required_type_returns_422(self, client, director_token):
        payload = {
            "address": "شارع ما",
            "status": "available",
        }
        resp = client.post(
            "/investment-properties/",
            json=payload,
            headers=_auth(director_token),
        )
        assert resp.status_code == 422

    def test_get_nonexistent_returns_404(self, client, director_token):
        resp = client.get("/investment-properties/99999", headers=_auth(director_token))
        assert resp.status_code == 404

    def test_update_nonexistent_returns_404(self, client, director_token):
        resp = client.put(
            "/investment-properties/99999",
            json={"status": "invested"},
            headers=_auth(director_token),
        )
        assert resp.status_code == 404
