# schemas.py
from pydantic import (
    BaseModel,
    ConfigDict,
    EmailStr,
    Field,
    field_validator,
    model_validator,
)



def clean_name(value: str) -> str:
    cleaned_value = value.strip()
    if not cleaned_value:
        raise ValueError("Name cannot be blank")
    return cleaned_value


class UserBase(BaseModel):
    name: str = Field(min_length=1, max_length=100)
    email: EmailStr

    @field_validator("name")
    @classmethod
    def validate_name(cls, value: str) -> str:
        return clean_name(value)


class UserCreate(UserBase):
    password: str = Field(min_length=8, max_length=128)


class UserLogin(BaseModel):
    email: EmailStr
    password: str = Field(min_length=8, max_length=128)


class UserUpdate(BaseModel):
    name: str | None = Field(default=None, min_length=1, max_length=100)
    email: EmailStr | None = None
    password: str | None = Field(default=None, min_length=8, max_length=128)

    @field_validator("name")
    @classmethod
    def validate_name(cls, value: str | None) -> str | None:
        if value is None:
            return value
        return clean_name(value)

    @model_validator(mode="after")
    def validate_has_data(self):
        if self.name is None and self.email is None and self.password is None:
            raise ValueError("At least one field must be provided")
        return self


class UserResponse(UserBase):
    id: int

    model_config = ConfigDict(from_attributes=True)


class TokenResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"


class MessageResponse(BaseModel):
    message: str
