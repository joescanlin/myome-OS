"""Family document processing and data extraction"""

import re
from dataclasses import dataclass, field
from datetime import UTC, datetime


@dataclass
class ExtractedBiomarker:
    """Extracted biomarker from document"""

    name: str
    value: float
    unit: str
    reference_range: str | None = None
    is_abnormal: bool | None = None
    confidence: float = 1.0


@dataclass
class ExtractedCondition:
    """Extracted medical condition from document"""

    name: str
    icd_code: str | None = None
    onset_date: str | None = None
    status: str = "active"  # active, resolved, chronic
    confidence: float = 1.0


@dataclass
class ExtractedMedication:
    """Extracted medication from document"""

    name: str
    dosage: str | None = None
    frequency: str | None = None
    confidence: float = 1.0


@dataclass
class DocumentExtractionResult:
    """Result of document extraction"""

    document_type: str
    document_date: datetime | None = None
    biomarkers: list[ExtractedBiomarker] = field(default_factory=list)
    conditions: list[ExtractedCondition] = field(default_factory=list)
    medications: list[ExtractedMedication] = field(default_factory=list)
    raw_text: str | None = None
    overall_confidence: float = 1.0
    extraction_notes: list[str] = field(default_factory=list)


# Common biomarker patterns for regex extraction
BIOMARKER_PATTERNS = {
    "ldl": {
        "patterns": [
            r"LDL[:\s-]*(\d+(?:\.\d+)?)\s*(mg/dL|mmol/L)?",
            r"LDL Cholesterol[:\s-]*(\d+(?:\.\d+)?)",
            r"Low Density Lipoprotein[:\s-]*(\d+(?:\.\d+)?)",
        ],
        "unit": "mg/dL",
        "normal_range": (0, 100),
    },
    "hdl": {
        "patterns": [
            r"HDL[:\s-]*(\d+(?:\.\d+)?)\s*(mg/dL|mmol/L)?",
            r"HDL Cholesterol[:\s-]*(\d+(?:\.\d+)?)",
            r"High Density Lipoprotein[:\s-]*(\d+(?:\.\d+)?)",
        ],
        "unit": "mg/dL",
        "normal_range": (40, 200),
    },
    "total_cholesterol": {
        "patterns": [
            r"Total Cholesterol[:\s-]*(\d+(?:\.\d+)?)",
            r"Cholesterol, Total[:\s-]*(\d+(?:\.\d+)?)",
        ],
        "unit": "mg/dL",
        "normal_range": (0, 200),
    },
    "triglycerides": {
        "patterns": [
            r"Triglycerides?[:\s-]*(\d+(?:\.\d+)?)",
        ],
        "unit": "mg/dL",
        "normal_range": (0, 150),
    },
    "hba1c": {
        "patterns": [
            r"HbA1c[:\s-]*(\d+(?:\.\d+)?)\s*%?",
            r"A1C[:\s-]*(\d+(?:\.\d+)?)\s*%?",
            r"Hemoglobin A1c[:\s-]*(\d+(?:\.\d+)?)",
            r"Glycated Hemoglobin[:\s-]*(\d+(?:\.\d+)?)",
        ],
        "unit": "%",
        "normal_range": (4.0, 5.7),
    },
    "fasting_glucose": {
        "patterns": [
            r"Fasting Glucose[:\s-]*(\d+(?:\.\d+)?)",
            r"Glucose, Fasting[:\s-]*(\d+(?:\.\d+)?)",
            r"FBG[:\s-]*(\d+(?:\.\d+)?)",
        ],
        "unit": "mg/dL",
        "normal_range": (70, 100),
    },
    "blood_pressure_systolic": {
        "patterns": [
            r"(?:Blood Pressure|BP)[:\s-]*(\d{2,3})/\d{2,3}",
            r"Systolic[:\s-]*(\d{2,3})",
        ],
        "unit": "mmHg",
        "normal_range": (90, 120),
    },
    "blood_pressure_diastolic": {
        "patterns": [
            r"(?:Blood Pressure|BP)[:\s-]*\d{2,3}/(\d{2,3})",
            r"Diastolic[:\s-]*(\d{2,3})",
        ],
        "unit": "mmHg",
        "normal_range": (60, 80),
    },
    "creatinine": {
        "patterns": [
            r"Creatinine[:\s-]*(\d+(?:\.\d+)?)",
        ],
        "unit": "mg/dL",
        "normal_range": (0.6, 1.2),
    },
    "egfr": {
        "patterns": [
            r"eGFR[:\s-]*(\d+(?:\.\d+)?)",
            r"GFR[:\s-]*(\d+(?:\.\d+)?)",
        ],
        "unit": "mL/min/1.73m2",
        "normal_range": (90, 200),
    },
}

