# Interpelli Vicenza → notifiche su iPhone

Controlla ogni ~10 minuti la [pagina interpelli 2026/27 dell'UST di Vicenza](https://vicenza.istruzioneveneto.gov.it/interpelli-2026-27-pagina-provvisoria/)
e, quando compare un nuovo PDF, invia una notifica push all'iPhone con:

- il titolo del file (es. *Aggiornamento Interpelli VI – 18_09_2026, 21_00*)
- un riassunto approssimativo: numero di interpelli, numero di scuole, classi di concorso (es. `ADEE (4), EEEE (3)`)
- un tocco sulla notifica apre il PDF; il pulsante "Apri pagina" apre la pagina dell'UST

Il controllo gira gratis su GitHub Actions, quindi non serve lasciare acceso il PC.
Le notifiche arrivano tramite l'app gratuita **ntfy**.

## Configurazione (circa 10 minuti)

### 1. iPhone
1. Installa **ntfy** dall'App Store.
2. Tocca **+**, scegli un nome di topic lungo e difficile da indovinare (chiunque conosca il nome può leggerlo),
   es. `interpelli-vi-k7f3q9x2m`, e iscriviti.
3. Consenti le notifiche quando te lo chiede.

### 2. GitHub
1. Crea un repository su GitHub (anche privato) e carica questi file:
   ```bash
   git init
   ```
   ```bash
   git add .
   ```
   ```bash
   git commit -m "Monitor interpelli"
   ```
   ```bash
   git branch -M main
   ```
   ```bash
   git remote add origin https://github.com/<tuo-utente>/interpelli-belli.git
   ```
   ```bash
   git push -u origin main
   ```
2. Nel repository: **Settings → Secrets and variables → Actions**
   - scheda **Secrets** → *New repository secret*: nome `NTFY_TOPIC`, valore = il topic scelto sull'iPhone
   - (facoltativo) scheda **Variables** → *New repository variable*: nome `WATCH_CDC`, valore = le tue classi
     di concorso separate da virgola, es. `ADEE,EEEE`. I PDF che le contengono arrivano con priorità urgente e ⭐;
     gli altri arrivano con priorità normale.
3. Scheda **Actions** → *Monitor interpelli Vicenza* → **Run workflow** per il primo avvio.
   Dovresti ricevere subito la notifica "Monitor interpelli attivo": i PDF già pubblicati vengono registrati
   senza notificarli, da quel momento arriva una notifica per ogni nuovo PDF.

## Note

- GitHub avvia i job programmati con qualche minuto di ritardo nei momenti di carico: aspettati la notifica
  entro 10–20 minuti dalla pubblicazione.
- Se la pagina cambia struttura o indirizzo (ad esempio quando la "pagina provvisoria" viene sostituita), il job
  fallisce e GitHub ti manda un'email: in quel caso aggiorna `PAGE_URL` in `monitor.py`.
- Il riassunto viene estratto dal testo del PDF, che è un'impaginazione a tabella: i numeri sono indicativi,
  per i dettagli fa fede il PDF.
- Prova in locale senza inviare notifiche: `DRY_RUN=1 python3 monitor.py` (richiede `pdftotext`).
