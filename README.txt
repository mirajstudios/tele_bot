========================================
  TELEGRAM LINK MANAGER BOT — SETUP
========================================

REQUIREMENTS
------------
- Python 3.10 or newer
- pip (Python package manager)

INSTALLATION
------------
1. Install the required library:
   pip install python-telegram-bot

2. Open bot.py and replace:
   BOT_TOKEN = "YOUR_BOT_TOKEN_HERE"
   with your actual token from @BotFather on Telegram.

HOW TO GET A BOT TOKEN
-----------------------
1. Open Telegram and search for @BotFather
2. Send: /newbot
3. Follow the steps and copy the token it gives you
4. Paste it into bot.py

RUNNING THE BOT
---------------
   python bot.py

MAKE THE BOT ADMIN IN YOUR GROUP
----------------------------------
1. Open your Telegram group
2. Go to Settings > Administrators
3. Add your bot as admin
4. Enable: "Delete Messages" permission

HOW IT WORKS
------------
- Someone sends a link in the group
  → Bot deletes their message
  → Bot reposts the link with their username
  → Total link counter increases

- /list    → Shows all users who sent links + their count
- /stats   → Shows total link count
- /help    → Shows usage guide

REMOVE YOURSELF FROM THE LIST
-------------------------------
Send a VIDEO in the group with caption:  ad  or  add
The bot will remove your username from the /list

HOSTING (keep it running 24/7)
--------------------------------
Free options:
  - Railway.app  (https://railway.app)
  - Render.com   (https://render.com)

Cheap VPS (~$4/month):
  - Hetzner, DigitalOcean, Vultr

On a server, run with:
  screen -S bot python bot.py
  (press Ctrl+A then D to detach)

========================================
