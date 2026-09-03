# Getting started (complete beginner guide)

This guide assumes you have **never written code, used a terminal, or used Git before**. Nothing is assumed as "obvious". Every new word is explained the first time it appears.

It is written for coastal science and geography students who need to run this shoreline analysis, not for programmers.

### The good news

You are not going to be writing code. The code is already written. Your job is to:

1. Install some software (once)
2. Change about four lines of settings (a date, or a place name)
3. Press Run
4. Check the outputs and save your work

Most of this guide is the one-time setup. Once that's done, a normal session is about five commands and pressing Run.

### Quick workflow: first time vs continuing

Use this as your simple decision tree:

```text
Start here
│
├─ First time on this computer?
│  ├─ Yes → do Parts 1-5 first
│  └─ No  → go straight to the checklist below
│
└─ Continuing from a previous session?
   ├─ Open the repo in VS Code
   ├─ Activate the environment (.venv)
   ├─ Pull the latest shared updates: git pull origin nzccdv2
   ├─ Push your own branch when you are ready: git push origin yourname
   └─ If Git reports a merge conflict, stop and ask before continuing
```

For day-to-day work, the rule is simple:

- **First time on a machine**: complete Parts 1-5.
- **Returning to the same project**: activate the environment, pull the latest shared updates, then start your run.
- **Only change the search settings and naming values** in the notebooks. Leave the workflow code alone unless someone specifically tells you to change it.

### How to read the instructions

When you see a grey box like this:

```powershell
cd C:\Users\yourname\repos\retrolens
```

that is a **command** — an instruction you type into a terminal (explained below) and then press Enter. Type or paste it exactly as written, one line at a time, unless told otherwise.

Where something says `yourname`, replace it with your actual name or username. Everything else should be copied literally, including punctuation like dots and backslashes, which are meaningful.

Follow the parts in order. **Parts 1-4 are setup you do once _per computer_.** After that you start at Part 5 each time. If you later switch to a different machine — a lab computer, a new laptop — see "Working on more than one computer" near the end.

---

## Part 0: The words you'll keep seeing

Read this once now. It won't all stick, and that's fine — come back when a word confuses you.

### The basics

**Terminal** (also "command line", "shell", "PowerShell")
A text window where you type instructions to your computer instead of clicking buttons. It looks intimidating but it's just a different way of saying "do this thing". You'll use it for a handful of commands like "go to this folder" and "save my work".

**Command**
One line you type into the terminal, followed by Enter. Nothing happens until you press Enter.

**Python**
The programming language this project is written in. You need it installed so your computer understands the code, in the same way you need a PDF reader to open a PDF.

**Package** (also "library", "module")
A bundle of pre-written code that does one job, written by someone else and shared freely. For example, `geopandas` is a package that knows how to read shapefiles. This project uses about a dozen. You don't write them, you just install them and the code uses them.

**Environment** (also "virtual environment", "venv")
A private box holding the specific packages this project needs. Different projects often need different, conflicting versions of the same package, so each project gets its own box rather than dumping everything together. You'll create one box for this project and "activate" it whenever you work.

**Activate**
Telling your terminal "use this project's box of packages". Terminals forget this when you close them, so you'll re-activate at the start of each session. This is normal, not something going wrong.

### The file and folder side

**Folder / directory**
The same thing you already know from File Explorer. "Directory" is just the older word for it.

**Path**
A folder's full address, like `C:\Users\catriona\repos\retrolens`. Windows uses backslashes `\` between folder names.

**Workspace** (a VS Code word)
Simply the folder you currently have open in VS Code. When people say "open the workspace", they mean "open the project folder". Nothing more mysterious than that.

**Local**
On your own computer, as opposed to online. Your "local copy" is the version sitting on your hard drive.

### The Git and GitHub side

**Git**
A program that tracks every change made to a set of files, so you can see what changed, when, and by whom — and undo things safely. Think of it as very thorough track-changes for a whole folder.

**GitHub**
A website that stores Git projects online so a team can share them. Git is the tool on your computer; GitHub is the website. They are two different things with confusingly similar names.

**Repository / repo**
A project folder that Git is tracking, including its full history. This project is one repo.

**Clone**
Download your own complete copy of an online repo onto your computer, permanently linked to the original so you can exchange updates.

**Branch**
Your own parallel version of the project, where your changes can't disturb anyone else. You'll make one named after yourself.

**`main`**
The shared, trusted, official version of the project. You do not work directly on this.

**`nzccdv2`**
The branch holding the shoreline-update workflow. This is the one you copy your own branch from. You don't work directly on this either.

**Commit**
A saved snapshot of your changes with a short note explaining them, like a labelled save point.

**Push / pull**
Push = upload your saved snapshots to GitHub. Pull = download other people's.

**Pull request (PR)**
A formal request to have your branch's changes reviewed and folded into the shared branch.

### The notebook side

**Notebook (a `.ipynb` file)**
A document that mixes written notes, chunks of code, and the results of that code — tables, maps, plots — all on one scrollable page. It's popular in research because you can see the working alongside the output. The three files you'll run are notebooks.

**Cell**
One chunk of a notebook. Code cells can be run individually by clicking the ▷ arrow beside them. Text cells are just notes.

**Run**
Execute a cell's code and show its result underneath.

**Kernel** 

The kernel is the **Python program running quietly in the background that actually does the work** and remembers everything as it goes.

