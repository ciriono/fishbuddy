import os
from dotenv import load_dotenv

def load_settings():
    # Loads .env into process env; safe to call multiple times
    load_dotenv()
    return {
        "OPENAI_API_KEY": os.getenv("OPENAI_API_KEY"),
        "ASSISTANT_ID": os.getenv("ASSISTANT_ID"),
    }
