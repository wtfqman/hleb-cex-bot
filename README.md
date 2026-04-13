# hleb-cex-bot

This is a Python Telegram bot, not a Node.js project, so `npm start` will not work here because there is no `package.json` in the project root.

## Run On Windows

```powershell
py -3.12 -m venv .venv
.\.venv\Scripts\python.exe -m pip install -r requirements.txt
.\.venv\Scripts\python.exe main.py
```

## If The Old `venv` Is Broken

The existing `venv` folder points to a missing Python interpreter at a path similar to `C:\Users\user\...`.
On this machine, use the new `.venv` environment shown above.

## Entry Point

Start the bot with `main.py`.
