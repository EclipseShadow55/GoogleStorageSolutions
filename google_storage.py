import os
import json

# Getting config information
with open("config.json", "r") as f:
    config = json.load(f)

# Setting up Google Sheet storage
SCOPES = ["https://www.googleapis.com/auth/drive.metadata.readonly"]


class GoogleStorage:
    def __init__(self, password):
        self.creds = None
        self.service = None
