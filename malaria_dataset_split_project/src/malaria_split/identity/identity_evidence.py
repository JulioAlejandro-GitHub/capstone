from dataclasses import asdict, dataclass
from enum import Enum


class IdentityStatus(str, Enum):
    VERIFIED = "VERIFIED"
    UNRESOLVED = "UNRESOLVED"
    CONFLICT = "CONFLICT"


class EvidenceType(str, Enum):
    OFFICIAL_METADATA = "official_metadata"
    OFFICIAL_FILENAME = "official_filename_convention"
    EXACT_ARTIFACT = "exact_artifact"
    DECODED_PIXEL_HASH = "decoded_pixel_hash"
    NONE = "none"


EVIDENCE_PRECEDENCE = {
    EvidenceType.OFFICIAL_METADATA: 1,
    EvidenceType.OFFICIAL_FILENAME: 2,
    EvidenceType.EXACT_ARTIFACT: 3,
    EvidenceType.DECODED_PIXEL_HASH: 4,
    EvidenceType.NONE: 5,
}


@dataclass(frozen=True)
class SourceIdentityRecord:
    source_record_id: str
    source_filename: str
    class_name: str
    patient_id: str | None
    evidence_type: EvidenceType
    evidence_reference: str
    mapping_key: str


@dataclass(frozen=True)
class ResolvedClinicalIdentity:
    tfds_index: int
    physical_relative_path: str
    historical_split: str
    class_name: str
    label: int
    source_record_id: str | None
    source_filename: str | None
    patient_id: str | None
    sample_id: str | None
    smear_id: str | None
    slide_id: str | None
    identity_status: IdentityStatus
    evidence_type: EvidenceType
    evidence_reference: str | None
    mapping_method: str
    ambiguity_count: int

    def to_dict(self) -> dict:
        result = asdict(self)
        result["identity_status"] = self.identity_status.value
        result["evidence_type"] = self.evidence_type.value
        return result

