import os
from dotenv import load_dotenv
import logging

load_dotenv()

logger = logging.getLogger(__name__)

# Models - All use Groq cloud-based instant models
PRO_MODEL_1 = "groq/llama-3.3-70b-versatile"
PRO_MODEL_2 = "groq/llama-3.3-70b-versatile"
CON_MODEL_1 = "groq/llama-3.3-70b-versatile"
CON_MODEL_2 = "groq/llama-3.3-70b-versatile"
JUDGE_MODEL = "groq/llama-3.3-70b-versatile"

# Groq API - Multiple Keys Support
# Load all API keys (GROQ_API_KEY, GROQ_API_KEY_2, GROQ_API_KEY_3, etc.)
GROQ_API_KEYS = []
for i in range(1, 11):  # Support up to 10 keys
    key_name = "GROQ_API_KEY" if i == 1 else f"GROQ_API_KEY_{i}"
    key = os.getenv(key_name)
    if key and key.strip():
        GROQ_API_KEYS.append(key.strip())

# Fallback to single key for backward compatibility
GROQ_API_KEY = GROQ_API_KEYS[0] if GROQ_API_KEYS else None

GROQ_ENDPOINT = "https://api.groq.com/openai/v1/chat/completions"
GROQ_DELAY_SECONDS = float(os.getenv("GROQ_DELAY_SECONDS", "1.0"))

if GROQ_API_KEYS:
    logger.info(f"✓ Loaded {len(GROQ_API_KEYS)} Groq API key(s)")
else:
    logger.warning("⚠️ No Groq API keys found in environment")

# Web Search
SEARCH_ENGINE = os.getenv("SEARCH_ENGINE", "duckduckgo")
MAX_SEARCH_RESULTS = int(os.getenv("MAX_SEARCH_RESULTS", "8"))
MAX_SCRAPED_PAGES_PER_FACTOR = int(os.getenv("MAX_SCRAPED_PAGES_PER_FACTOR", "5"))
SCRAPE_TIMEOUT = int(os.getenv("SCRAPE_TIMEOUT", "15"))

# Debate
DEBATE_ROUNDS = int(os.getenv("DEBATE_ROUNDS", "3"))
MAX_ARGUMENT_LENGTH = int(os.getenv("MAX_ARGUMENT_LENGTH", "200"))
ALLOW_CROSS_CRITIQUE = os.getenv("ALLOW_CROSS_CRITIQUE", "true").lower() == "true"
MAX_FACTORS = int(os.getenv("MAX_FACTORS", "5"))

# Rate Limiting
REQUEST_DELAY_SECONDS = float(os.getenv("REQUEST_DELAY_SECONDS", "0.5"))
MAX_RETRIES = int(os.getenv("MAX_RETRIES", "6"))
RETRY_BACKOFF_FACTOR = float(os.getenv("RETRY_BACKOFF_FACTOR", "2.0"))

# Evaluation
ENABLE_ANONYMIZATION = os.getenv("ENABLE_ANONYMIZATION", "true").lower() == "true"
SCORING_SCALE = os.getenv("SCORING_SCALE", "1-10")

# Output
OUTPUT_DIR = os.getenv("OUTPUT_DIR", "outputs/")
SAVE_TRANSCRIPTS = os.getenv("SAVE_TRANSCRIPTS", "true").lower() == "true"
