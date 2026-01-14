from langsmith import Client
import os

LANGSMITH_API_KEY = os.getenv("LANGSMITH_API_KEY")

ls_client = Client(
    api_url="https://api.smith.langchain.com",
    api_key=LANGSMITH_API_KEY
)