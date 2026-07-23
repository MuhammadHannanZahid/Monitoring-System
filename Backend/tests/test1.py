from app.core.jwt import jwt_service
from app.core.security import (password_service, refresh_token_service,)

password = "Admin@123"
hashed = password_service.hash_password(password)
print(password_service.verify_password(password, hashed))

token = refresh_token_service.generate_token()
hashed_token = refresh_token_service.hash_token(token)
print(refresh_token_service.verify_token(token, hashed_token))

access = jwt_service.create_access_token(
    user_id="123",
    username="admin",
    role="admin",
)
print(access)

payload = jwt_service.verify_access_token(access)
print(payload)