from google import genai
from google.genai import types
from dotenv import load_dotenv

# The client gets the API key from the environment variable `GEMINI_API_KEY`.
load_dotenv()
client = genai.Client()

grounding_tool = types.Tool(
    google_search=types.GoogleSearch()
)
config = types.GenerateContentConfig(
    tools=[grounding_tool]
)

response = client.models.generate_content(
    model="gemini-2.5-flash",
    contents="Who won the euro 2024?",
    config=config,
)

print(response.text)