An analogy: the notebook is a lab notebook page, and the kernel is the lab bench where the actual work happens. Writing "add reagent A" on the page changes nothing — it only happens when it's carried out on the bench. When you run a cell, you're handing that instruction to the kernel to carry out.

Why this matters in practice:

- **The kernel remembers.** If cell 1 loads your shoreline data, that data stays in the kernel's memory, so cell 5 can use it. This is why order matters — running cell 5 before cell 1 fails, because the bench is still empty.
- **The memory is separate from the file.** You can close a notebook with results visible on screen and still have lost everything, because those results are just a picture of what the kernel did earlier.
- **"Restart the kernel" means clear the bench.** Everything loaded is forgotten and you start from the first cell again. It's the standard fix when a notebook is behaving strangely, and it's completely safe — it never deletes your files.
- **"Select a kernel" means choose which Python to use.** VS Code is asking which Python installation should do the work. You'll always pick the `.venv` one, so it has this project's packages.

### The coastal data side

**Shapefile (`.shp`)**
The map data format you'll recognise from QGIS/ArcGIS. Important quirk: one "shapefile" is really several files sharing a name (`.shp`, `.dbf`, `.prj`, `.shx`). They must always travel together or it won't open.

**AOI**
Area of Interest — one named stretch of coast, e.g. `BrownsBay`.

**Baseline, transect, intersect, rate**
The standard DSAS concepts you already know: the baseline runs behind the shore, transects are drawn perpendicular from it, each shoreline crossing a transect gives an intersection point, and the movement of those points over time gives a change rate.

---

## Part 0.5: How the pieces fit together

Four separate things are involved. People often assume these are one thing, which is where confusion starts:

| Thing | What it is | Where it lives |
| --- | --- | --- |
| The **repository** on GitHub | The shared online copy of the code | github.com |
| Your **local folder** | Your own copy of the code | e.g. `C:\Users\yourname\repos\retrolens` |
| Your **environment** | The box of Python packages the code needs | a hidden `.venv` folder inside your local folder |
| The **data drive** | The shapefiles and imagery the code reads | a network drive, mapped as `Z:` |

**Key point: you work locally.** You edit and run everything on your own computer. Nothing you do affects GitHub or your colleagues until you deliberately "push". You cannot break the shared version by experimenting. This is the whole point of the setup.

Also note the code and the data live in completely different places. The code is in your repo folder; the shapefiles stay on the `Z:` drive and are never copied into the repo.

### About that terminal prompt

When you open a terminal in VS Code you'll see something like:

```
(base) PS C:\Users\ctho213\repos\retrolens>
```

This is the **prompt** — the terminal telling you about itself and waiting for you to type. Reading it left to right:

- `(base)` is the **name of the active Python environment**. `base` is a default one. Once you activate this project's environment it changes to `(.venv)`.
- `PS` means PowerShell, the terminal program itself.
- `C:\Users\ctho213\repos\retrolens` is the **folder you are currently in**.
- `>` is where your typing appears.

The folder and the environment are two independent things that happen to be displayed on the same line:

- the **folder** decides which project your Git commands act on
- the **environment** decides whether your code has the packages it needs

Neither affects the other. Part 3 explains this further, because it's the single most common thing to get muddled.

---

## Part 1: Install the software

You need three programs, and they do three different jobs:

- **Python** — understands and runs the code
- **Git** — tracks your changes and talks to GitHub
- **VS Code** — the window you'll actually sit in and work from

Install them in this order. If your computer is university-managed and blocks installers, you may need IT to approve them.

### 1.1 Install Python

1. Go to https://www.python.org/downloads/
2. Click the "get the standalone installer for Python" button.
3. Run the downloaded installer (double-click it in your Downloads folder).
4. **Important:** on the very first screen, tick the box that says **"Add python.exe to PATH"** before clicking anything else. This tells Windows where to find Python. It's easy to miss, and skipping it causes confusing errors later.
5. Click "Install Now" and wait.

If Python is installed but the terminal still says `python is not recognized`, Windows usually did not add Python to the PATH. The usual fix is to run the installer again, choose **Modify** or **Repair**, and make sure **"Add python.exe to PATH"** is enabled. If you want to test without reinstalling, try `py -3 -m venv .venv` in the terminal instead of `python -m venv .venv`.

### 1.2 Install Git

1. Go to https://git-scm.com/downloads
2. Download the Windows version and run the installer.
3. Click Next through every screen. The defaults are fine — there are a lot of screens and none of them need changing.

You won't see Git as an icon anywhere afterwards. That's expected: it works through the terminal rather than having its own window.

### 1.3 Install VS Code

VS Code (Visual Studio Code) is a free editor from Microsoft. It's where you'll open the project, edit settings, run the notebooks, and use the terminal — all in one window.

1. Go to https://code.visualstudio.com/
2. Download and run the installer.
3. Accept the defaults, and tick **"Add to PATH"** if offered.

### 1.4 Install the VS Code extensions

Extensions are add-ons that teach VS Code new tricks. Out of the box it can't run notebooks, so you need two:

1. Open VS Code.
2. Click the **Extensions** icon in the left sidebar (four small squares), or press `Ctrl+Shift+X`.
3. Search for **Python** — the one published by Microsoft — and click Install.
4. Search for **Jupyter** — also by Microsoft — and click Install.

("Jupyter" is the name of the notebook system; `.ipynb` stands for "IPython notebook", its original name.)

