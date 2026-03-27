import discord
from discord import app_commands
from discord.ext import commands, tasks
from datetime import datetime, timedelta, timezone
import os
import json
from dotenv import load_dotenv
from zoneinfo import ZoneInfo

load_dotenv()
TOKEN = os.getenv("DISCORD_TOKEN")

intents = discord.Intents.default()
intents.message_content = True

# Fichiers de sauvegarde JSON
GUILD_NAMES_FILE = "guild_names.json"
GUILD_TIMEZONES_FILE = "guild_timezones.json"
GUILD_LANGS_FILE = "guild_langs.json"
VOTES_FILE = "votes.json"

def load_json_file(path):
    try:
        with open(path, "r") as f:
            return json.load(f)
    except FileNotFoundError:
        return {}

def save_json_file(path, data):
    with open(path, "w") as f:
        json.dump(data, f, indent=4)

def load_votes():
    return load_json_file(VOTES_FILE)

def save_votes(data):
    save_json_file(VOTES_FILE, data)

LANG_STRINGS = {
    "set_timezone_prompt": {
        "ENG": "Choose the server's timezone:",
        "FR": "Choisis le fuseau horaire du serveur :"
    },
    "timezone_set": {
        "ENG": "🕒 Timezone set to UTC{sign}{offset}",
        "FR": "🕒 Fuseau horaire configuré sur UTC{sign}{offset}"
    },
    "poll_announcement": {
        "ENG": "@here 📣 **GvG League poll for {guild_name} !**",
        "FR": "@here 📣 **Sondage GvG League pour {guild_name} !**"
    },
    "poll_description": {
        "ENG": "🗳️ React with the times you are available for GvG:\n\n",
        "FR": "🗳️ Réagis à l'heure où tu es dispo pour la GvG :\n\n"
    },
    "timezone_field": {
        "ENG": "🕒 Timezone",
        "FR": "🕒 Fuseau horaire"
    },
    "footer_text": {
        "ENG": "{guild_name} • GvG on demand ⚔️",
        "FR": "{guild_name} • GvG à la demande ⚔️"
    },
    "guild_set": {
        "ENG": "✅ Guild name set to: **{guild_name}**",
        "FR": "✅ Nom de guilde défini : **{guild_name}**"
    },
    "lang_set": {
        "ENG": "✅ Language set to English (ENG)",
        "FR": "✅ Langue définie sur Français (FR)"
    },
    "lang_help": {
        "ENG": "📖 Help - GvG League Bot\nAvailable commands:",
        "FR": "📖 Aide - Bot GvG League\nCommandes disponibles :"
    },
    "help_commands": {
        "ENG": {
            "/setguild <name>": "Set the guild name (admin)",
            "/settimezone": "Set the server timezone (admin)",
            "/startpoll": "Start a poll adapted to day and timezone (admin)",
            "/setlanguage <ENG/FR>": "Change the bot language (admin)",
            "/help": "Show this help message"
        },
        "FR": {
            "/setguild <nom>": "Définit le nom de la guilde (admin)",
            "/settimezone": "Configure le fuseau horaire du serveur (admin)",
            "/startpoll": "Lance un sondage adapté au jour et fuseau (admin)",
            "/setlanguage <ENG/FR>": "Change la langue du bot (admin)",
            "/help": "Affiche ce message"
        }
    },
    "language_invalid": {
        "ENG": "❌ Invalid language! Choose ENG or FR.",
        "FR": "❌ Langue invalide ! Choisis ENG ou FR."
    }
}

class MyBot(commands.Bot):
    def __init__(self):
        super().__init__(command_prefix="!", intents=intents)
        self.guild_names = load_json_file(GUILD_NAMES_FILE)
        self.timezones = load_json_file(GUILD_TIMEZONES_FILE)
        self.langs = load_json_file(GUILD_LANGS_FILE)

    async def setup_hook(self):
        await self.tree.sync()

bot = MyBot()

base_week_slots = [
    "17:00", "17:30", "18:00", "18:30", "19:00", "19:30",
    "20:00", "20:30", "21:00", "21:30", "22:00", "22:30",
    "23:00", "23:30", "00:00", "00:30", "01:00"
]

base_weekend_slots = [
    "13:00", "13:30", "14:00", "14:30", "15:00", "15:30",
    "16:00", "16:30", "17:00", "17:30", "18:00", "18:30",
    "19:00", "19:30", "20:00", "20:30", "21:00", "21:30",
    "22:00", "22:30"
]

EMOJIS = [
    "🇦", "🇧", "🇨", "🇩", "🇪", "🇫", "🇬", "🇭", "🇮", "🇯",
    "🇰", "🇱", "🇲", "🇳", "🇴", "🇵", "🇶", "🇷", "🇸", "🇹"
]

