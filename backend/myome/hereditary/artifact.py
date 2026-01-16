"""Hereditary health artifact generation"""

from dataclasses import dataclass, field
from datetime import datetime, timedelta, timezone
from typing import Optional
from uuid import uuid4
import json
import hashlib
import base64

from myome.analytics.data_loader import TimeSeriesLoader
from myome.core.logging import logger


@dataclass
class PrivacySettings:
    """Privacy settings for artifact generation"""
    exclude_categories: list[str] = field(default_factory=list)
    anonymize_location: bool = True
    include_interpretations: bool = True
    include_raw_data: bool = False


@dataclass
class ArtifactRecipient:
    """Recipient of hereditary artifact"""
    name: str
    public_key: Optional[str] = None
    relationship: str = "descendant"
    access_level: str = "full"  # full, summary, genetic_only


class HereditaryArtifact:
    """
    Hereditary Health Artifact
    
    A comprehensive, encrypted health record designed for
    multi-generational transfer.
    """
    
    VERSION = "1.0.0"
    
    def __init__(self, user_id: str):
        self.user_id = user_id
        self.artifact_id = str(uuid4())
        self.created_at = datetime.now(timezone.utc)
        self.loader = TimeSeriesLoader(user_id)
        
        self._data: dict = {}
        self._encrypted: bool = False
    
    async def generate(
        self,
        privacy_settings: PrivacySettings,
        start_date: Optional[datetime] = None,
        end_date: Optional[datetime] = None,
        family_members: Optional[list] = None,
    ) -> dict:
        """
        Generate hereditary artifact from user health data
        
        Args:
            privacy_settings: Privacy configuration
            start_date: Start of data collection period
            end_date: End of data collection period
            family_members: List of FamilyMember objects to include
        """
        if end_date is None:
            end_date = datetime.now(timezone.utc)
        if start_date is None:
            start_date = end_date - timedelta(days=365 * 5)
        
        self._data = {
            "artifact_version": self.VERSION,
            "artifact_id": self.artifact_id,
            "created_at": self.created_at.isoformat(),
            "signature": None,
            
            "donor": await self._generate_donor_metadata(start_date, end_date),
            "genomic_data": await self._generate_genomic_section(privacy_settings),
            "biomarker_trajectories": await self._generate_biomarker_trajectories(
                start_date, end_date, privacy_settings
            ),
            "family_history": self._generate_family_history(family_members, privacy_settings),
            "disease_events": await self._generate_disease_events(privacy_settings),
            "environmental_lifestyle": await self._generate_lifestyle_section(privacy_settings),
            "interpretation_for_descendants": await self._generate_interpretations(privacy_settings),
            "privacy_settings": {
                "excluded_data": privacy_settings.exclude_categories,
                "anonymized": privacy_settings.anonymize_location,
            },
        }
        
        return self._data
    
    async def _generate_donor_metadata(
        self,
        start_date: datetime,
        end_date: datetime,
    ) -> dict:
        """Generate donor identification section"""
        id_hash = hashlib.sha256(self.user_id.encode()).hexdigest()
        
        return {
            "id_hash": f"sha256:{id_hash[:16]}",
            "data_collection_period": {
                "start": start_date.isoformat(),
                "end": end_date.isoformat(),
                "duration_days": (end_date - start_date).days,
            },
        }
    
    async def _generate_genomic_section(
        self,
        privacy_settings: PrivacySettings,
    ) -> dict:
        """Generate genomic data section"""
        if "genetic" in privacy_settings.exclude_categories:
            return {"excluded": True, "reason": "user_preference"}
        
        return {
            "pathogenic_variants": [],
            "polygenic_risk_scores": {},
            "pharmacogenomics": {},
            "note": "Genomic data not yet imported",
        }
    
    async def _generate_biomarker_trajectories(
        self,
        start_date: datetime,
        end_date: datetime,
        privacy_settings: PrivacySettings,
    ) -> dict:
        """Generate biomarker trajectory summaries"""
        trajectories = {}
        
        # Heart rate trajectory
        try:
            hr_df = await self.loader.load_heart_rate(start_date, end_date, resample='1M')
            if not hr_df.empty:
                trajectories["resting_heart_rate"] = {
                    "unit": "bpm",
                    "measurement_frequency": "continuous",
                    "data_points": len(hr_df),
                    "summary_statistics": self._compute_trajectory_stats(hr_df['heart_rate_bpm']),
                }
        except Exception as e:
            logger.warning(f"Failed to load heart rate: {e}")
        
        # Glucose trajectory
        try:
            glucose_df = await self.loader.load_glucose(start_date, end_date, resample='1M')
            if not glucose_df.empty:
                trajectories["glucose"] = {
                    "unit": "mg/dL",
                    "measurement_frequency": "continuous",
                    "data_points": len(glucose_df),
                    "summary_statistics": self._compute_trajectory_stats(glucose_df['glucose_mg_dl']),
                }
        except Exception as e:
            logger.warning(f"Failed to load glucose: {e}")
        
        # HRV trajectory
        try:
            hrv_df = await self.loader.load_hrv(start_date, end_date, resample='1M')
            if not hrv_df.empty and 'sdnn_ms' in hrv_df.columns:
                trajectories["hrv_sdnn"] = {
                    "unit": "ms",
                    "measurement_frequency": "daily",
                    "data_points": len(hrv_df),
                    "summary_statistics": self._compute_trajectory_stats(hrv_df['sdnn_ms'].dropna()),
                }
        except Exception as e:
            logger.warning(f"Failed to load HRV: {e}")
        
        # Sleep trajectory
        try:
            sleep_df = await self.loader.load_sleep(start_date, end_date)
            if not sleep_df.empty:
                trajectories["sleep_duration"] = {
                    "unit": "minutes",
                    "measurement_frequency": "nightly",
                    "data_points": len(sleep_df),
                    "summary_statistics": self._compute_trajectory_stats(sleep_df['total_sleep_minutes']),
                }
        except Exception as e:
            logger.warning(f"Failed to load sleep: {e}")
        
        return trajectories
    
    def _compute_trajectory_stats(self, series) -> dict:
        """Compute summary statistics for a trajectory"""
        if series.empty:
            return {}
        
        import numpy as np
        
        return {
            "overall": {
                "mean": float(series.mean()),
                "std": float(series.std()) if len(series) > 1 else 0.0,
                "min": float(series.min()),
                "max": float(series.max()),
                "count": int(len(series)),
            },
            "trend": self._compute_trend(series),
        }
    
    def _compute_trend(self, series) -> dict:
        """Compute trend analysis"""
        import numpy as np
        
        if len(series) < 3:
            return {"direction": "insufficient_data"}
        
        x = np.arange(len(series))
        y = series.values
        valid = ~np.isnan(y)
        
        if valid.sum() < 3:
            return {"direction": "insufficient_data"}
        
        coeffs = np.polyfit(x[valid], y[valid], 1)
        slope = coeffs[0]
        
        return {
            "direction": "increasing" if slope > 0.01 else "decreasing" if slope < -0.01 else "stable",
            "slope_per_period": float(slope),
        }
    
    def _generate_family_history(
        self,
        family_members: Optional[list],
        privacy_settings: PrivacySettings,
    ) -> dict:
        """Generate family history section from FamilyMember records"""
        if "family" in privacy_settings.exclude_categories:
            return {"excluded": True, "reason": "user_preference"}
        
        if not family_members:
            return {"members": [], "note": "No family history recorded"}
        
        members_data = []
        for member in family_members:
            member_data = {
                "relationship": member.relationship,
                "relatedness": member.relatedness,
                "is_living": member.is_living,
            }
            
            if member.birth_year:
                member_data["birth_year"] = member.birth_year
            if member.death_year:
                member_data["death_year"] = member.death_year
                member_data["age_at_death"] = member.age_at_death
            if member.cause_of_death:
                member_data["cause_of_death"] = member.cause_of_death
            if member.conditions:
                member_data["conditions"] = member.conditions
            if member.biomarkers:
                member_data["biomarkers"] = member.biomarkers
            
            members_data.append(member_data)
        
        return {
            "members": members_data,
            "total_relatives": len(members_data),
        }
    
    async def _generate_disease_events(
        self,
        privacy_settings: PrivacySettings,
    ) -> list:
        """Generate disease events section"""
        return []
    
    async def _generate_lifestyle_section(
        self,
        privacy_settings: PrivacySettings,
    ) -> dict:
        """Generate lifestyle and environmental section"""
        if "lifestyle" in privacy_settings.exclude_categories:
            return {"excluded": True}
        
        return {
            "exercise": {},
            "diet": {},
            "sleep": {},
            "note": "Detailed lifestyle data not yet imported",
        }
    
    async def _generate_interpretations(
        self,
        privacy_settings: PrivacySettings,
    ) -> dict:
        """Generate interpretation for descendants"""
        if not privacy_settings.include_interpretations:
            return {}
        
        return {
            "key_findings": [
                "Health data collection in progress",
                "Biomarker trajectories being tracked",
            ],
            "recommendations_for_carriers": [
                "Continue health monitoring",
                "Share findings with healthcare provider",
            ],
        }
    
    def encrypt(self, password: str) -> bytes:
        """Encrypt artifact with password"""
        try:
            from cryptography.fernet import Fernet
            from cryptography.hazmat.primitives import hashes
            from cryptography.hazmat.primitives.kdf.pbkdf2 import PBKDF2HMAC
            from cryptography.hazmat.backends import default_backend
        except ImportError:
            raise ImportError("cryptography package required for encryption")
        
        salt = b'myome_hereditary_salt_v1'
        kdf = PBKDF2HMAC(
            algorithm=hashes.SHA256(),
            length=32,
            salt=salt,
            iterations=480000,
            backend=default_backend()
        )
        key = base64.urlsafe_b64encode(kdf.derive(password.encode()))
        
        fernet = Fernet(key)
        data_bytes = json.dumps(self._data).encode()
        encrypted = fernet.encrypt(data_bytes)
        
        self._encrypted = True
        return encrypted
    
    def sign(self, private_key: str) -> str:
        """Sign artifact (simplified - production would use proper digital signatures)"""
        data_str = json.dumps(self._data, sort_keys=True)
        signature = hashlib.sha256(
            (data_str + private_key).encode()
        ).hexdigest()
        
        self._data["signature"] = signature
        return signature
    
    def to_json(self) -> str:
        """Export artifact as JSON"""
        return json.dumps(self._data, indent=2)
    
    def to_dict(self) -> dict:
        """Export artifact as dictionary"""
        return self._data.copy()
    
    @property
    def size_bytes(self) -> int:
        """Get artifact size in bytes"""
        return len(self.to_json().encode())


