import pytest
from eu_ai_compliance_scraper.parser.form_parser import parse_form_html

SAMPLE_HTML = '''
<div class="wsf-field-wrapper" data-type="radio">
  <input type="radio" value="Provider"> <label>Provider</label>
  <input type="radio" value="User"> <label>User</label>
</div>
'''

def test_parse_form_html_extracts_fields():
    result = parse_form_html(SAMPLE_HTML)
    assert 'form' in result
    assert len(result['form']) == 1
    field = result['form'][0]
    assert field['type'] == 'radio'
    assert field['label'] == 'Provider'
    assert 'Provider' in field['options']
    assert 'User' in field['options'] 