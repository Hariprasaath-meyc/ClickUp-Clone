from pydantic import BaseModel, ConfigDict, EmailStr, Field, field_validator

class SignupInput(BaseModel):
    email: EmailStr

    password: str = Field(min_length=1)

    display_name: str = Field(
        min_length=1,
        max_length=100,
    )

    @field_validator("display_name", mode="before")
    @classmethod
    def normalize_display_name(cls, value: str) -> str:
        if isinstance(value, str):
            return value.strip()

        return value

    
class ConfirmSignupInput(BaseModel):
    model_config = ConfigDict(str_strip_whitespace=True)

    email: EmailStr
    confirmation_code: str = Field(min_length=1)