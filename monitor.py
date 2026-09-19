"""Monitora la pagina interpelli dell'UST Vicenza e invia una notifica push (ntfy) per ogni nuovo PDF."""

import base64
import html
import json
import os
import re
import subprocess
import sys
import tempfile
import urllib.request
from collections import Counter
from pathlib import Path

PAGE_URL = "https://vicenza.istruzioneveneto.gov.it/interpelli-2026-27-pagina-provvisoria/"
STATE_FILE = Path(__file__).with_name("seen.json")
NTFY_SERVER = os.environ.get("NTFY_SERVER", "https://ntfy.sh")
NTFY_TOPIC = os.environ.get("NTFY_TOPIC", "")
# Classi di concorso da evidenziare, es. "ADEE,EEEE" (vuoto = nessun filtro)
WATCH_CDC = {c.strip().upper() for c in os.environ.get("WATCH_CDC", "").split(",") if c.strip()}
DRY_RUN = os.environ.get("DRY_RUN") == "1"

UA = {"User-Agent": "Mozilla/5.0 (interpelli-monitor)"}
LINK_RE = re.compile(r'<a\s+[^>]*href="([^"]+\.pdf)"[^>]*>(.*?)</a>', re.I | re.S)


def fetch(url: str) -> bytes:
    req = urllib.request.Request(url, headers=UA)
    with urllib.request.urlopen(req, timeout=60) as r:
        return r.read()


def find_links(page: str) -> list[tuple[str, str]]:
    # Solo il contenuto dell'articolo, per ignorare PDF in header/footer
    start = page.find('class="entry-content"')
    end = page.find('class="entry-links"', start)
    body = page[start:end] if start != -1 and end != -1 else page
    links = []
    for href, text in LINK_RE.findall(body):
        title = html.unescape(re.sub(r"<[^>]+>", "", text)).strip() or href.rsplit("/", 1)[-1]
        links.append((href, title))
    return links


def summarize_pdf(url: str) -> dict:
    """Riassunto approssimativo del PDF: righe, scuole, classi di concorso."""
    with tempfile.TemporaryDirectory() as d:
        pdf = Path(d, "f.pdf")
        pdf.write_bytes(fetch(url))
        txt = subprocess.run(
            ["pdftotext", "-layout", str(pdf), "-"], capture_output=True, check=True
        ).stdout.decode("utf-8", "replace")
    rows = len(re.findall(r"\d\d/\d\d/\d\d\s+\d\d/\d\d/\d\d\s+\d\d/\d\d/\d\d", txt))
    schools = set(re.findall(r"\bVI[A-Z]{2}[0-9A-Z]{6}\b", txt))
    cdc = Counter(re.findall(r"\b([A-Z][A-Z0-9]{3})(?= -)", txt))
    return {"rows": rows, "schools": len(schools), "cdc": cdc}


def notify(title: str, message: str, click: str, tags: str, priority: str) -> None:
    if DRY_RUN or not NTFY_TOPIC:
        print(f"[notifica] {title}\n{message}\n{click}\n")
        return
    req = urllib.request.Request(
        f"{NTFY_SERVER}/{NTFY_TOPIC}",
        data=message.encode("utf-8"),
        headers={
            # Gli header HTTP devono essere latin-1: il titolo va codificato RFC 2047
            "Title": "=?UTF-8?B?" + base64.b64encode(title.encode()).decode() + "?=",
            "Click": click,
            "Tags": tags,
            "Priority": priority,
            "Actions": f"view, Apri PDF, {click}; view, Apri pagina, {PAGE_URL}",
        },
        method="POST",
    )
    urllib.request.urlopen(req, timeout=30).read()


def main() -> int:
    page = fetch(PAGE_URL).decode("utf-8", "replace")
    links = find_links(page)
    if not links:
        print("Nessun link trovato: la struttura della pagina potrebbe essere cambiata.", file=sys.stderr)
        return 1

    first_run = not STATE_FILE.exists()
    seen = set(json.loads(STATE_FILE.read_text())) if not first_run else set()
    new = [(u, t) for u, t in links if u not in seen]

    if first_run:
        print(f"Primo avvio: registro {len(links)} link esistenti senza notificare.")
        notify(
            "Monitor interpelli attivo",
            f"Sto monitorando la pagina. {len(links)} PDF già presenti; ultimo: {links[0][1]}",
            PAGE_URL, "white_check_mark", "default",
        )
    for url, title in reversed(new if not first_run else []):
        lines = []
        tags, priority = "school,bell", "high"
        try:
            s = summarize_pdf(url)
            lines.append(f"≈{s['rows']} interpelli da {s['schools']} scuole")
            if s["cdc"]:
                lines.append("Classi: " + ", ".join(f"{c} ({n})" for c, n in s["cdc"].most_common()))
            if WATCH_CDC:
                hits = sorted(WATCH_CDC & set(s["cdc"]))
                if hits:
                    lines.insert(0, "⭐ Contiene: " + ", ".join(hits))
                    tags, priority = "star,school", "urgent"
                else:
                    priority = "default"
        except Exception as e:  # la notifica parte comunque
            lines.append(f"(impossibile leggere il PDF: {e})")
        notify(f"Nuovo: {title}", "\n".join(lines), url, tags, priority)
        print(f"Notificato: {title}")

    if not DRY_RUN:
        STATE_FILE.write_text(json.dumps(sorted(seen | {u for u, _ in links}), indent=1) + "\n")
    if not new:
        print("Nessuna novità.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
