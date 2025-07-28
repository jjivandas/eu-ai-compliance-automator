import pytest
from unittest.mock import patch
from eu_ai_compliance_scraper.scraper.form_navigator import scrape_compliance_checker

def test_scrape_compliance_checker_returns_html():
    with patch('eu_ai_compliance_scraper.scraper.form_navigator.scrape_compliance_checker') as mock_scrape:
        mock_scrape.return_value = '<html><body>test</body></html>'
        html = scrape_compliance_checker('http://example.com')
        assert '<html>' in html 