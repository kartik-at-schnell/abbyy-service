from pydantic import BaseModel
from typing import List, Optional

# field extraction
class FieldValue(BaseModel):
    name: str
    value: str
    confidence: float

# ocr result, pqagewise
class PageResult(BaseModel):
    page_number: int
    fields: List[FieldValue]

#complete response
class OCRResponse(BaseModel):

    pages: List[PageResult]
    
    def get_average_confidence(self) -> float:
        all_confidences = []
        for page in self.pages:
            all_confidences.extend([f.confidence for f in page.fields])
        
        return sum(all_confidences) / len(all_confidences) if all_confidences else 0.0
    
    def get_field_by_name(self, name: str) -> Optional[FieldValue]:
        for page in self.pages:
            for field in page.fields:
                if field.name == name:
                    return field
        return None
