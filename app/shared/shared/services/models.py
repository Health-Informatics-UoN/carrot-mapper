from typing import Optional, TypedDict


class VocabularyMapping(TypedDict):
    sr_field_id: int
    field_data_type: Optional[str]
    vocabulary_id: Optional[str]
