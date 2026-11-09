import strawberry


@strawberry.type
class CodeDeliveryDetails:
    destination: str | None
    delivery_medium: str | None
    attribute_name: str | None


@strawberry.type
class SignupResult:
    confirmation_required: bool
    message: str
    delivery: CodeDeliveryDetails | None = None


@strawberry.type
class LoginResult:
    access_token: str
    id_token: str
    refresh_token: str | None
    expires_in: int
    token_type: str


@strawberry.type
class RefreshSessionResult:
    access_token: str
    id_token: str | None
    expires_in: int
    token_type: str
    refresh_token: str | None = None


@strawberry.type
class LogoutResult:
    success: bool
    message: str
