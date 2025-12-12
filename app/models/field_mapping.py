from sqlalchemy import Column, String, Float, Boolean, DateTime, UniqueConstraint
from datetime import datetime
from app.models.base import BaseModel
#ocr field extraction
class FieldMapping(BaseModel):
    __tablename__ = "field_mapping"
    
    document_type = Column(String(50), nullable=False, index=True)
    abbyy_field_name = Column(String(100), nullable=False)
    db_field_name = Column(String(100), nullable=False)
    confidence_threshold = Column(Float, default=95.0, nullable=False)
    required = Column(Boolean, default=False, nullable=False)
    
    __table_args__ = (
        UniqueConstraint("document_type", "abbyy_field_name", name="uq_document_field_pair"),
    )
    
    def __repr__(self):
        return f"<FieldMapping({self.document_type}.{self.abbyy_field_name})>"


DEFAULT_FIELD_MAPPINGS = [
    {
        "document_type": "VR_MASTER",
        "abbyy_field_name": "VehicleIDNumber",
        "db_field_name": "vin",
        "confidence_threshold": 95.0,
        "required": True
    },
    {
        "document_type": "VR_MASTER",
        "abbyy_field_name": "Make",
        "db_field_name": "make",
        "confidence_threshold": 90.0,
        "required": False
    },
    {
        "document_type": "VR_MASTER",
        "abbyy_field_name": "Year",
        "db_field_name": "year",
        "confidence_threshold": 95.0,
        "required": False
    },
    {
        "document_type": "VR_MASTER",
        "abbyy_field_name": "LicensePlate",
        "db_field_name": "plate",
        "confidence_threshold": 95.0,
        "required": False
    },
]
