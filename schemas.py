# schemas.py
from pydantic import BaseModel, ConfigDict, EmailStr, Field, field_validator

# Base rules for a user
class UserBase(BaseModel):
    name: str = Field(min_length=1, max_length=100)
    email: EmailStr

    @field_validator("name")
    @classmethod
    def validate_name(cls, value: str) -> str:
        cleaned_value = value.strip()
        if not cleaned_value:
            raise ValueError("Name cannot be blank")
        return cleaned_value

# What people send us when creating a user (POST)
class UserCreate(UserBase):
    pass

# What we send back to people (GET)
class UserResponse(UserBase):
    id: int

    model_config = ConfigDict(from_attributes=True)


class MessageResponse(BaseModel):
    message: str
