from dotenv import load_dotenv
import os
from pathlib import Path

# Charge explicitement le .env du dossier backend
load_dotenv(dotenv_path=Path(__file__).parent / ".env")
print("JIRA_URL =", os.getenv("JIRA_URL"))
print("JIRA_API_TOKEN =", os.getenv("JIRA_API_TOKEN"))
print("JIRA_EMAIL =", os.getenv("JIRA_EMAIL"))
