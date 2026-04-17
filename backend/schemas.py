from typing import Optional

from pydantic import BaseModel, Field


class BaseFieldResult(BaseModel):
    needs_supplement: bool = Field(
        False,
        description="如果当前信息不足以完成提取，设为 true",
    )
    supplement_question: Optional[str] = Field(
        None,
        description="当 needs_supplement 为 true 时，必须填写需要补充的具体问题",
    )


class ChiefComplaintResult(BaseFieldResult):
    主诉: str = Field(
        ...,
        description="提取的主诉内容。如果信息不足，needs_supplement 设为 true 并在 supplement_question 中说明需要补充的问题。",
    )


class PresentIllnessResult(BaseFieldResult):
    现病史: str = Field(
        ...,
        description="提取的现病史内容。如果信息不足，needs_supplement 设为 true 并在 supplement_question 中说明需要补充的问题。",
    )


class PastHistoryResult(BaseFieldResult):
    既往史: str = Field(
        ...,
        description="提取的既往史内容。如果信息不足，needs_supplement 设为 true 并在 supplement_question 中说明需要补充的问题。",
    )


class AllergyHistoryResult(BaseFieldResult):
    过敏史: str = Field(
        ...,
        description="提取的过敏史内容。如果信息不足，needs_supplement 设为 true 并在 supplement_question 中说明需要补充的问题。",
    )


class DiagnosisResult(BaseFieldResult):
    诊断: str = Field(
        ...,
        description="初步诊断及建议。如果信息不足，needs_supplement 设为 true 并在 supplement_question 中说明需要补充的问题。",
    )


FIELD_SCHEMA_MAP = {
    "主诉": ChiefComplaintResult,
    "现病史": PresentIllnessResult,
    "既往史": PastHistoryResult,
    "过敏史": AllergyHistoryResult,
    "诊断": DiagnosisResult,
}