# Common condition patterns
CONDITION_PATTERNS = {
    "type_2_diabetes": [
        r"Type 2 Diabetes",
        r"T2DM",
        r"Diabetes Mellitus Type 2",
        r"Type II Diabetes",
        r"NIDDM",
    ],
    "type_1_diabetes": [
        r"Type 1 Diabetes",
        r"T1DM",
        r"Diabetes Mellitus Type 1",
        r"Type I Diabetes",
        r"IDDM",
    ],
    "hypertension": [
        r"Hypertension",
        r"High Blood Pressure",
        r"HTN",
        r"Elevated BP",
    ],
    "hyperlipidemia": [
        r"Hyperlipidemia",
        r"High Cholesterol",
        r"Dyslipidemia",
        r"Hypercholesterolemia",
    ],
    "coronary_artery_disease": [
        r"Coronary Artery Disease",
        r"CAD",
        r"Coronary Heart Disease",
        r"CHD",
        r"Ischemic Heart Disease",
    ],
    "myocardial_infarction": [
        r"Myocardial Infarction",
        r"MI",
        r"Heart Attack",
        r"STEMI",
        r"NSTEMI",
    ],
    "stroke": [
        r"Stroke",
        r"CVA",
        r"Cerebrovascular Accident",
        r"TIA",
        r"Transient Ischemic Attack",
    ],
    "atrial_fibrillation": [
        r"Atrial Fibrillation",
        r"AFib",
        r"A-Fib",
        r"AF",
    ],
    "chronic_kidney_disease": [
        r"Chronic Kidney Disease",
        r"CKD",
        r"Renal Insufficiency",
    ],
    "copd": [
        r"COPD",
        r"Chronic Obstructive Pulmonary",
        r"Emphysema",
        r"Chronic Bronchitis",
    ],
}


