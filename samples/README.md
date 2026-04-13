# Sample files for testing

- `sample_invoice.txt` — contains invoice-like keywords for category detection.
- `sample_resume.txt` — resume-style text for keyword and category heuristics.
- `export_finalized.example.json` — example shape of a bulk JSON export (array of finalized jobs).

Upload these via the **Upload** screen or `curl`:

```bash
curl -X POST http://127.0.0.1:8000/api/v1/documents/upload \
  -F "files=@samples/sample_invoice.txt" \
  -F "files=@samples/sample_resume.txt"
```
