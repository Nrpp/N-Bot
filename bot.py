import os
import random

from datetime import datetime, timedelta, timezone

import discord
from discord import app_commands
from discord.ext import commands, tasks
from dotenv import load_dotenv

import database

load_dotenv()

TOKEN = os.getenv("DISCORD_TOKEN")

if not TOKEN:
    raise RuntimeError("DISCORD_TOKEN is not configured in .env")

intents = discord.Intents.default()

bot = commands.Bot(
    command_prefix="!",
    intents=intents
)

@bot.event
async def on_ready():
    database.init_database()

    try:
        synced = await bot.tree.sync()
        print(f"Synchronized {len(synced)} commands.")
    except Exception as e:
        print(f"Error synchronizing commands: {e}")

    if not reminder_loop.is_running():
        reminder_loop.start()

    print("--------------------------------")
    print(f"Pulse is connected as {bot.user}")
    print(f"ID: {bot.user.id}")
    print("--------------------------------")


@bot.tree.command(
    name="help",
    description="Shows what Pulse can do."
)

async def help_command(interaction: discord.Interaction):
    embed = discord.Embed(
        title="Pulse",
        description=(
            "Your little center of utilities for Discord.\n\n"
            "Organize tasks, earn rewards, "
            "take care of the server pet and compete "
            "in the leaderboard."
        ),
        color=discord.Color.blurple()
    )

    embed.add_field(
        name="Organization",
        value=(
            "`/task add` - Add a task\n"
            "`/task list` - View your tasks\n"
            "`/task done` - Complete a task\n"
            "`/task delete` - Delete a task\n"
            "`/remind` - Create a reminder"
        ),
        inline=False
    )

    embed.add_field(
        name="Progress",
        value=(
            "`/profile` - See your profile\n"
            "`/daily` - Daily reward\n"
            "`/leaderboard` - Server ranking"
        ),
        inline=False
    )

    embed.add_field(
        name="Pet",
        value=(
            "`/pet` - See your pet\n"
            "`/feed` - Feed your pet\n"
            "`/play` - Play with your pet\n"
            "`/rest` - Let your pet rest"
        ),
        inline=False
    )

    embed.add_field(
        name="Fun",
        value=(
            "`/coinflip` - Flip a coin\n"
            "`/roll` - Roll a dice"
        ),
        inline=False
    )

    await interaction.response.send_message(
        embed=embed,
        ephemeral=True
    )

@bot.tree.command(
    name="profile",
    description="Show your Pulse profile."
)
async def profile(interaction: discord.Interaction):
    user = database.get_user(
        interaction.user.id,
        interaction.guild_id
    )

    required_xp = user["level"] * 100

    embed = discord.Embed(
        title=f"{interaction.user.display_name}'s Profile",
        color=discord.Color.blurple()
    )

    embed.add_field(
        name="Level",
        value=f"`{user['level']}`",
        inline=True
    )

    embed.add_field(
        name="XP",
        value=f"`{user['xp']} / {required_xp}`",
        inline=True
    )

    embed.add_field(
        name="Coins",
        value=f"`{user['coins']}`",
        inline=True
    )
    embed.add_field(
        name="Streak",
        value=f"`{user['streak']} days`",
        inline=True
    )

    await interaction.response.send_message(
        embed=embed
    )


@bot.tree.command(
    name="daily",
    description="Pick up your daily reward."
)

