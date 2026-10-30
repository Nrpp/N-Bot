# N-Bot

*Pulse* is a Discord bot that I made in Python (discord.py)

I wanted to make something useful and that could entretain and make you be more organized.

## What can it do?

### Profiles (/profile)

Every person has:
* XP
* Level
* Coins
* Daily streak

### Tasks

```
/task add Finish my homework
/task list
/task done 1
/task delete 1
```

### Reminders

`/remind 30m Study for my exam`

The bot check every 30 seconds to see when the reminder is due

### Daily rewards

There's one reward per day that the people in the server can claim.
There's also a streak of how many days you've been claiming your daily rewards to encourage people to keep doing it.

`/daily`

### Leaderboard

I think there's nothing to be said here 😁

`/leaderboard`

### Server pet

The server has a shared pet that everyone needs to take care of. It has:
* Hunger
* Happiness
* ENergy statistics

```
/pet
/feed
/play
/rest
```

### Extra (for extra points 😁)

```
/coinflip
/roll
/help
```

## How it works

There are two pyhton files.

* *bot.py* --> contains the comands and bacground tasks
* *database.py* --> conatins the database and all of the functions for storing users, tasks, reminders and the pet

# Development

I started with the discord basic bot tutorial and escalated with the database of SQLite that I learned in a course of python. 

One of the things I found dificult about this proyect is that the things that seem short and easy to make were the ones that took the longer. FOr example /daily. It is not only a comand that gives you exp, there's a lot going on: the last time you took a reward, if you've claimed today, ...

The same thing happens with reminder, it need a background task that could keep checking the database even when nobody was using a comand.

## Problems I ran into

### Python versions,

One of the first problems I had was with python because I had diferent versions installed (between them the last one) and it was not taking that one.

Finnally, I figured out that in the variables of windows the Python 2.7 was in the top part.

### Daily streaks

This was also a problem because it needed a lot of parameters and things

# Hosting

Once the bot was FINALY working, I wanted it to run without my pc on, so, as the guide said, I aplied for Nest and the days passed and I haven't recieved yet nothin. Finally (today, 30/10/2026) I recieved a mail and put all my effort into it, researching on google and doing a lot of trials and errord.

I finaly did it with systemd service and it is still running. You can try it on https://discord.gg/6b2zBmuZMQ


# Running it yourself

You can do it, if you want, by cloning this repository, creating an .venv python environment, activating it, install the dependencies and finally, running bot.py (if you have put your own DISCORD_TOKEN in the .env file).


# What I learned

How to do a Discord bot and automate python programs.



# Ideas to develop this bot

* Add more commands
* Add a shop
* Add pet features
* ...
