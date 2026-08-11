import os

from dotenv import load_dotenv

load_dotenv()

print(os.environ["APP_NAME"])
print(os.environ["DATABASE_NAME"])
print(os.environ["JWT_SECRET"])
print(os.environ["API_PREFIX"])