async def daily(interaction: discord.Interaction):
    user = database.get_user(
        interaction.user.id,
        interaction.guild_id
    )

    now = datetime.now(timezone.utc)

    streak = user["streak"]

    if user["last_daily"]:
        last = datetime.fromisoformat(user["last_daily"])
        elapsed = now - last
        if elapsed < timedelta(hours=24):
            remaining = timedelta(hours=24) - elapsed
            hours=int(remaining.total_seconds() // 3600)
            minutes = int((remaining.total_seconds() % 3600) // 60)

            await interaction.response.send_message(
                f"You have already claimed your reward.\n"
                f"Come back in **{hours}h {minutes}m**.",
                ephemeral=True
            )

            return

        if elapsed < timedelta(hours=48):
            streak += 1
        else:
            streak = 1

    else:
        streak = 1

    reward = random.randint(50, 100)

    database.add_coins(
        interaction.user.id,
        interaction.guild_id,
        reward
    )

    level, leveled_up = database.add_xp(
        interaction.user.id,
        interaction.guild_id,
        25
    )

    conn = database.get_connection()

    conn.execute(
        """
        UPDATE users
        SET last_daily = ?, streak = ?
        WHERE user_id = ? AND guild_id = ?
        """,
        (
            now.isoformat(),
            streak,
            interaction.user.id,
            interaction.guild_id
        )
    )

    conn.commit()
    conn.close()

    message = (
        f"**Daily reward!**\n\n"
        f"+{reward} coins\n"
        f"+25 XP\n\n"
        f"Streak: **{streak} days**\n\n"
        f"Come back tomorrow!"
    )

    if leveled_up:
        message += (
            f"\n\n**LEVEL UP!**\n"
            f"You are now level **{level}**!"
        )

    await interaction.response.send_message(
        message
    )


@bot.tree.command(
    name="leaderboard",
    description="Show the server ranking."
)
async def leaderboard(interaction: discord.Interaction):
    users = database.get_leaderboard(
        interaction.guild_id
    )

    if not users:
        await interaction.response.send_message(
            "There's no one in the ranking yet."
        )
        return
    lines = []
    medals = ["🥇","🥈","🥉"]
    for position, user in enumerate(users, start=1):
        member = interaction.guild.get_member(
            user["user_id"]
        )
        name = (
            member.display_name
            if member
            else f"User {user['user_id']}"
        )
        prefix = (
            medals[position - 1]
            if position <= 3
            else f"**{position}.**"
        )
        lines.append(
            f"{prefix} {name} - "
            f"Level {user['level']} · "
            f"{user['xp']} XP"
        )
    
    embed = discord.Embed(
        title = "Server Leaderboard",
        description = "\n".join(lines),
        color=discord.Color.gold()
    )

    await interaction.response.send_message(embed=embed)


task_group = app_commands.Group(
    name="task",
    description="Manage your tasks."
)

@task_group.command(
    name="add",
    description="Add a task."
)
@app_commands.describe(task="What you need to do")
async def task_add(
    interaction: discord.Interaction,
    task: str
):

    task_id = database.add_task(
        interaction.user.id,
        interaction.guild_id,
        task
    )

    await interaction.response.send_message(
        f"**Task added!**\n\n"
        f"**#{task_id}** - {task}"
    )

@task_group.command(
    name="list",
    description="Show your tasks."
)
async def task_list(interaction: discord.Interaction):
    user_tasks = database.get_tasks(
        interaction.user.id,
        interaction.guild_id
    )

    if not user_tasks:
        await interaction.response.send_message(
            "You don't have any tasks yet.\n\n"
            "Use `/task add` to create one."
        )
        return

    lines = []

    for task in user_tasks:
        icon = "✅" if task["completed"] else "⬜"
        lines.append(
            f"{icon} **#{task['id']}** -" 
            f"{task['task']}"
        )

    embed = discord.Embed(
        title="Your Tasks",
        description="\n".join(lines),
        color=discord.Color.blurple()
    )

    await interaction.response.send_message(embed=embed)

@task_group.command(
    name="done",
    description="Mark a task as completed."
)
@app_commands.describe(task_id="Task number")
async def task_done(
    interaction: discord.Interaction,
    task_id: int
):

    success = database.complete_task(
        task_id,
        interaction.user.id,
        interaction.guild_id
    )

    if not success:
        await interaction.response.send_message(
            "The task wasn't found or it was already completed.",
            ephemeral=True
        )
        return

    level, leveled_up = database.add_xp(
        interaction.user.id,
        interaction.guild_id,
        30
    )

    database.add_coins(
        interaction.user.id,
        interaction.guild_id,
        15
    )

    message = (
        "**Task completed!!**\n\n"
        "+30 XP\n"
        "+15 Coins"
    )

    if leveled_up:
        message += (
            f"\n\n **LEVEL UP!**\n"
            f"You're now level **{level}**!"
        )

    await interaction.response.send_message(message)

@task_group.command(
    name="delete",
    description="Delete a task."
)
@app_commands.describe(task_id="Number of task")
async def task_delete(
    interaction: discord.Interaction,
    task_id: int
):
    success = database.delete_task(
        task_id,
        interaction.user.id,
        interaction.guild_id
    )

    if success:
        await interaction.response.send_message(
            "Task deleted."
        )
    else:
        await interaction.response.send_message(
            "Task not found.",
            ephemeral=True
        )

bot.tree.add_command(task_group)

@bot.tree.command(
    name="remind",
    description="Create a reminder."
)
@app_commands.describe(
    minutes="How many minutes from now",
    message="What do you want to be reminded about?"
)
async def remind(
    interaction: discord.Interaction,
    minutes: int,
    message: str
):
    if minutes < 1 or minutes > 10080:
        await interaction.response.send_message(
            "The time must be between "
            "1 minute and 7 days.",
            ephemeral=True
        )
        return
    remind_at = (
        datetime.now(timezone.utc)
        + timedelta(minutes=minutes)
    )

    conn = database.get_connection()

    conn.execute(
        """
        INSERT INTO reminders
        (user_id, guild_id, channel_id, message, remind_at)
        VALUES (?, ?, ?, ?, ?)
        """,
        (
            interaction.user.id,
            interaction.guild_id,
            interaction.channel_id,
            message,
            remind_at.isoformat()
        )
    )

    conn.commit()
    conn.close()

    await interaction.response.send_message(
        f"**Reminder created!**\n\n"
        f"I'll remind you about **{message}** "
        f"in **{minutes} minutes**."
    )

@tasks.loop(seconds=30)
async def reminder_loop():
    now = datetime.now(timezone.utc)
    conn = database.get_connection()
    reminders = conn.execute(
        """
        SELECT *
        FROM reminders
        WHERE remind_at <= ?
        """,
        (now.isoformat(),)
    ).fetchall()

    for reminder in reminders:
        channel = bot.get_channel(
            reminder["channel_id"]
        )

        if channel:
            try:
                user = await bot.fetch_user(
                    reminder["user_id"]
                )

                await channel.send(
                    f"{user.mention} **Reminder**\n\n"
                    f"{reminder['message']}"
                )

            except Exception as e:
                print(
                    f"Error sending reminder: {e}"
                )

            conn.execute(
                "DELETE FROM reminders WHERE id = ?",
                (reminder["id"],)
            )

    conn.commit()
    conn.close()

@reminder_loop.before_loop
async def before_reminder_loop():
    await bot.wait_until_ready()

@bot.tree.command(
    name="pet",
    description="Show the pet of the server."
)
async def pet(interaction: discord.Interaction):
    server_pet = database.get_pet(
        interaction.guild_id
    )

    average = (
        server_pet["hunger"]
        + server_pet["happiness"]
        + server_pet["energy"]
    ) / 3

    if average < 30:
        mood = ":("
    elif average < 60:
        mood = ":|"
    elif average > 90:
        mood = "🤩"
    else:
        mood = ":)"

    embed = discord.Embed(
        title=f"{server_pet['name']} {mood}",
        description="The pet of the entire server.",
        color=discord.Color.green()
    )

    embed.add_field(
        name="Hunger",
        value=f"`{server_pet['hunger']}/100`",
        inline=True
    )

    embed.add_field(
        name="Happiness",
        value=f"`{server_pet['happiness']}/100`",
        inline=True
    )

    embed.add_field(
        name="Energy",
        value=f"`{server_pet['energy']}/100`",
        inline=True
    )

    await interaction.response.send_message(
        embed=embed
    )

@bot.tree.command(
    name="feed",
    description="Feed the server pet."
)
async def feed(interaction: discord.Interaction):
    server_pet = database.update_pet(
        interaction.guild_id,
        hunger=20,
        happiness=5
    )

    database.add_xp(
        interaction.user.id,
        interaction.guild_id,
        10
    )

    await interaction.response.send_message(
        f"**{server_pet['name']} has eaten!**\n\n"
        f"Hunger: `{server_pet['hunger']}/100`\n"
        f"Happiness: `{server_pet['happiness']}/100`\n\n"
        f"+10 XP"
    )

@bot.tree.command(
    name="play",
    description="Play with the server pet."
)
async def play(interaction: discord.Interaction):
    server_pet = database.update_pet(
        interaction.guild_id,
        happiness=20,
        energy=-10
    )

    database.add_xp(
        interaction.user.id,
        interaction.guild_id,
        15
    )

    await interaction.response.send_message(
        f"**You've played with {server_pet['name']}!**\n\n"
        f"Happiness: `{server_pet['happiness']}/100`\n"
        f"Energy: `{server_pet['energy']}/100`\n\n"
        f"+15 XP"
    )

@bot.tree.command(
    name="rest",
    description="Let the pet rest."
)
async def rest(interaction: discord.Interaction):
    server_pet = database.update_pet(
        interaction.guild_id,
        energy=25,
        hunger=-5
    )

    await interaction.response.send_message(
        f"**{server_pet['name']} is resting.**\n\n"
        f"Energy: `{server_pet['energy']}/100`\n"
        f"Hunger: `{server_pet['hunger']}/100`"
    )


@bot.tree.command(
    name="coinflip",
    description="Flip a coin."
)
async def coinflip(interaction: discord.Interaction):
    result = random.choice(
        ["Heads", "Tails"]
    )

    await interaction.response.send_message(
        f"**{result}!**"
    )

@bot.tree.command(
    name="roll",
    description="Roll a dice."
)
@app_commands.describe(
    sides="Number of sides of the dice"
)
async def roll(
    interaction: discord.Interaction,
    sides: int = 6
):
    if sides < 2 or sides > 1000:
        await interaction.response.send_message(
            "The dice needs to have between "
            "2 and 1000 sides.",
            ephemeral=True
        )

        return
    result = random.randint(1, sides)

    await interaction.response.send_message(
        f"You rolled a **{result}** "
        f"on a {sides}-sided dice!"
    )



@bot.tree.error
async def on_app_command_error(
    interaction: discord.Interaction,
    error: app_commands.AppCommandError
):
    print(f"Command error: {error}")

    if interaction.response.is_done():
        await interaction.followup.send(
            "There's been an unexpected error. "
            "Check the bot console for details.",
            ephemeral=True
        )
    else:
        await interaction.response.send_message(
            "There's been an unexpected error. "
            "Check the bot console for details.",
            ephemeral=True
        )

database.init_database()

bot.run(TOKEN)