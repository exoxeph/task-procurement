"""GET /api/samples -> the ten sample PDFs with their expected verdict and extracted page text."""
from http.server import BaseHTTPRequestHandler
import json
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from procurement.shared.pdf_text import read_pdf  # noqa: E402
from procurement.shared.references import PROJECT_ROOT, SAMPLE_DIRECTORY  # noqa: E402

TESTS = {
    '01': "Payment 'after delivery and acceptance of goods'", '02': "Delivery 'at your factory'",
    '03': 'Unit price far above the maximum', '04': 'Price slightly above the maximum',
    '05': '40% advance', '06': 'No late-delivery penalty clause', '07': 'Quantity differs from the request',
    '08': "No TIN or BIN ('available on request')", '09': 'Payment 30 to 90 days as agreed; wrong arithmetic',
    '10': 'Delivery in 60 days; VAT included',
}


class handler(BaseHTTPRequestHandler):
    def do_GET(self):
        labels = json.loads((PROJECT_ROOT / 'config/manual-labels.json').read_text(encoding='utf-8'))['documents']
        payload = []
        for n in range(1, 11):
            name = f'supplier-pack-{n:02d}'
            document = read_pdf(SAMPLE_DIRECTORY / f'{name}.pdf')
            payload.append({'id': name, 'label': TESTS[f'{n:02d}'], 'expected': labels[f'{name}.pdf']['verdict'],
                            'text': '\n'.join(page.text for page in document.pages)})
        body = json.dumps(payload).encode('utf-8')
        self.send_response(200)
        self.send_header('Content-Type', 'application/json; charset=utf-8')
        self.send_header('Cache-Control', 'public, max-age=3600')
        self.end_headers()
        self.wfile.write(body)
