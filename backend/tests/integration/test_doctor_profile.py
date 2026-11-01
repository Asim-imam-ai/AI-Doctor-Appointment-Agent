import uuid
from unittest.mock import MagicMock

from fastapi.testclient import TestClient

from app.api.v1 import doctors as doctor_routes
from app.domain.doctors.models import DoctorModel, SpecialtyModel
from app.main import app


def test_active_doctor_profile_returns_search_fields(monkeypatch):
    doctor = DoctorModel(
        name="Dr. Khan", clinic_name="Clinic", location="Karachi", bio="Consultations."
    )
    service = MagicMock()
    service.get_doctor.return_value = doctor
    service.get_doctor_specialties.return_value = [SpecialtyModel(name="Cardiology")]
    monkeypatch.setattr(doctor_routes, "get_doctor_service", lambda: service)

    response = TestClient(app).get(f"/api/v1/doctors/{doctor.id}")

    assert response.status_code == 200
    assert response.json() == {
        "id": str(doctor.id),
        "name": "Dr. Khan",
        "specialties": ["Cardiology"],
        "clinic_name": "Clinic",
        "location": "Karachi",
        "bio": "Consultations.",
        "consultation_duration": 30,
        "is_active": True,
    }
    service.get_doctor.assert_called_once_with(doctor.id)
    service.get_doctor_specialties.assert_called_once_with(doctor.id)


def test_missing_and_inactive_doctors_are_not_exposed(monkeypatch):
    doctor = DoctorModel(name="Inactive", is_active=False)
    service = MagicMock()
    service.get_doctor.side_effect = [None, doctor]
    monkeypatch.setattr(doctor_routes, "get_doctor_service", lambda: service)
    client = TestClient(app)

    assert client.get(f"/api/v1/doctors/{uuid.uuid4()}").status_code == 404
    assert client.get(f"/api/v1/doctors/{doctor.id}").status_code == 404
    assert client.get("/api/v1/doctors/not-a-uuid").status_code == 422
    service.get_doctor_specialties.assert_not_called()