### 1.5 Get access to the data drive

The notebooks read shapefiles from the research drive `ressci201900060-RNC2-Coastal` on `files.auckland.ac.nz`. You need this mapped as drive `Z:` on your computer.

1. Ask the project lead to give your account access to the drive if you don't already have it.
2. In Windows, open File Explorer, right-click **This PC**, choose **Map network drive**.
3. Choose the letter `Z:` and enter the folder path:
   `\\files.auckland.ac.nz\research\ressci201900060-RNC2-Coastal`
4. Tick "Reconnect at sign-in" and sign in with your university credentials.

Check it worked: open `Z:` in File Explorer and confirm you can see folders like `MaxarImagery`, `Retrolens`, and `DSAS`. If you can't reach the drive, the notebooks will not find any files.

Two things to be aware of:

- **Access is granted to you personally.** Until the project lead has added your account to the drive, the mapping step will fail no matter how carefully you follow it. Do step 1 first and wait for confirmation before trying step 2.
- **The mapping is manual and per-computer.** Nothing in this repo sets up the drive for you. Each person maps it themselves on their own machine, and you'd need to repeat it on any other computer you work from. If the drive disappears after a restart or a VPN drop, just map it again.

---

## Part 2: Get a GitHub account and access

1. Create a free account at https://github.com if you don't have one.
2. Send your GitHub username to the project lead and ask to be added as a collaborator on the repository. Without this you can read the code but not push your changes.

---

## Part 3: Get the code onto your computer (clone)

"Cloning" means downloading your own full copy of the online project, permanently linked back to it.

