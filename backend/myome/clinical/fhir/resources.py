"""FHIR resource generation"""

from datetime import datetime, timezone
from typing import Optional
from uuid import uuid4


class FHIRResourceGenerator:
    """Generate HL7 FHIR resources from Myome data"""
    
    def __init__(self, user_id: str):
        self.user_id = user_id
    
    def create_patient(self, user_data: dict) -> dict:
        """Create FHIR Patient resource"""
        return {
            "resourceType": "Patient",
            "id": self.user_id,
            "meta": {
                "lastUpdated": datetime.now(timezone.utc).isoformat(),
            },
            "name": [{
                "use": "official",
                "family": user_data.get("last_name", ""),
                "given": [user_data.get("first_name", "")],
            }],
            "birthDate": user_data.get("date_of_birth"),
            "gender": self._map_gender(user_data.get("biological_sex")),
        }
    
    def create_observation(
        self,
        code: str,
        display: str,
        value: float,
        unit: str,
        timestamp: datetime,
        category: str = "vital-signs",
    ) -> dict:
        """Create FHIR Observation resource"""
        return {
            "resourceType": "Observation",
            "id": str(uuid4()),
            "meta": {
                "lastUpdated": datetime.now(timezone.utc).isoformat(),
            },
            "status": "final",
            "category": [{
                "coding": [{
                    "system": "http://terminology.hl7.org/CodeSystem/observation-category",
                    "code": category,
                    "display": category.replace("-", " ").title(),
                }]
            }],
            "code": {
                "coding": [{
                    "system": "http://loinc.org",
                    "code": code,
                    "display": display,
                }]
            },
            "subject": {
                "reference": f"Patient/{self.user_id}",
            },
            "effectiveDateTime": timestamp.isoformat() if timestamp.tzinfo else timestamp.isoformat() + "Z",
            "valueQuantity": {
                "value": value,
                "unit": unit,
                "system": "http://unitsofmeasure.org",
            },
        }
    
    def create_heart_rate_observation(self, hr_bpm: int, timestamp: datetime) -> dict:
        """Create heart rate FHIR observation"""
        return self.create_observation(
            code="8867-4",
            display="Heart rate",
            value=hr_bpm,
            unit="beats/minute",
            timestamp=timestamp,
        )
    
    def create_glucose_observation(self, glucose_mg_dl: float, timestamp: datetime) -> dict:
        """Create glucose FHIR observation"""
        return self.create_observation(
            code="2345-7",
            display="Glucose [Mass/volume] in Serum or Plasma",
            value=glucose_mg_dl,
            unit="mg/dL",
            timestamp=timestamp,
            category="laboratory",
        )
    
    def create_hrv_observation(self, sdnn_ms: float, timestamp: datetime) -> dict:
        """Create HRV SDNN FHIR observation"""
        return self.create_observation(
            code="80404-7",
            display="Heart rate variability SDNN",
            value=sdnn_ms,
            unit="ms",
            timestamp=timestamp,
        )
    
    def create_body_weight_observation(self, weight_kg: float, timestamp: datetime) -> dict:
        """Create body weight FHIR observation"""
        return self.create_observation(
            code="29463-7",
            display="Body weight",
            value=weight_kg,
            unit="kg",
            timestamp=timestamp,
        )
    
    def create_blood_pressure_observation(
        self,
        systolic: int,
        diastolic: int,
        timestamp: datetime,
    ) -> dict:
        """Create blood pressure FHIR observation with multiple components"""
        return {
            "resourceType": "Observation",
            "id": str(uuid4()),
            "meta": {
                "lastUpdated": datetime.now(timezone.utc).isoformat(),
            },
            "status": "final",
            "category": [{
                "coding": [{
                    "system": "http://terminology.hl7.org/CodeSystem/observation-category",
                    "code": "vital-signs",
                    "display": "Vital Signs",
                }]
            }],
            "code": {
                "coding": [{
                    "system": "http://loinc.org",
                    "code": "85354-9",
                    "display": "Blood pressure panel with all children optional",
                }]
            },
            "subject": {
                "reference": f"Patient/{self.user_id}",
            },
            "effectiveDateTime": timestamp.isoformat() if timestamp.tzinfo else timestamp.isoformat() + "Z",
            "component": [
                {
                    "code": {
                        "coding": [{
                            "system": "http://loinc.org",
                            "code": "8480-6",
                            "display": "Systolic blood pressure",
                        }]
                    },
                    "valueQuantity": {
                        "value": systolic,
                        "unit": "mmHg",
                        "system": "http://unitsofmeasure.org",
                        "code": "mm[Hg]",
                    },
                },
                {
                    "code": {
                        "coding": [{
                            "system": "http://loinc.org",
                            "code": "8462-4",
                            "display": "Diastolic blood pressure",
                        }]
                    },
                    "valueQuantity": {
                        "value": diastolic,
                        "unit": "mmHg",
                        "system": "http://unitsofmeasure.org",
                        "code": "mm[Hg]",
                    },
                },
            ],
        }
    
    def create_diagnostic_report(
        self,
        report_data: dict,
        observations: list[dict],
    ) -> dict:
        """Create FHIR DiagnosticReport from physician report"""
        return {
            "resourceType": "DiagnosticReport",
            "id": str(uuid4()),
            "meta": {
                "lastUpdated": datetime.now(timezone.utc).isoformat(),
            },
            "status": "final",
            "category": [{
                "coding": [{
                    "system": "http://terminology.hl7.org/CodeSystem/v2-0074",
                    "code": "OTH",
                    "display": "Other",
                }],
                "text": "Personal Health Monitoring Summary",
            }],
            "code": {
                "coding": [{
                    "system": "http://loinc.org",
                    "code": "77599-9",
                    "display": "Additional documentation",
                }],
                "text": "Myome Continuous Health Monitoring Report",
            },
            "subject": {
                "reference": f"Patient/{self.user_id}",
            },
            "effectivePeriod": {
                "start": report_data["metadata"]["period_start"],
                "end": report_data["metadata"]["period_end"],
            },
            "issued": report_data["metadata"]["generated_at"],
            "performer": [{
                "reference": "Device/myome-system",
                "display": "Myome Health Monitoring System",
            }],
            "result": [
                {"reference": f"Observation/{obs['id']}", "display": obs["code"]["coding"][0]["display"]}
                for obs in observations[:10]  # Limit to 10 key observations
            ],
            "conclusion": self._generate_conclusion(report_data),
        }
    
    def create_bundle(self, resources: list[dict]) -> dict:
        """Create FHIR Bundle containing multiple resources"""
        return {
            "resourceType": "Bundle",
            "id": str(uuid4()),
            "meta": {
                "lastUpdated": datetime.now(timezone.utc).isoformat(),
            },
            "type": "collection",
            "total": len(resources),
            "entry": [
                {"resource": resource}
                for resource in resources
            ],
        }
    
    def _map_gender(self, biological_sex: Optional[str]) -> str:
        """Map biological sex to FHIR gender"""
        mapping = {
            "male": "male",
            "female": "female",
            "other": "other",
        }
        return mapping.get(biological_sex, "unknown") if biological_sex else "unknown"
    
    def _generate_conclusion(self, report_data: dict) -> str:
        """Generate report conclusion text"""
        summary = report_data.get("executive_summary", {})
        status = summary.get("overall_status", "unknown")
        
        alerts = summary.get("critical_alerts", [])
        if alerts:
            alert_text = f" {len(alerts)} critical alert(s) require attention."
        else:
            alert_text = ""
        
        score = summary.get("health_score", {}).get("score")
        score_text = f" Overall health score: {score}/100." if score else ""
        
        return f"Monitoring period summary: Status {status}.{alert_text}{score_text}"