TIMEZONE_OPTIONS = [
    discord.SelectOption(label="UTC+1 West Africa (Bénin, Lagos)", value="Africa/Lagos"),
    discord.SelectOption(label="UTC+2 Central Africa (Cairo)", value="Africa/Cairo"),
    discord.SelectOption(label="UTC+3 East Africa (Nairobi)", value="Africa/Nairobi"),
    discord.SelectOption(label="UTC+3 Madagascar (Antananarivo)", value="Indian/Antananarivo"),
    discord.SelectOption(label="UTC+4 Réunion", value="Indian/Reunion"),
    discord.SelectOption(label="UTC+0 London", value="Europe/London"),
    discord.SelectOption(label="UTC+1 Paris, Berlin", value="Europe/Paris"),
    discord.SelectOption(label="UTC+2 Athens", value="Europe/Athens"),
    discord.SelectOption(label="UTC-8 Pacific (Los Angeles)", value="America/Los_Angeles"),
    discord.SelectOption(label="UTC-7 Mountain (Denver)", value="America/Denver"),
    discord.SelectOption(label="UTC-6 Central (Chicago)", value="America/Chicago"),
    discord.SelectOption(label="UTC-5 Eastern (New York)", value="America/New_York"),
]

@bot.event
async def on_ready():
    print(f"✅ Bot connected as {bot.user}")
    check_vote_reminders.start()

@bot.tree.command(name="settimezone", description="Set the server timezone (admin only)")
@app_commands.checks.has_permissions(administrator=True)
async def settimezone(interaction: discord.Interaction):
    guild_id = str(interaction.guild.id)
    lang = bot.langs.get(guild_id, "ENG")

    options = TIMEZONE_OPTIONS
    placeholder = "Choose timezone (Africa / EU / NA)" if lang == "ENG" else "Choisis le fuseau horaire (Afrique / EU / NA)"
    view = discord.ui.View()
    select = discord.ui.Select(placeholder=placeholder, max_values=1, min_values=1, options=options)

    async def select_callback(interaction_select: discord.Interaction):
        tz_name = select.values[0]
        bot.timezones[guild_id] = tz_name
        save_json_file(GUILD_TIMEZONES_FILE, bot.timezones)
        tzinfo = ZoneInfo(tz_name)
        now = datetime.now(tz=tzinfo)
        utc_offset_hours = now.utcoffset().total_seconds() / 3600
        sign = "+" if utc_offset_hours >= 0 else ""
        msg = LANG_STRINGS["timezone_set"][lang].format(sign=sign, offset=int(utc_offset_hours))
        await interaction_select.response.send_message(msg, ephemeral=True)
        view.stop()

    select.callback = select_callback
    view.add_item(select)
    prompt = LANG_STRINGS["set_timezone_prompt"][lang]
    await interaction.response.send_message(prompt, view=view, ephemeral=True)

@bot.tree.command(name="setguild", description="Set the guild name (admin only)")
@app_commands.describe(guild_name="Guild name")
@app_commands.checks.has_permissions(administrator=True)
async def setguild(interaction: discord.Interaction, guild_name: str):
    guild_id = str(interaction.guild.id)
    bot.guild_names[guild_id] = guild_name
    save_json_file(GUILD_NAMES_FILE, bot.guild_names)
    lang = bot.langs.get(guild_id, "ENG")
    msg = LANG_STRINGS["guild_set"][lang].format(guild_name=guild_name)
    await interaction.response.send_message(msg)

@bot.tree.command(name="startpoll", description="Start a GvG League poll (admin only)")
@app_commands.checks.has_permissions(administrator=True)
async def startpoll(interaction: discord.Interaction):
    guild_id = str(interaction.guild.id)
    lang = bot.langs.get(guild_id, "ENG")
    guild_name = bot.guild_names.get(guild_id, "your guild" if lang == "ENG" else "votre guilde")
    tz_name = bot.timezones.get(guild_id, "UTC")
    guild_tz = ZoneInfo(tz_name)

    now = datetime.now(tz=guild_tz)
    weekday = now.weekday()
    date_sondage = now.strftime("%d/%m/%Y")

    slots = base_weekend_slots if weekday >= 5 else base_week_slots

    description = LANG_STRINGS["poll_description"][lang]

    for emoji, time_str in zip(EMOJIS, slots):
        h, m = map(int, time_str.split(":"))
        local_dt = datetime(now.year, now.month, now.day, h, m, tzinfo=guild_tz)
        dt_utc = local_dt.astimezone(ZoneInfo("UTC"))
        unix_ts = int(dt_utc.timestamp())
        description += f"{emoji} → <t:{unix_ts}:t>\n"

    embed = discord.Embed(
        title=f"📊 GvG League Poll - {guild_name} - {date_sondage}" if lang == "ENG" else f"📊 Sondage GvG League - {guild_name} - {date_sondage}",
        description=description,
        color=discord.Color.orange(),
        timestamp=now
    )
    embed.add_field(
        name=LANG_STRINGS["timezone_field"][lang],
        value=f"Times shown in server timezone {tz_name} (UTC{'+' if now.utcoffset().total_seconds() >= 0 else ''}{int(now.utcoffset().total_seconds()/3600)})",
        inline=False
    )
    embed.set_footer(text=LANG_STRINGS["footer_text"][lang].format(guild_name=guild_name))

    msg = await interaction.channel.send(embed=embed)

    for i, emoji in enumerate(EMOJIS):
        if i >= len(slots):
            break
        await msg.add_reaction(emoji)

    # --- Enregistrement du sondage pour suivi des votes et rappels ---
    votes = load_votes()
    votes[str(msg.id)] = {
        "guild_id": guild_id,
        "timezone": tz_name,
        "timestamp": now.isoformat(),
        "slots": slots,
        "votes": {}
    }
    save_votes(votes)

