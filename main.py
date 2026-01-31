# imports

import os
import requests
from dotenv import load_dotenv
from bs4 import BeautifulSoup
from IPython.display import Markdown, display
from openai import OpenAI
import json
import sys
from datetime import datetime


# If you get an error running this cell, then please head over to the troubleshooting notebook!
# Load environment variables in a file called .env

load_dotenv(".env", override=True)
api_key = os.getenv('OPENAI_API_KEY', '').strip()

# Check the key

if not api_key:
    print("No API key was found - please head over to the troubleshooting notebook in this folder to identify & fix!")
elif not api_key.startswith("sk-proj-"):
    print("An API key was found, but it doesn't start sk-proj-; please check you're using the right key - see troubleshooting notebook")
elif api_key.strip() != api_key:
    print("An API key was found, but it looks like it might have space or tab characters at the start or end - please remove them - see troubleshooting notebook")
else:
    print("API key found and looks good so far!")

# === Load API Key from .env File ===
load_dotenv(".env", override=True)
client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))