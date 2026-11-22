# Start here

Welcome to StatProj (LS03 – Team 1). You do not need any data background to begin.
This page tells you how to set up your computer and how to work with your AI assistant.

## 1. What the project is about, in one paragraph

A US government survey (the 2022 NHTS) asked people to record every trip they made on one
day. We look at trips from home to work and back, made on weekdays by adults. For each
trip we know how long it took, how far home is from work, which vehicle was used, what
time the person left, which direction they went (to work or home), and whether they live
in a city or the countryside. **Our question:** using only what is known before leaving,
how well can we predict how many minutes a commute will take? The first half of the
project (exploring the data, called EDA) is finished. Now the team builds and tests
prediction methods. More background: `docs/PROJECT_BACKGROUND.md`.

## 2. Set up your computer (once)

You need **Git** and **Python 3.10–3.13** (3.12 recommended). Then, in a terminal opened in
this folder:

| Your computer | Command |
|---|---|
| Windows | double-click `setup.cmd`, or run `powershell -ExecutionPolicy Bypass -File setup.ps1` |
| macOS / Linux | `bash setup.sh` |

The script creates a private Python environment in `.venv/`, installs the libraries from
`requirements.txt`, builds fake test data and runs the checks. It ends with
`... passed` when everything works. Each time you open a new terminal, activate the
environment:

| Windows | macOS / Linux |
|---|---|
| `.venv\Scripts\activate` | `source .venv/bin/activate` |

The real data files must be in `Data/` (they come with the repository). If the script says
a data file is missing, tell the team before going further.

## 3. Work with your AI assistant

Open this folder in your AI tool (Claude Code, Codex, Cursor, GitHub Copilot Chat, …).
These tools read `AGENTS.md` automatically. Start with a message like:

> Tôi là **Galvin** (hoặc Jovie / Anthony). Hãy đọc hướng dẫn của dự án, cho tôi biết dự án
> đang ở đâu, phần việc của tôi là gì và bước tiếp theo nên làm.

The assistant will answer in Vietnamese, explain one step at a time, and ask you to run
the commands yourself. Ask as many questions as you like ("Cột này nghĩa là gì?",
"Tại sao lại chia theo hộ?"). The goal is that **you** understand the work, because every
member is questioned in the final defence.

**If your AI tool cannot read files** (for example a chat website), attach `AGENTS.md`,
this file, your file in `docs/team/` and `CONTRACT.md`, then paste the message above.

## 4. Your part

| Name | Part | Your guide |
|---|---|---|
| Galvin | Turn the raw data into clean tables | `docs/team/galvin.md` |
| Jovie | Build the prediction methods | `docs/team/jovie.md` |
| Anthony | Split for fair testing, score the methods, final check | `docs/team/anthony.md` |

You can start today: everyone can work on **fake data** first (`python -m src.make_fixture`)
because the shared formats are fixed in `CONTRACT.md`.

## 5. Daily workflow

1. `git checkout main` and `git pull` to get the latest version.
2. `git checkout -b feature/<your-name>-<task>` for new work (or switch to your branch).
3. Work in your own files only. Run `python -m pytest` before you share.
4. `git add <files>`, `git commit -m "short description"`, `git push -u origin <branch>`.
5. Open a pull request on GitHub and ask your reviewer (see `README.md`, "Team rules").
6. Add an entry to your section of `AI_USE.md`.