@bot.tree.command(name="setlanguage", description="Change bot language ENG/FR (admin only)")
@app_commands.describe(language="Choose ENG or FR")
@app_commands.checks.has_permissions(administrator=True)
async def setlanguage(interaction: discord.Interaction, language: str):
    lang_choice = language.upper()
    guild_id = str(interaction.guild.id)
    if lang_choice not in ("ENG", "FR"):
        guild_lang = bot.langs.get(guild_id, "ENG")
        await interaction.response.send_message(LANG_STRINGS["language_invalid"][guild_lang], ephemeral=True)
        return
    bot.langs[guild_id] = lang_choice
    save_json_file(GUILD_LANGS_FILE, bot.langs)
    await interaction.response.send_message(LANG_STRINGS["lang_set"][lang_choice], ephemeral=True)

@bot.tree.command(name="help", description="Show help message")
async def help(interaction: discord.Interaction):
    guild_id = str(interaction.guild.id)
    lang = bot.langs.get(guild_id, "ENG")
    embed = discord.Embed(
        title=LANG_STRINGS["lang_help"][lang],
        description="",
        color=discord.Color.blue()
    )
    for cmd, desc in LANG_STRINGS["help_commands"][lang].items():
        embed.add_field(name=cmd, value=desc, inline=False)
    footer_text = "GvG League Bot • Simplified organization ⚔️" if lang == "ENG" else "Bot GvG League • Organisation simplifiée ⚔️"
    embed.set_footer(text=footer_text)
    embed.timestamp = datetime.now()
    await interaction.response.send_message(embed=embed)

# --- Ajout pour gestion des votes en DM + rappel 5 min avant ---

@bot.event
async def on_raw_reaction_add(payload: discord.RawReactionActionEvent):
    # Ignore les réactions du bot lui-même
    if payload.user_id == bot.user.id:
        return

    votes_data = load_votes()
    message_id = str(payload.message_id)
    user_id = str(payload.user_id)
    emoji = str(payload.emoji)

    if message_id not in votes_data:
        return

    poll = votes_data[message_id]

    if emoji not in EMOJIS:
        return

    index = EMOJIS.index(emoji)
    if index >= len(poll["slots"]):
        return

    voted_time = poll["slots"][index]

    if "votes" not in poll:
        poll["votes"] = {}

    poll["votes"][user_id] = {"time": voted_time, "notified": False}

    save_votes(votes_data)

    # Envoi DM confirmation
    try:
        user = await bot.fetch_user(payload.user_id)
        guild_id = str(payload.guild_id)
        lang = bot.langs.get(guild_id, "ENG")
        msg = {
            "ENG": f"✅ Your vote for {voted_time} has been recorded. You'll be reminded 5 minutes before the event.",
            "FR": f"✅ Ton vote pour {voted_time} a été pris en compte. Tu seras prévenu 5 minutes avant l'événement."
        }
        await user.send(msg[lang])
    except discord.Forbidden:
        pass

@tasks.loop(minutes=5)
async def check_vote_reminders():
    now_utc = datetime.now(timezone.utc)
    votes_data = load_votes()
    updated = False

    for message_id, poll in votes_data.items():
        tz_name = poll.get("timezone")
        if not tz_name:
            continue
        tz = ZoneInfo(tz_name)

        poll_time_str = poll.get("timestamp")
        if not poll_time_str:
            continue
        poll_time = datetime.fromisoformat(poll_time_str).astimezone(tz)

        votes = poll.get("votes", {})
        for user_id, vote_info in votes.items():
            if vote_info.get("notified"):
                continue

            vote_time_str = vote_info.get("time")
            if not vote_time_str:
                continue

            h, m = map(int, vote_time_str.split(":"))
            event_dt = poll_time.replace(hour=h, minute=m, second=0, microsecond=0)

            reminder_dt = event_dt - timedelta(minutes=5)
            if now_utc >= reminder_dt.astimezone(timezone.utc):
                try:
                    user = await bot.fetch_user(int(user_id))
                    guild_id = poll.get("guild_id", "")
                    lang = bot.langs.get(str(guild_id), "ENG")
                    reminder_msg = {
                        "ENG": f"⚔️ Reminder! Your GvG event is scheduled for {vote_time_str} (server time). Get ready!",
                        "FR": f"⚔️ Rappel ! Ton event GvG est prévu à {vote_time_str} (heure du serveur). Prépare-toi !"
                    }
                    await user.send(reminder_msg[lang])
                    vote_info["notified"] = True
                    updated = True
                except (discord.Forbidden, discord.NotFound):
                    pass

    if updated:
        save_votes(votes_data)

bot.run(TOKEN)
