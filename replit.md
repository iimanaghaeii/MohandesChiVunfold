# Telegram Bot Project

## Overview
This is a Telegram bot written in Python that requires users to join a specific Telegram channel and view the last 3 channel posts before they can use the bot's features. The bot tracks which posts users have seen using a SQLite database.

## Purpose
- Enforce channel membership for bot access
- Track user engagement with channel posts
- Provide a gateway mechanism for bot features

## Current State
The bot is configured and running on Replit. It requires Telegram bot credentials to be set up in environment variables.

## Project Architecture

### File Structure
- `bot.py` - Main bot application with command handlers
- `utils/`
  - `config.py` - Configuration and environment variable loading
  - `auth.py` - User authentication and membership verification
  - `storage.py` - SQLite database operations for tracking seen posts
  - `channel.py` - Channel-related utilities and button creation
- `data/` - SQLite database storage directory
- `requirements.txt` - Python dependencies

### Technology Stack
- **Language**: Python 3.12
- **Bot Library**: pyTelegramBotAPI (async)
- **Database**: SQLite
- **HTTP Client**: aiohttp
- **Environment**: python-dotenv

### Key Features
1. Channel membership verification
2. Post view tracking (last 3 posts)
3. Interactive inline keyboard buttons
4. Async/await support for better performance

## Configuration

### Required Secrets (via Replit Secrets)
The bot requires two secrets to be set in Replit's Secrets manager:
- `BOT_TOKEN` - Your Telegram bot token from BotFather
- `CHANNEL_USERNAME` - The channel username (format: @channelname)

**IMPORTANT**: Never commit bot tokens to git. Use Replit's built-in Secrets feature.

### Setup Instructions
1. Go to BotFather on Telegram and create/get your bot token
2. Add the bot token and channel username to Replit Secrets
3. Update the `LAST_POSTS` array in `bot.py` with actual message IDs from your channel
4. Restart the bot workflow

## How It Works
1. User sends `/start` command
2. Bot checks if user is a member of the specified channel
3. If not a member, shows "Join Channel" button
4. If member, checks which of the last 3 posts the user has viewed
5. Shows buttons for unviewed posts
6. When user marks all 3 posts as viewed, they gain access to core bot features

## Recent Changes (Nov 4, 2025)
- Initial project import from GitHub
- Installed Python dependencies (pyTelegramBotAPI, python-dotenv, aiohttp)
- Fixed async/await compatibility issues (changed to use AsyncTeleBot from telebot.async_telebot)
- Created data directory for SQLite database
- Added comprehensive .gitignore for Python projects (including .env)
- Configured Replit workflow to run the bot
- Removed exposed bot token from repository
- Added placeholder implementation for `get_last_3_posts()` with documentation on how to implement it properly
- Moved to Replit Secrets for secure credential management

## Development Notes
- The bot uses async/await throughout for better performance
- Database is initialized automatically on first run
- **Post IDs are currently set to placeholder values [1, 2, 3]** - You must update these with actual message IDs from your channel
- The original implementation attempted to use non-existent Telegram API endpoints (getChatHistory)
- To get actual message IDs: Forward messages from your channel to @userinfobot or check the channel admin panel

## Important Security Note
**The original imported code had a bot token committed in .env file.** This has been removed. If this was your active bot:
1. Revoke the old token immediately via BotFather
2. Generate a new token
3. Add it to Replit Secrets (never commit tokens to git)

## User Preferences
None documented yet.

## Next Steps
- Implement proper channel post fetching mechanism
- Consider using Telegram's native message forwarding instead of custom API calls
- Add more bot features in the `core_main` function
