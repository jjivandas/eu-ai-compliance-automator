from bs4 import BeautifulSoup
from typing import Any, Dict

def parse_form_html(html: str) -> Dict[str, Any]:
    """
    Parses the compliance checker HTML and extracts form structure as JSON.
    """
    soup = BeautifulSoup(html, 'html.parser')
    form_structure = []
    for field in soup.find_all('div', class_='wsf-field-wrapper'):
        q_type = field.get('data-type')
        label = field.find('label')
        options = [opt.get('value') for opt in field.find_all('input') if opt.get('value')]
        form_structure.append({
            'type': q_type,
            'label': label.text.strip() if label else None,
            'options': options
        })
    return {'form': form_structure} 