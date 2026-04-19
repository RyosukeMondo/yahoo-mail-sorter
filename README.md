# yahoo-mail-sorter

A small Python CLI for **Yahoo Japan Mail** that talks to the server over
**IMAP**. It can:

- **scan / sort / clean** — classify messages with regex rules in `rules.yaml`
  and move them into folders (Important / Finance / Shopping / Newsletter /
  Social / Spam).
- **folders** — list your IMAP folders.
- **dump** — export raw RFC822 messages from a folder into a local **SQLite**
  file (no parsing, just raw bytes) so you can hand the file to someone else
  or process it offline later.

Works against `imap.mail.yahoo.co.jp:993` using a Yahoo-issued **app
password** — the same mechanism Thunderbird / Outlook use. Your normal Yahoo
login password will not work.

---

## 1. Install

Requires Python 3.13+ and [uv](https://github.com/astral-sh/uv).

```bash
git clone https://github.com/RyosukeMondo/yahoo-mail-sorter.git
cd yahoo-mail-sorter
uv sync
```

This gives you a `yahoo-mail-sorter` command inside the project's virtualenv
(`uv run yahoo-mail-sorter ...`).

---

## 2. Credentials — generate a Yahoo Japan app password

You do **not** put your regular login password in the `.env` file. Instead:

1. Sign in at <https://account.edit.yahoo.co.jp/>.
2. Open the **security / login settings** page and enable IMAP/POP access.
3. Issue an **app-specific password** (アプリパスワード) for IMAP. Yahoo
   shows it to you once — copy it.
4. Copy `.env.example` to `.env` and fill in the values:

```bash
cp .env.example .env
```

```ini
# .env
YAHOO_IMAP_HOST=imap.mail.yahoo.co.jp
YAHOO_IMAP_PORT=993
YAHOO_MAIL_USER=your-yahoo-id          # the part before @yahoo.co.jp
YAHOO_MAIL_PASSWORD=your-app-password  # the app password from step 3
RULES_PATH=rules.yaml
```

`.env` is gitignored and never leaves your machine. It is loaded at startup
by [`python-dotenv`](https://github.com/theskumar/python-dotenv); you can
also point at a different file with `--env-file /path/to/other.env`.

---

## 3. Run

All commands default to **dry-run** where applicable — no message is moved
or modified unless you explicitly pass `--execute`.

### Preview classification

```bash
uv run yahoo-mail-sorter scan              # all messages in INBOX
uv run yahoo-mail-sorter scan -n 50        # last 50 messages
```

### Sort into folders

```bash
uv run yahoo-mail-sorter sort              # dry run (preview)
uv run yahoo-mail-sorter sort --execute    # actually move
```

### Move spam only

```bash
uv run yahoo-mail-sorter clean --execute
```

### List IMAP folders

```bash
uv run yahoo-mail-sorter folders
```

### Dump raw messages to SQLite (no parsing)

Use this when you want a self-contained offline snapshot of a mailbox — for
example, archiving Yahoo Auction history or handing a file to someone else
to analyse.

```bash
# Whole INBOX → ./mail_dump.sqlite (default)
uv run yahoo-mail-sorter dump

# A specific folder into a specific file
uv run yahoo-mail-sorter dump \
    --db auction.sqlite \
    --folder INBOX \
    --search 'FROM "auctions.yahoo.co.jp"'

# Limit to the most recent 100 messages
uv run yahoo-mail-sorter dump --db recent.sqlite -n 100
```

Options:

| Flag | Default | Description |
|---|---|---|
| `--db PATH` | `mail_dump.sqlite` | Output SQLite file (created if missing). |
| `--folder NAME` | `INBOX` | IMAP folder to read from. |
| `--search CRITERIA` | *(none)* | Optional raw IMAP SEARCH criteria, e.g. `'FROM "..."'`, `'SINCE 01-Jan-2025'`. |
| `-n, --limit N` | *(all)* | Take only the most recent N matches. |
| `--env-file PATH` | auto-detect | Use a different `.env`. |
| `--debug` | off | Verbose logging to stderr. |

Re-runs are **idempotent** — messages already in the DB (same folder +
UIDVALIDITY + UID) are skipped, so you can safely run it again to pick up
new mail.

`BODY.PEEK[]` is used on the server, so messages are **not** marked as read.

---

## 4. Where the data goes

### Sort / clean / scan

Nothing is written locally. Messages stay on Yahoo's IMAP server; `sort`
and `clean --execute` move them between server-side folders (creating
`Important` / `Finance` / `Shopping` / `Newsletter` / `Social` / `Spam`
as needed).

### Dump

A single SQLite file at the path you pass to `--db` (default
`./mail_dump.sqlite`). One table:

```sql
CREATE TABLE emails (
    folder      TEXT    NOT NULL,  -- IMAP folder name
    uidvalidity INTEGER NOT NULL,  -- IMAP UIDVALIDITY of that folder
    uid         TEXT    NOT NULL,  -- IMAP UID within the folder
    fetched_at  TEXT    NOT NULL,  -- UTC ISO-8601 timestamp of the fetch
    raw         BLOB    NOT NULL,  -- full RFC822 message bytes
    PRIMARY KEY (folder, uidvalidity, uid)
);
CREATE INDEX idx_emails_folder ON emails(folder);
```

The `raw` column is the **complete** RFC822 message — headers, body, any
attachments, multipart boundaries, everything — exactly as it arrived.
Nothing is decoded, stripped, or rewritten. To read it back later:

```python
import email, sqlite3

conn = sqlite3.connect("auction.sqlite")
for (raw,) in conn.execute("SELECT raw FROM emails"):
    msg = email.message_from_bytes(raw)
    print(msg["Subject"])
    # walk msg.walk() for attachments / HTML / plain-text parts
```

### Classification rules

`rules.yaml` in the project root. Edit it to add your own senders or
subject patterns — each rule is a Python regex (case-insensitive). Use
`--rules-file /path/to/other.yaml` to point at a different file.

---

## 5. Safety notes

- The app password lives only in your local `.env`; it is never logged or
  committed (`.env` is in `.gitignore`).
- `scan` / `sort` without `--execute` **never** touch the server state.
- `dump` fetches with `BODY.PEEK[]`, so read/unread flags are preserved.
- Destructive operations are limited to `sort --execute` and
  `clean --execute`, which COPY + mark `\Deleted` + EXPUNGE to move
  messages into the target folder.

---

## 6. Development

```bash
uv sync
uv run pytest                 # run the test suite
uv run ruff check .           # lint
uv run mypy src               # type check
```

Layout:

```
src/yahoo_mail_sorter/
├── cli.py          # Typer commands: scan, sort, clean, folders, dump
├── config.py       # .env / env-var loading
├── imap_client.py  # imaplib wrapper (connect, fetch, move, fetch_raw)
├── classifier.py   # applies rules.yaml to an Email
├── sorter.py       # orchestrates scan / sort / clean
├── dumper.py       # writes raw messages to SQLite
├── rules_loader.py # parses + validates rules.yaml
├── decoder.py      # RFC2047 header decoding
├── models.py       # Email / Category / SortReport dataclasses
└── exceptions.py   # typed error hierarchy
```
