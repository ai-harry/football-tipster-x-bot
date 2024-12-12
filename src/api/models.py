from pydantic import BaseModel, Field, validator
from typing import Optional

class TwitterCredentials(BaseModel):
    api_key: str = Field(..., min_length=1)
    api_secret: str = Field(..., min_length=1)
    access_token: str = Field(..., min_length=1)
    access_token_secret: str = Field(..., min_length=1)
    
    @validator('api_key', 'api_secret', 'access_token', 'access_token_secret')
    def validate_credentials(cls, v):
        if not v.strip():
            raise ValueError("Credential fields cannot be empty")
        return v

class PromptTemplate(BaseModel):
    template: str = Field(..., min_length=10)
    
    @validator('template')
    def validate_template(cls, v):
        required_placeholders = ['{bet_details}', '{analysis_points}']
        for placeholder in required_placeholders:
            if placeholder not in v:
                raise ValueError(f"Template must contain {placeholder}")
        return v

class PromptUpdateResponse(BaseModel):
    success: bool
    message: str
    current_template: str

class ConfigResponse(BaseModel):
    success: bool
    message: str 