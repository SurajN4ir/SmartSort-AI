# SmartSort

SmartSort is a desktop app that looks at a messy folder, works out what's in
it, and proposes a clean structure to organize it into — without moving a
single file until you approve the plan.

```
Downloads/                      Downloads/
├── resume.pdf                  ├── Documents/
├── assignment.docx      --->   │   ├── resume.pdf
├── Messi.jpg                   │   └── assignment.docx
├── setup.exe                   ├── Images/
├── project.zip                 │   └── Messi.jpg
└── invoice.pdf                 ├── Applications/
                                │   └── setup.exe
                                ├── Archives/
                                │   └── project.zip
                                └── Documents/
                                    └── invoice.pdf
```

## How it works

1. **Scan** — reads the files in a folder (name, extension, size, modified date).
2. **Classify** — a rule-based engine maps each file's extension to a category
   (Documents, Images, Videos, Code, Archives, ...).
3. **Plan** — builds a full move plan (source → destination), resolving name
   collisions automatically. Nothing on disk changes at this point.
4. **Review** — every proposed move is shown before anything happens. Files
   can be excluded or reassigned to a different category.
5. **Apply** — only the moves you approved are executed, and every session is
   recorded so it can be undone later.

Nothing moves until you click *Apply*. That review step is the whole point:
running SmartSort on a folder full of files should never be a leap of faith.

## Project structure

```
smartsort/
├── scanner.py       # walks a directory, collects file metadata
├── categorizer.py   # extension -> category rules
├── planner.py       # turns classified files into a move plan
├── organizer.py     # executes a plan on disk, and undoes it later
├── database.py      # SQLite-backed scan/session history
├── models.py         # shared data structures
└── gui/              # CustomTkinter desktop UI
    ├── app.py
    ├── overview.py    # select -> scan -> propose -> review -> apply
    ├── history.py     # past sessions, drill-down, undo
    └── settings.py
main.py               # entry point
tests/                 # pytest suite for the core pipeline
```

The core pipeline (scanner, categorizer, planner, organizer, database) has no
GUI dependency and is fully unit tested. The GUI is a thin layer on top of it.

## Running it

Requires Python 3.11+.

```bash
python -m venv venv
venv\Scripts\activate      # on Windows
pip install -r requirements.txt
python main.py
```

## Running the tests

```bash
pip install -r requirements-dev.txt
pytest
```

## Design notes

- **Extension-based classification** is deliberate for this version. It's the
  seam where a smarter, content-aware classifier could plug in later without
  touching the scanner, planner, or GUI.
- **SQLite history** means every organize session is remembered, not just
  performed and forgotten — which is what makes an undo feature possible.
- **Dry-run by default**: the planner only ever produces a proposal. The
  organizer is the one and only place that touches the filesystem, and it
  only runs on files you've explicitly approved in the review screen.

## License

MIT — see [LICENSE](LICENSE).
