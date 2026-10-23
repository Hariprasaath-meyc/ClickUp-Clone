
from copy import error
import os

import boto3
from botocore.exceptions import ClientError
from fastapi import APIRouter, HTTPException, status
from pydantic import BaseModel, EmailStr, Field

router = APIRouter(prefix="/auth", tags=["Authentication"])

region = os.getenv("AWS_REGION", "ap-south-1")
client_id = os.getenv("COGNITO_CLIENT_ID")

if not client_id:
    raise RuntimeError("COGNITO_CLIENT_ID is missing from .env")

cognito = boto3.client("cognito-idp", region_name=region)


class SignupRequest(BaseModel):
    name: str = Field(min_length=1, max_length=100)
    email: EmailStr
    password: str = Field(min_length=8, max_length=256)


@router.post("/signup", status_code=status.HTTP_201_CREATED)
def signup(data: SignupRequest):
    try:
        result = cognito.sign_up(
            ClientId=client_id,
            Username=str(data.email),
            Password=data.password,
            UserAttributes=[
                {"Name": "email", "Value": str(data.email)},
                {"Name": "name", "Value": data.name},
            ],
        )

        return {
            "message": "Signup successful. Check your email for the confirmation code.",
            "user_id": result["UserSub"],
            "confirmation_required": not result.get(
                "UserConfirmed", False
            ),
        }

    except ClientError as exc:
        error_code = exc.response.get("Error", {}).get("Code")
        print("Cognito error code:", error.get("Code"))
        print("Cognito error message:", error.get("Message"))



        if error_code == "UsernameExistsException":
            raise HTTPException(
                status_code=409,
                detail="An account with this username already exists.",
            ) from exc

        if error_code in {
            "InvalidPasswordException",
            "InvalidParameterException",
        }:
            raise HTTPException(
                status_code=400,
                detail="Signup details are invalid or the password does not meet policy requirements.",
            ) from exc

        if error_code == "LimitExceededException":
            raise HTTPException(
                status_code=429,
                detail="Signup limit reached. Please try again later.",
            ) from exc

        raise HTTPException(
            status_code=502,
            detail="The identity provider could not complete signup.",
        ) from exc