1. Open VS Code.
2. Open a terminal: menu **Terminal > New Terminal** (or press `` Ctrl+` `` — that's the key above Tab, left of the 1). A panel appears at the bottom of the window. This is the terminal.
3. Make a folder to keep projects in, and move into it. Type these one at a time, pressing Enter after each:

```powershell
mkdir C:\Users\$env:USERNAME\repos
```

`mkdir` means "make directory". `$env:USERNAME` automatically fills in your own Windows username, so you can copy this line as-is.

```powershell
cd C:\Users\$env:USERNAME\repos
```

`cd` means "change directory" — it's how you move between folders in a terminal, equivalent to double-clicking a folder in File Explorer. You'll notice the path in your prompt changes to match.

(If `mkdir` says the folder already exists, no problem — just run the `cd` line.)

4. Clone the repository:

```powershell
git clone https://github.com/RNC-Research-Group/retrolens.git
```

This downloads everything and creates a folder called `retrolens`. It may ask you to sign in to GitHub.

5. Move into that new folder:

```powershell
cd retrolens
```

6. Switch to the workflow branch. Cloning gives you `main`, but the shoreline-update work lives on a branch called `nzccdv2`:

```powershell
git checkout nzccdv2
```

This is the branch everyone starts from. Your own branch (Part 5) will be made from this one, not from `main`.

7. Tell Git who you are. This labels your saved changes so the team knows who made them. You only ever do this once on a computer:

```powershell
git config --global user.name "Your Name"
git config --global user.email "your.email@example.com"
```

Keep the quote marks, and use your real name and the email attached to your GitHub account.

8. In VS Code, go to **File > Open Folder** and select `C:\Users\yourname\repos\retrolens`. The project's files now appear in the sidebar on the left. (This is what people mean by "opening the workspace".)

The sidebar deliberately shows only the files this workflow uses. The project contains a lot of other code for unrelated mapping work, and it's hidden so it can't confuse you. Nothing has been deleted — if you ever want to see it all, open **File > Preferences > Settings**, search for `files.exclude`, and clear the entries.

### How Git knows which project you mean

This trips up almost everyone, so it's worth a moment.

Git has no menu where you pick a project. It works it out from **the folder your terminal is currently sitting in** — the file path shown in your prompt.

So in this prompt:

```
(base) PS C:\Users\ctho213\repos\retrolens>
```

it's the `C:\Users\ctho213\repos\retrolens` part that tells Git "this is the retrolens project". Any `git` command typed here acts on this repo.

**The `(base)` part is not what does this.** `(base)` is the name of the active *Python environment*, and Git pays it no attention whatsoever. The two are unrelated:

| Part of the prompt | What it controls | Changed by |
| --- | --- | --- |
| `(base)` or `(.venv)` | which Python packages are available when code runs | activating an environment (Part 4) |
| `C:\Users\...\retrolens` | which project your `git` commands apply to | the `cd` command |

You could run `git status` with `(base)` showing, `(.venv)` showing, or no environment at all, and it would behave identically — only the folder matters to Git.

The reverse also holds: if you `cd` somewhere outside this folder and type a Git command, you'll get an error saying "not a git repository", or it may act on a different project entirely. If that happens, come back with:

```powershell
cd C:\Users\yourname\repos\retrolens
```

A terminal opened via **Terminal > New Terminal** starts in whichever folder you have open in VS Code, so if you did step 8 you're already in the right place.

---

## Part 4: Set up the Python environment

Remember from Part 0: an environment is a private box of packages for this project, kept separate so projects can't break each other.

In the VS Code terminal, in the `retrolens` folder, run these one at a time.

**Create the box:**

```powershell
python -m venv .venv
```

This makes a hidden folder called `.venv` inside your project. It takes a few seconds and prints nothing when it works — silence means success. (Terminals are generally quiet when things go well and loud when they don't.)

**Activate it:**

```powershell
.\.venv\Scripts\Activate.ps1
```

If you get a red error about "running scripts is disabled on this system", that's a Windows security default. Run this, then try activating again:

```powershell
Set-ExecutionPolicy -Scope Process -ExecutionPolicy RemoteSigned
```

(`-Scope Process` means it applies only to this terminal window, not your whole computer.)

When activation works, your prompt changes from `(base)` to `(.venv)`. That's your confirmation.

**Install the packages:**

```powershell
python -m pip install --upgrade pip
python -m pip install -r requirements.txt
```

`pip` is Python's package installer. `requirements.txt` is a plain list of everything this project needs, so `-r requirements.txt` means "install everything on that list". Expect a few minutes of scrolling text — that's normal and doesn't need reading.

Here's what you're installing and why:

| Package | What it does here |
| --- | --- |
| `geopandas` | reads and writes shapefiles, handles map data |
| `shapely` | geometry maths (lines, points, intersections) |
| `pandas` | tables of data, like a spreadsheet in code |
| `numpy` | fast numerical maths |
| `rasterio` | reads the imagery/raster files used for uncertainty |
| `rapidfuzz` | fuzzy name matching, for when folder names don't match exactly |
| `statsmodels` | the regression behind the shoreline change rates |
| `folium` | the interactive preview maps inside the notebooks |
| `matplotlib` | plots and charts |
| `pyarrow` | fast data file handling |
| `tqdm` | the progress bars you'll see while it runs |
| `requests` | downloading files from the internet |
| `jupyter-autotime` | shows how long each cell took to run |

**Point VS Code at the environment:**

1. Press `Ctrl+Shift+P`. A search box appears at the top — this is the "command palette", VS Code's way of finding any feature by typing its name.
2. Type `Python: Select Interpreter` and press Enter.
3. Choose the option with `.venv` in its path (usually marked "Recommended").

"Interpreter" is just another word for the Python installation that runs your code.

**One thing to remember:** terminals forget their environment when closed. Each new session, re-run:

```powershell
.\.venv\Scripts\Activate.ps1
```

You don't reinstall anything — the packages stay put. You're only reconnecting to them.

---

## Part 5: Make your own branch

A branch is your own parallel version of the project. Working on your own branch means you cannot break the shared version, and your half-finished experiments don't disturb anyone. **Never work directly on `main` or on `nzccdv2`.**

There are three levels, and it helps to picture them:

| Branch | What it is | Who changes it |
| --- | --- | --- |
| `main` | the long-term project | maintainer only |
| `nzccdv2` | the shoreline-update workflow everyone shares | maintainer only |
| `yourname` | your own copy to work in | you |

Check which branch you're on:

```powershell
git branch --show-current
```

It should say `nzccdv2`. If it doesn't, run `git checkout nzccdv2` first — **your branch must be made from `nzccdv2`**, so that you start with the notebooks, the guide and the settings already in place.

Now create your own, named after yourself in lowercase with no spaces:

```powershell
git checkout -b yourname
```

For example `git checkout -b catriona`. The `-b` means "create this branch and switch to it". You only use `-b` the first time.

To switch to a branch that already exists, leave `-b` out:

```powershell
git checkout yourname
```

At the start of each working session, collect any updates the maintainer has made to the shared workflow:

```powershell
git pull origin nzccdv2
```

When you finish work and want to save it online, push your own branch:

```powershell
git push origin yourname
```

If Git says there is a merge conflict, do not guess. Stop and ask the project lead or the maintainer to help you resolve it.

### Before you begin each run: pre-flight checklist

Before you run the notebooks, check these four things first:

- The shoreline files you want to use have already been drawn and saved in the expected shoreline folder on the `Z:` drive.
- The baselines have already been drawn and merged into the regional baseline in the expected baseline folder on the `Z:` drive.
- The AOI polygons for your AOI extent already exist and are stored in the expected AOI folder on the `Z:` drive.
- Your notebook settings still match across all three notebooks: `RUN_OWNER`, `search_mode`, `cutoff_date`, `target_aoi`, `target_region`, and `search_roots`.

If one of these is missing, do not start the notebook workflow yet. Fix the missing data or the missing files first.

---

## Part 6: Change the settings for your run

This is the only place you edit anything. You're changing values, not writing code.

All three notebooks share the same shoreline-selection settings, and **the settings must match across all three**. If they don't, each notebook processes a different set of files and the results won't line up.

Open [new_transects.ipynb](new_transects.ipynb) and find the cell near the top containing these lines:

```python
cutoff_date = pd.Timestamp("2024-07-18")
search_roots = [Path(r"Z:\MaxarImagery\HighFreq"), Path(r"Z:\Retrolens")]
search_mode = "date"
target_aoi = "BrownsBay"
target_region = "Auckland"

RUN_OWNER = "yourname"
```

Each line sets one value: the name on the left, an `=` sign, then the value. The `#` lines above them are comments — notes for humans that the computer ignores.

What each one does:

- **`RUN_OWNER`** — your name, lowercase, no spaces. This creates your own output folder, `DataUpdatev2/yourname/`, so that if you and someone else both process the same AOI, neither of you overwrites the other. **Set this first, and use the identical value in all three notebooks** — the later notebooks read the earlier ones' files out of this folder, so a mismatch means "file not found".
- **`search_mode`** — how shoreline files get chosen. Pick exactly one of:
  - `"date"` — everything modified after `cutoff_date` (the usual choice for routine updates)
  - `"aoi"` — one specific AOI, any date
  - `"aoi_in_date_range"` — one specific AOI, only if modified after `cutoff_date`
  - `"region"` — every AOI in one region, any date
  - `"region_in_date_range"` — every AOI in one region, modified after `cutoff_date`
- **`cutoff_date`** — the date to search from. Keep the `pd.Timestamp("YYYY-MM-DD")` wrapper exactly, changing only the date inside: `pd.Timestamp("2025-01-31")`.
- **`target_aoi`** — the AOI name, e.g. `"BrownsBay"`. Only used by the AOI modes.
- **`target_region`** — the region name, e.g. `"Auckland"`. Only used by the region modes.
- **`search_roots`** — where to look on the `Z:` drive. Leave this alone.

### Rules for editing safely

- Change only the text **inside the quote marks**.
- Keep the quote marks themselves. To Python, `"date"` is a piece of text but `date` without quotes is a command — dropping them causes an error.
- Don't add spaces before the start of a line. Indentation is meaningful in Python.
- Names must match the folders on the `Z:` drive, including capitals: `BrownsBay`, not `brownsbay` or `Browns Bay`.
- Save with `Ctrl+S` after editing.

Unused settings are harmless — if `search_mode` is `"date"`, then `target_aoi` is simply ignored, so you can leave it as it is.

Now make the same changes in the matching cell of [new_uncy.ipynb](new_uncy.ipynb) and [new_DSAS.ipynb](new_DSAS.ipynb). `RUN_OWNER` especially must be identical in all three.

---

## Part 7: Run the notebooks

Run the three notebooks **in this order**. Each one uses the outputs of the one before, so the order is not optional.

### How to run a notebook

1. Click the notebook file in the VS Code sidebar on the left to open it.
2. Look at the **top right** of the notebook. If it says "Select Kernel", click it and choose the `.venv` option. (As covered in Part 0, this is you telling VS Code which Python should do the work — you want the one with this project's packages.)
3. Run the cells. You have two options:
   - **Run All** at the top runs everything from top to bottom.
   - The small **▷ arrow** to the left of each cell runs just that cell.

**Run cells one at a time for your first few goes.** You'll see each step's output as it appears, which makes it far easier to spot where something went wrong. Once you trust it, Run All is fine.

While a cell is running you'll see a spinner or a progress bar, and a `[*]` beside the cell. When it finishes, that becomes a number. Some cells take several minutes — the DSAS one especially. A slow cell is not a stuck cell.

### Things that will look alarming but aren't

- **Warnings in yellow or pink boxes.** Warnings are not errors. If the cell finished and produced output, it worked.
- **A wall of scrolling text during installs or runs.** Normal.
- **Numbers beside cells jumping around** (e.g. `[7]` then `[12]`). They just count the order things were run in.

### When a notebook misbehaves

If results look wrong, or a variable seems to have vanished, the usual cause is that cells were run out of order, so the kernel's memory doesn't hold what you think it does.

The fix is almost always: click **Restart** at the top of the notebook, then run the cells again from the top. This clears the kernel's memory and gives you a clean start. It never deletes files or code — it only clears what Python was holding in memory.

### Step 1 — [new_transects.ipynb](new_transects.ipynb)

Creates the transect lines. As it runs, check:

- the table of matched shoreline files is not empty (if it is, your settings matched nothing)
- **Table 1** lists AOIs whose polygon couldn't be found — these are skipped
- **Table 2** lists AOIs with no baseline overlap — these are skipped too
- the QA summary near the end says all checks passed

Skipped AOIs aren't necessarily a bug, but if an AOI you specifically wanted is on those lists, sort that out before continuing.

### Step 2 — [new_uncy.ipynb](new_uncy.ipynb)

Calculates uncertainty for each shoreline row. Merged shapefiles may contain many dates and sources, so check `new_uncy_row_report.csv` and `new_uncy_row_missing.csv`, not only the legacy file-level summary. This notebook reads source shapefiles and imagery metadata but does not write to the source shoreline shapefiles.

### Step 3 — [new_DSAS.ipynb](new_DSAS.ipynb)

Builds the updated dataset and calculates the shoreline change rates. This is the slowest of the three — leave it running.

### If something goes wrong

Read the **last line** of a red error message first. Python puts the actual problem at the bottom, after a long trace of where it happened. Common ones:

| Message | What it means | Fix |
| --- | --- | --- |
| `ModuleNotFoundError` | a package is missing, or the wrong kernel is selected | check the kernel is `.venv`; redo Part 4 |
| `FileNotFoundError` | it can't find a file, usually on `Z:` | check the drive is connected in File Explorer |
| `NameError` | using something not yet created | you ran cells out of order — restart and run from the top |
| Empty tables, no matches | your date or AOI settings match nothing | re-check Part 6 spelling and dates |
| `not a git repository` | your terminal is in the wrong folder | `cd` back to the repo folder |

If you're stuck, copy the last few lines of the error and send them to whoever maintains the project. The error text is far more useful than a description of it.

---

## Part 8: Where the outputs go

Everything is written to your own folder inside the repo: `DataUpdatev2/yourname/`, where `yourname` is whatever you set `RUN_OWNER` to.

| File | What it contains |
| --- | --- |
| `new_transects.shp` | the transect lines, with `Unique_ID`, `MEAS`, `DIST`, region and AOI |
| `new_uncy_row_report.csv` | one row per shoreline feature: date, source, Pixel_ER, Georef_ER, CPS, Dig_ER, Total_UNCY, provenance and status |
| `new_uncy_row_missing.csv` | shoreline rows where an uncertainty component could not be resolved |
| `new_uncy_summary.csv` | legacy file-level summary from older runs |
| `new_uncy_missing.csv` | legacy file-level missing report from older runs |
| `NZCCDv2_<tag>.shp` | the shoreline dataset **for your area only** (the NZCCDv1 rows for your AOIs, plus the new shorelines) |
| `intersectsv2_<tag>.shp` | the points where each shoreline crosses each transect |
| `ratesv2_<tag>.shp` | the shoreline change rates attached to each transect |
| `ratesv2_<tag>.csv` | the same rates as a spreadsheet, without the map geometry |
| `intersectsv2_<tag>.csv` | the same intersection points as a spreadsheet, without the map geometry |
| `new_dsas_exclusions_<tag>.csv` | shoreline files left out of the results, and why |

### What `<tag>` means

The DSAS notebook puts your selection into the filename, so nobody overwrites anybody else. If you ran the `region_in_date_range` mode for Auckland with a cutoff of 18 July 2024, you get `NZCCDv2_Auckland_since20240718.shp`. If you ran `aoi` mode for Medlands Beach, you get `NZCCDv2_MedlandsBeach.shp`.

Two consequences worth understanding:

- **Your NZCCDv2 is a slice, not the whole country.** Coastline outside the AOIs you ran is dropped on purpose. That is what makes it possible to combine your work with someone else's later.
- **You never merge your slice into the national dataset yourself.** The project maintainer does that with `NZCCDv2_merge.ipynb`, which reads everyone's folders and stitches them back together.

Between `RUN_OWNER` and the tag, nothing you produce can be overwritten by anyone else — and the only way to overwrite your *own* work is to re-run the same area yourself, which is usually what you want.

You can open the `.shp` files in QGIS or ArcGIS to look at them on a map, and the `.csv` files in Excel.

Note that a shapefile is really several files sharing one name (`.shp`, `.dbf`, `.prj`, `.shx` and so on). If you copy one somewhere else, copy all of them together or it will not open.

### Pipeline reference: inputs and search

The three notebooks share `cutoff_date`, `search_roots`, `search_mode`, `target_aoi`, `target_region`, and `RUN_OWNER`. The search roots are normally:

- `Z:\MaxarImagery\HighFreq\<Region>\<AOI>\Shorelines\*.shp`
- `Z:\Retrolens\<Region>\<AOI>\Shorelines\*.shp`

Supporting inputs are read from `Z:\MaxarImagery\HighFreq\AOI\` (AOI polygons), `Z:\DSAS\BaselineTemplate\Baselines\` (regional baselines), `Z:\DSAS\BaselineTemplate\Routes\` or `Data for testing/Routes/` (routes), and `Data for testing/NZCCDv1.shp` (the starting dataset). `new_transects.ipynb` and `new_DSAS.ipynb` also need `lds-nz-coastlines-and-islands-polygons-topo-150k-GPKG.zip` (the LINZ *NZ Coastlines and Islands Polygons (Topo 1:50k)* layer, exported as GeoPackage from the LINZ Data Service) in the repo root or in `Data for testing/` — it tells the code which end of each transect is on land, so change rates always come out with positive = accretion. Maxar mosaics live in the Maxar `Stack` folder; Retrolens mosaics live in the Retrolens `Stack` folder. Each mosaic may have a `.jp2.aux.xml` sidecar containing its pixel resolution.

`target_aoi` and `target_region` can be strings or lists. Matching ignores case and punctuation and checks both the AOI folder and the AOI part of the shoreline filename. `cutoff_date` filters file modification time. It does not define the observation date used by uncertainty or DSAS.

### Pipeline reference: transects and IDs

`new_transects.ipynb` finds the selected shoreline files, resolves AOI polygons and baselines, filters each baseline to its AOI, selects the route with the greatest AOI overlap, and creates transects at 10 m spacing. Each `Unique_ID` is:

```text
3-digit route code + 9-digit rounded centimetres along route
```

`MEAS` is metres along the route and `DIST = round(MEAS * 100)` is centimetres. Route codes are `100` North Island, `101` Waiheke, `102` Matakana, `200` South Island, `201` Jackett, `202` Moturoa/Rabbit, and `203` Rakiura/Stewart. Duplicate `DIST` values are nudged by centimetres, first within an AOI and then between AOIs sharing a route. The adjustment and all skipped items are recorded in `new_transects.csv`; QA requires unique 12-digit IDs.

Each transect is also oriented against the LINZ land polygons so its last vertex sits on the land side (voted per baseline segment). Without this, a baseline digitised with the sea on its left produces transects whose rates come out sign-reversed. Reversed segments are logged in `new_transects.csv` as `ADJUSTED`.

### Pipeline reference: uncertainty

`new_uncy.ipynb` evaluates every shoreline feature row and writes CSV reports only. For each row, date precedence is `DSAS_Date`, then `Date`, then filename. Source precedence is the `Source` attribute, then LDS survey-year inference when applicable, then the folder as a final fallback. `LZ`/`LINZ` becomes `LDS`, `MAXAR` becomes `MAX`, and Retrolens aliases become `RL`.

`Pixel_ER` uses the row attribute first. For `MAX`, it then searches the exact-date mosaic in `Z:\MaxarImagery\HighFreq\<Region>\<AOI>\Stack\`. For `RL`, it searches the exact-date mosaic in `Z:\Retrolens\<Region>\<AOI>\Stack\`, then accepts the nearest dated Retrolens mosaic within 92 days. The `.jp2.aux.xml` sidecar supplies the pixel size, with header/rasterio fallbacks. LDS has no local mosaic: 1999/2000/2003 use `2.5 m`, 2012 uses `0.5 m`, and 2017/2020/2022/2024 use `0.075 m`; otherwise the LDS default applies.

`Georef_ER` uses the row attribute first. If absent, RL reads photoscale from the AOI CSV beside the Stack/Shorelines folder and assigns `2.09`, `2.43`, or `2.90`; MAX is `1.17`; LDS/LZ is `0`. `CPS` maps to `Dig_ER` as `{1: 0.43, 2: 0.73, 3: 0.97, 4: 2.07, 5: 8.59}`. Missing or invalid CPS defaults to `1`.

```text
Total_UNCY = sqrt(Pixel_ER^2 + Georef_ER^2 + Dig_ER^2)
```

Use `new_uncy_row_report.csv` as the current report and DSAS input. It records each row's date, source, three error components, total, provenance, and status. `new_uncy_row_missing.csv` lists unresolved rows. The older `new_uncy_summary.csv` and `new_uncy_missing.csv` are legacy file-level reports.

### Pipeline reference: DSAS

`new_DSAS.ipynb` repeats the target search, loads `new_transects.shp`, and applies the row-level uncertainty report by source file and geometry. It keeps each row's own `DSAS_Date`/`Date`, so merged shapefiles remain multi-date observations. For every transect it intersects the dated shoreline rows, selects one point per shoreline, sorts by date, and requires at least three observations.

It calculates `NSM` (first-to-last movement), `SCE` (maximum separation), `EPR` (NSM divided by elapsed years), `LRR` (ordinary least-squares rate and diagnostics), `EPRunc` (endpoint uncertainty divided by duration), and `WLR` (weighted least-squares with weights `1 / Total_UNCY^2` when all observations have uncertainty). Missing dates exclude rows. Missing uncertainty prevents weighted rates but still allows unweighted rates.

Distances are measured from the transect end that the LINZ land polygons say is landward of the measured shoreline, so positive rates always mean accretion regardless of how the transect's vertices are ordered. Each rate row records the decision in `OrientFix` (`kept`, `reversed`, or a warning value `undecided`/`no_land`), and the notebook prints a per-AOI summary of reversals — check that summary after every run.

**Performance and machine requirements.** The transect loop prefilters shorelines with a spatial index (only rows whose geometry actually touches the transect are processed, in stable table order so results are identical to the unfiltered loop) and fans the work across every CPU core — worker processes on Linux/macOS, threads on Windows (a smaller speed-up there, since threads share one Python interpreter). Measured on a 32-core / 62 GB Linux machine: an AOI-scale run (4,298 transects × 1,120 shoreline rows) takes ~10 s end to end with ~0.3 GB peak RAM, and a national-scale run (25,808 transects × 8,214 shoreline rows) takes ~1.7 min with ~1 GB peak in the main process plus ~0.2 GB per worker (forked workers share memory with the main process, so the total stays within a few GB). Runtime scales roughly linearly with transect count and inversely with core count — expect a national-scale run in the order of 10–15 minutes on a 4-core laptop, and any AOI-scale run in well under a minute. 8 GB of RAM is comfortable for any current run size; no GPU is used.

---

## Part 9: Save your work back to GitHub

Git saves work in three separate moves. They feel repetitive at first, but each does a distinct job:

1. **add** — choose which changes to include
2. **commit** — save them as a labelled snapshot, on your computer
3. **push** — upload those snapshots to GitHub

A commit is local only. Until you push, your work exists nowhere but your own machine — which also means an unpushed commit won't survive a lost laptop.

**See what you've changed:**

```powershell
git status
```

This lists modified files. It changes nothing and is always safe to run — use it freely whenever you're unsure where things stand.

**Stage your changes:**

```powershell
git add .
```

The `.` means "everything that changed in this folder".

**Commit them with a message:**

```powershell
git commit -m "Run workflow for Auckland region shorelines"
```

`-m` introduces the message. Keep the quote marks. Write something your future self would understand — "stuff" and "update" are not helpful six months later.

**Push to your branch** (not `main`):

```powershell
git push origin yourname
```

`origin` is Git's nickname for the GitHub copy. Replace `yourname` with your branch name.

The first time you push a new branch, Git may reply with a longer suggested command such as `git push --set-upstream origin yourname`. Copy and run exactly what it suggests — Git is being helpful, not complaining. After that, plain `git push` works.

If a browser window opens asking you to sign in to GitHub, do so. This normally happens only once.

### A note on large output files

**The `DataUpdatev2` folder is deliberately kept out of Git.** If `git status` shows nothing after a run, that's expected rather than broken.

The reason is worth knowing. Shapefiles are binary files, so Git can't merge them the way it merges code. If two people both committed their own `NZCCDv2`, Git would hit a conflict it cannot resolve, and one person's work would be thrown away. Every commit of a shapefile also stores a complete fresh copy — a single NZCCDv2 is roughly 65 MB, so the repository would grow by that much every run, permanently, for everybody.

So: **code goes in Git, data does not.** To hand over your results, copy your `DataUpdatev2/yourname` folder to the `Z:` drive (or wherever the maintainer asks). They run `NZCCDv2_merge.ipynb` to combine it with everyone else's.

What you *do* commit is any change you made to the notebooks or settings.

### Getting your work into `nzccdv2`

Don't merge into `nzccdv2` or `main` yourself. Instead:

1. Push your branch as above.
2. Go to the repository page on GitHub.
3. Click the **Pull requests** tab, then **New pull request**.
4. Set your branch as the source and **`nzccdv2`** as the target (not `main`), add a short description, and create it.
5. Someone on the team reviews it and merges it.

Remember this is only your *code and settings* changes. Your data outputs are handed over separately, as described above.

---

## Working on more than one computer

Common for students — a personal laptop, a lab machine, a desktop in the department. This is fine, but it helps to know what travels with you and what doesn't.

### What has to be redone on each computer

All of this is tied to the machine, not to you. On a new computer you repeat:

| Step | Why it doesn't travel |
| --- | --- |
| Install Python, Git, VS Code, extensions (Part 1) | software is installed per machine |
| Map the `Z:` drive (Part 1.5) | drive mappings are per machine, per user |
| `git config` your name and email (Part 3) | stored in that computer's settings |
| Clone the repo (Part 3) | you need a local copy on each machine |
| Create `.venv` and install packages (Part 4) | see the warning below |
| Select the interpreter and kernel (Parts 4 and 7) | a VS Code setting on that machine |

In short: the whole of Parts 1 to 4 again. It's quicker the second time, and `pip install -r requirements.txt` means you never have to remember what the packages were.

**Never copy a `.venv` folder between computers** (or onto a USB stick). It contains hard-coded paths to the machine it was built on and will break in confusing ways. Always create a fresh one with `python -m venv .venv`. For the same reason, `.venv` is deliberately never uploaded to GitHub.

### What follows you automatically

Once pushed to GitHub, these are waiting for you on any machine:

- your branch
- every commit you made
- any code or settings changes in those commits
- `requirements.txt`, so you can rebuild the environment identically

### Moving between machines cleanly

**Before you leave computer A**, save and upload your work:

```powershell
git status
git add .
git commit -m "what I did today"
git push
```

**On computer B**, if it's already set up:

```powershell
cd C:\Users\yourname\repos\retrolens
.\.venv\Scripts\Activate.ps1
git checkout yourname
git pull
```

`git pull` brings down what you pushed from computer A. If computer B is new, do Parts 1 to 4 first, then `git checkout yourname` to get onto your branch.

### Things that catch people out

- **Unpushed work exists in exactly one place.** If you finish on the lab computer and forget to push, that work is not on your laptop and not on GitHub. Get into the habit of committing and pushing before you walk away.
- **Outputs don't travel via GitHub.** The files in `DataUpdatev2` are large and mostly excluded from Git on purpose. On a new machine you'll have an empty `DataUpdatev2` even after pulling. Either re-run the notebooks or copy the outputs across via the `Z:` drive.
- **Forgetting `git pull` first.** Starting work on computer B without pulling means editing an old version, which creates conflicts to untangle later. Pull first, always.
- **University-managed machines may block installers.** If you can't install Python or Git on a lab computer, check whether they're already there before asking IT — many teaching machines have them.
- **Shared computers.** If you sign in to GitHub on a machine other people use, sign out when you're finished.

### The safest habit

Treat GitHub as the master copy and each computer as disposable. Pull at the start, push at the end. Do that and moving machines is uneventful — which is exactly what Git is for.

---

## Everyday checklist

Once you're set up, a normal working session looks like this. Open VS Code, open a terminal, then:

```powershell
cd C:\Users\yourname\repos\retrolens
.\.venv\Scripts\Activate.ps1
git checkout yourname
git pull
```

In plain English: go to the project folder, switch on its packages, make sure you're on your own branch, and collect any updates.

Then edit the settings (Part 6), run the three notebooks in order (Part 7), check the outputs in `DataUpdatev2` (Part 8), and finish with:

```powershell
git add .
git commit -m "short description of what you did"
git push
```

---

## Command cheat sheet

Every command in this guide, in one place. Terms are explained in Part 0.

| Command | Plain English |
| --- | --- |
| `cd <folder path>` | go to that folder |
| `.\.venv\Scripts\Activate.ps1` | switch on this project's packages |
| `git branch --show-current` | which branch am I on? |
| `git checkout -b yourname` | create a new branch and switch to it |
| `git checkout yourname` | switch to a branch that already exists |
| `git pull` | download other people's changes |
| `git status` | what have I changed? (always safe) |
| `git add .` | select all my changes to be saved |
| `git commit -m "message"` | save a labelled snapshot on my computer |
| `git push` | upload my snapshots to GitHub |

Two reassurances worth holding onto:

- `git status`, `git branch --show-current` and `cd` only look at things or move you around. They change nothing and cannot break anything.
- Nothing you do locally affects your colleagues until you `push`. Experiment freely.

---

## Still stuck?

When asking for help, include these four things and you'll get an answer much faster:

1. Which Part or notebook you were on.
2. The **exact** error text, copied and pasted (a screenshot of the last few lines is fine).
3. What your terminal prompt says — it shows your folder and environment at a glance.
4. What you'd already tried.

