# Git workflow, step by step

Git keeps the history of every file and lets four people work at the same time without
overwriting each other. GitHub is the shared copy online:
<https://github.com/qfc88/StatProj>. Your AI assistant can run these commands with you;
read what each one does before running it.

## Words you need

| Word | Meaning |
|---|---|
| repository (repo) | The project folder with its full history |
| clone | Download the repo to your computer (once) |
| branch | Your own line of work. `main` is the shared, reviewed version |
| commit | A saved snapshot of your changes, with a short message |
| push | Send your commits to GitHub |
| pull | Get the newest commits from GitHub |
| pull request (PR) | A request to add your branch to `main`, reviewed by a teammate |
| merge | Add the reviewed branch into `main` |

## 1. Get the project (once)

```bash
git clone https://github.com/qfc88/StatProj.git
cd StatProj
```

Then run the setup (`setup.cmd` on Windows, `bash setup.sh` on macOS/Linux).

## 2. Start of every work session

```bash
git checkout main
git pull                                  # newest shared version
git checkout feature/<name>-<task>        # back to your branch, if you already have one
git merge main                            # bring the newest main into your branch
python -m src.status --name <YourName>    # what exists and what is pending
```

## 3. Start a new task: make a branch

Never edit on `main`. One branch per task, named `feature/<name>-<task>`:

```bash
git checkout main
git pull
git checkout -b feature/galvin-baseline
```

## 4. Save your work (commit), often

```bash
python -m pytest                    # checks must pass
git status                          # what changed? only your own files should be listed
git add src/models.py               # add the files you changed, by name
git commit -m "Add baseline median predictions"
```

Write the message as "what this commit does". Do not add `outputs/`, `.venv/`, data
changes, passwords or personal files; `git status` must not list them for adding.

## 5. Share your work (push)

```bash
git push -u origin feature/galvin-baseline   # first time on this branch
git push                                     # later times
```

## 6. Ask for review (pull request)

On GitHub, open the repo; a yellow bar offers **Compare & pull request**. Or with the
GitHub CLI: `gh pr create --fill`. In the description write:

1. **What I did** (two or three sentences).
2. **How to run it** (exact commands).
3. **What I checked** (counts, tests, a hand example) and the real output.
4. **What this lets us conclude**, and what it does not.
5. **Pending**: what my teammates need to do next.

Ask your reviewer (`docs/team/README.md`). The reviewer reads the code, runs it, and
comments or approves. After approval, the author clicks **Merge**, then everyone pulls.

## 7. After your PR is merged

```bash
git checkout main
git pull
git branch -d feature/galvin-baseline    # delete the finished branch locally
```

Tell the team in the group chat what is now available (see `docs/INTEGRATION.md`).

## Common problems

| Message | What it means | What to do |
|---|---|---|
| `rejected ... fetch first` | GitHub has commits you do not have | `git pull`, then `git push` again |
| `CONFLICT (content)` | You and someone else changed the same lines | Ask your AI assistant to explain the conflict; keep the correct lines; `git add` the file; `git commit` |
| `You are on main` (from `src.status`) | Editing on the shared branch | `git checkout -b feature/<name>-<task>` before changing files |
| `Your branch is behind` | Newer commits exist | `git pull` |
| Files under `outputs/` appear | Generated files | Do not add them; they are rebuilt by the scripts |
