import os
from dotenv import load_dotenv

load_dotenv()

COMPLIANCE_CHECKER_URL = os.getenv(
    'COMPLIANCE_CHECKER_URL',
    'https://artificialintelligenceact.eu/assessment/eu-ai-act-compliance-checker/'
)
DATA_DIR = os.getenv('DATA_DIR', os.path.join(os.path.dirname(os.path.dirname(__file__)), 'data'))

# Example selectors (update as needed)
FORM_FIELD_WRAPPER = 'div.wsf-field-wrapper' 