class ArtifactReader:
    """Read and decrypt hereditary artifacts"""
    
    @staticmethod
    def load(path: str, password: Optional[str] = None) -> dict:
        """Load artifact from file"""
        with open(path, 'r') as f:
            content = f.read()
        
        if content.startswith('gAAAAA'):
            if password is None:
                raise ValueError("Password required for encrypted artifact")
            return ArtifactReader.decrypt(content.encode(), password)
        
        return json.loads(content)
    
    @staticmethod
    def decrypt(encrypted_data: bytes, password: str) -> dict:
        """Decrypt artifact with password"""
        try:
            from cryptography.fernet import Fernet
            from cryptography.hazmat.primitives import hashes
            from cryptography.hazmat.primitives.kdf.pbkdf2 import PBKDF2HMAC
            from cryptography.hazmat.backends import default_backend
        except ImportError:
            raise ImportError("cryptography package required for decryption")
        
        salt = b'myome_hereditary_salt_v1'
        kdf = PBKDF2HMAC(
            algorithm=hashes.SHA256(),
            length=32,
            salt=salt,
            iterations=480000,
            backend=default_backend()
        )
        key = base64.urlsafe_b64encode(kdf.derive(password.encode()))
        
        fernet = Fernet(key)
        decrypted = fernet.decrypt(encrypted_data)
        
        return json.loads(decrypted.decode())
    
    @staticmethod
    def verify_signature(artifact: dict, public_key: str) -> bool:
        """Verify artifact signature (simplified)"""
        stored_signature = artifact.get("signature")
        if not stored_signature:
            return False
        
        artifact_copy = artifact.copy()
        del artifact_copy["signature"]
        
        data_str = json.dumps(artifact_copy, sort_keys=True)
        computed = hashlib.sha256(
            (data_str + public_key).encode()
        ).hexdigest()
        
        return computed == stored_signature