class FamilyDocumentProcessor:
    """
    Process uploaded family medical documents

    Extracts biomarkers, conditions, and medications from
    lab reports, discharge summaries, and other medical documents.
    """

    def __init__(self):
        self.biomarker_patterns = BIOMARKER_PATTERNS
        self.condition_patterns = CONDITION_PATTERNS

    async def process_document(
        self,
        text: str,
        document_type: str = "unknown",
        relative_age_at_document: int | None = None,
    ) -> DocumentExtractionResult:
        """
        Process document text and extract medical data

        Args:
            text: Raw text from document (after OCR if needed)
            document_type: Type of document (lab_report, discharge_summary, etc.)
            relative_age_at_document: Age of family member at time of document
        """
        result = DocumentExtractionResult(
            document_type=document_type,
            raw_text=text,
        )

        # Detect document type if not provided
        if document_type == "unknown":
            result.document_type = self._detect_document_type(text)

        # Extract document date
        result.document_date = self._extract_date(text)

        # Extract biomarkers
        result.biomarkers = self._extract_biomarkers(text)

        # Extract conditions
        result.conditions = self._extract_conditions(text)

        # Extract medications
        result.medications = self._extract_medications(text)

        # Calculate overall confidence
        if result.biomarkers or result.conditions:
            confidences = [b.confidence for b in result.biomarkers] + [
                c.confidence for c in result.conditions
            ]
            result.overall_confidence = sum(confidences) / len(confidences)
        else:
            result.overall_confidence = 0.5
            result.extraction_notes.append("Limited data extracted from document")

        return result

    def _detect_document_type(self, text: str) -> str:
        """Detect document type from content"""
        text_lower = text.lower()

        if any(
            term in text_lower
            for term in ["lab result", "laboratory", "blood test", "lipid panel"]
        ):
            return "lab_report"
        if any(
            term in text_lower
            for term in ["discharge summary", "hospital discharge", "admission"]
        ):
            return "discharge_summary"
        if any(
            term in text_lower for term in ["prescription", "rx", "medication list"]
        ):
            return "prescription"
        if any(
            term in text_lower
            for term in ["annual physical", "wellness visit", "checkup"]
        ):
            return "physical_exam"

        return "medical_record"

    def _extract_date(self, text: str) -> datetime | None:
        """Extract document date"""
        # Common date patterns
        patterns = [
            r"Date[:\s]*(\d{1,2}[/-]\d{1,2}[/-]\d{2,4})",
            r"(\d{1,2}[/-]\d{1,2}[/-]\d{2,4})",
            r"(\w+ \d{1,2},? \d{4})",
        ]

        for pattern in patterns:
            match = re.search(pattern, text, re.IGNORECASE)
            if match:
                try:
                    date_str = match.group(1)
                    # Try common formats
                    for fmt in [
                        "%m/%d/%Y",
                        "%m-%d-%Y",
                        "%m/%d/%y",
                        "%B %d, %Y",
                        "%B %d %Y",
                    ]:
                        try:
                            return datetime.strptime(date_str, fmt).replace(tzinfo=UTC)
                        except ValueError:
                            continue
                except Exception:
                    continue

        return None

    def _extract_biomarkers(self, text: str) -> list[ExtractedBiomarker]:
        """Extract biomarkers from text"""
        biomarkers = []

        for name, config in self.biomarker_patterns.items():
            for pattern in config["patterns"]:
                match = re.search(pattern, text, re.IGNORECASE)
                if match:
                    try:
                        value = float(match.group(1))

                        # Check if abnormal
                        normal_min, normal_max = config["normal_range"]
                        is_abnormal = value < normal_min or value > normal_max

                        biomarkers.append(
                            ExtractedBiomarker(
                                name=name,
                                value=value,
                                unit=config["unit"],
                                reference_range=f"{normal_min}-{normal_max}",
                                is_abnormal=is_abnormal,
                                confidence=0.9,
                            )
                        )
                        break  # Found match, move to next biomarker
                    except (ValueError, IndexError):
                        continue

        return biomarkers

    def _extract_conditions(self, text: str) -> list[ExtractedCondition]:
        """Extract medical conditions from text"""
        conditions = []

        for condition_name, patterns in self.condition_patterns.items():
            for pattern in patterns:
                if re.search(pattern, text, re.IGNORECASE):
                    conditions.append(
                        ExtractedCondition(
                            name=condition_name,
                            status="active",
                            confidence=0.85,
                        )
                    )
                    break

        return conditions

    def _extract_medications(self, text: str) -> list[ExtractedMedication]:
        """Extract medications from text"""
        medications = []

        # Common medication patterns
        common_meds = [
            ("metformin", r"Metformin\s*(?:(\d+\s*mg))?"),
            ("lisinopril", r"Lisinopril\s*(?:(\d+\s*mg))?"),
            ("atorvastatin", r"(?:Atorvastatin|Lipitor)\s*(?:(\d+\s*mg))?"),
            ("simvastatin", r"(?:Simvastatin|Zocor)\s*(?:(\d+\s*mg))?"),
            ("amlodipine", r"(?:Amlodipine|Norvasc)\s*(?:(\d+\s*mg))?"),
            ("metoprolol", r"(?:Metoprolol|Lopressor)\s*(?:(\d+\s*mg))?"),
            ("omeprazole", r"(?:Omeprazole|Prilosec)\s*(?:(\d+\s*mg))?"),
            ("levothyroxine", r"(?:Levothyroxine|Synthroid)\s*(?:(\d+\s*mcg))?"),
            ("aspirin", r"Aspirin\s*(?:(\d+\s*mg))?"),
            ("warfarin", r"(?:Warfarin|Coumadin)\s*(?:(\d+\s*mg))?"),
        ]

        for med_name, pattern in common_meds:
            match = re.search(pattern, text, re.IGNORECASE)
            if match:
                dosage = match.group(1) if match.lastindex and match.group(1) else None
                medications.append(
                    ExtractedMedication(
                        name=med_name,
                        dosage=dosage,
                        confidence=0.8,
                    )
                )

        return medications

    def convert_to_family_member_data(
        self,
        extraction: DocumentExtractionResult,
        relationship: str,
        age_at_document: int | None = None,
    ) -> dict:
        """
        Convert extraction result to FamilyMember-compatible format

        Args:
            extraction: Document extraction result
            relationship: Relationship to user
            age_at_document: Age of relative at time of document
        """
        # Convert biomarkers to storage format
        biomarkers = {}
        for b in extraction.biomarkers:
            biomarkers[b.name] = {
                "value": b.value,
                "unit": b.unit,
                "age_at_measurement": age_at_document,
                "is_abnormal": b.is_abnormal,
            }

        # Convert conditions to storage format
        conditions = [
            {
                "condition": c.name,
                "onset_age": None,  # Would need to be manually specified
                "current": c.status == "active",
            }
            for c in extraction.conditions
        ]

        # Convert medications
        medications = [
            {
                "name": m.name,
                "dosage": m.dosage,
            }
            for m in extraction.medications
        ]

        return {
            "relationship": relationship,
            "biomarkers": biomarkers,
            "conditions": conditions,
            "medications": medications,
            "data_source": "document",
            "confidence_score": extraction.overall_confidence,
        }
