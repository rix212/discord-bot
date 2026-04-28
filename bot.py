import os
import re
import json
import threading
from datetime import timedelta, datetime
from collections import defaultdict

import discord
from discord.ext import commands
from flask import Flask, jsonify, send_from_directory
from flask_cors import CORS

# ─── CONFIG ───────────────────────────────────────────────────────────────────
TOKEN = os.getenv("DISCORD_TOKEN", "")

SERVER_NAME = "Ambitious Notifier"

# ── BOT SETTINGS (editable via dashboard) ─────────────────────────────────────
BOT_SETTINGS = {
    "autoreply": "67",
    "status": "67 67 67 67",
}
BLACKLIST_ROLE_ID = 1494380951567073451

# ── IMMUNE USER — completely exempt from ALL checks including GIFs ────────────
IMMUNE_USER_IDS = {1482300597935013968, 1436220760304652338}

# ── WHITELISTED USERS — can use BLOCKED_WORDS freely (all other checks still apply) ──
WHITELISTED_USER_IDS: set = set()

CONFIG = {
    "exempt_roles": [],
    "exempt_users": [],
    "log_channel_id": 1493335195535937738,
}

# ─── PUNISHMENTS (used for links AND gifs) ────────────────────────────────────
PUNISHMENTS = [
    {"label": "1 minute timeout",   "timeout_minutes": 1},
    {"label": "10 minute timeout",  "timeout_minutes": 10},
    {"label": "1 hour timeout",     "timeout_minutes": 60},
    {"label": "Kicked from server", "timeout_minutes": None},
]

# ─── ALLOWED URLS ─────────────────────────────────────────────────────────────
ALLOWED_URLS = [
    "ambitious-joiner.com/dashboard",
    "cdn.discordapp.com",
    "media.discordapp.net",
]

# ─── BLOCKED SYMBOLS ──────────────────────────────────────────────────────────
BLOCKED_SYMBOLS = set(
    "#%^&*()_+-=[]{}|;'\",<>?`~!§\\"
    "∞≈≠≤≥±÷×√∑∏∫∆"
    "→←↑↓↔↕⇄⇅⇆"
    "■□▪▫▲△▶▷▼▽"
    "\u00ab\u00bb\u2039\u203a"
    "\u201e\u201c\u201d\u201a\u2018\u2019"
    "※‼⁂⁎⁑"
)

# ─── BLOCKED PHRASES ──────────────────────────────────────────────────────────
BLOCKED_PHRASES = [
    "join my discord", "check my bio for discord", "discord in bio",
    "join discord in bio", "my discord is in bio", "look in bio for discord",
    "bio has my discord", "discord link in bio", "find my discord in bio",
    "go to bio for discord", "bio for discord", "join my server",
    "join my server in bio", "server link in bio", "community in bio",
    "join our community", "be part of the server", "join the community",
    "join the community in bio", "click bio for discord", "tap bio for discord",
    "open bio for discord", "visit bio for discord", "bio link join now",
    "dont miss out join discord", "join now discord in bio",
    "best community join now", "active server in bio", "growing community join",
    "exclusive server in bio", "private server join now",
    "only few spots join discord", "limited access join now",
    "talk with us in discord", "chat in my discord", "hang out in discord",
    "play together join discord", "updates in discord", "news in discord",
    "join events in discord", "giveaways in discord", "rewards in discord",
    "best free script in bio", "free script in my bio", "you want free script",
    "look in my bio",
    # DM bait — send/slide
    "dm me", "send me a dm", "slide into my dm", "slide in my dm",
    "dm for info", "dm for more", "dm me for", "dm us",
    "dm for access", "dm to join", "dm me to join", "dm for invite",
    "dm for link", "dm for discord", "dm for server", "dm for script",
    "dm for free", "dm for details", "dm me for info", "dm me for link",
    "dm me for access", "dm me for discord",
    "hmu", "hit me up", "message me", "msg me",
    # "check DMs / DM" variants — catches all capitalizations via lower() comparison
    "check dms", "check dm", "check your dms", "check your dm",
    "check ur dms", "check ur dm", "check the dms", "check the dm",
    "i dmed you", "i dm'd you", "i sent a dm", "sent you a dm",
    "sent a dm", "dmed you", "dm'd you",
    "look at your dms", "look at ur dms",
    "look in your dms", "look in ur dms",
    "replied in dms", "answer my dm", "answer the dm",
    "respond to my dm", "respond to the dm",
    "open your dms", "open ur dms", "open dms",
    "dms open", "my dms are open", "dms are open",
    "sliding into dms", "slide into dms", "slid into dms",
    "in your dms", "in ur dms", "in the dms",
    "via dm", "via dms", "through dm", "through dms",
    "link in dms", "sent in dms", "info in dms",
    "details in dms", "discord in dms",
]

# ─── BLOCKED WORDS ────────────────────────────────────────────────────────────
BLOCKED_WORDS = [
    "nigger", "niggers", "nigga", "niggas", "niggah", "niggaz",
    "chink", "chinks", "gook", "gooks", "spic", "spics", "spick",
    "kike", "kikes", "wetback", "wetbacks", "beaner", "beaners",
    "coon", "coons", "jigaboo", "jiggaboo", "sambo", "sambos",
    "towelhead", "towelheads", "raghead", "ragheads", "sandnigger",
    "zipperhead", "zipperheads", "cracker", "crackers", "honky", "honkies",
    "redneck", "rednecks", "whitey", "whiteboy",
    "faggot", "faggots", "fag", "fags", "dyke", "dykes",
    "tranny", "trannies", "shemale", "shemales",
    "retard", "retards", "retarded", "spastic", "spaz",
    "fuck", "fucker", "fuckers", "fucking", "fucked", "fucks",
    "motherfucker", "motherfuckers", "motherfucking",
    "shit", "shits", "shitty", "bullshit",
    "asshole", "assholes",
    "bitch", "bitches", "bitching",
    "cunt", "cunts",
    "cock", "cocks", "cocksucker", "cocksuckers",
    "dick", "dicks", "dickhead", "dickheads",
    "pussy", "pussies",
    "bastard", "bastards",
    "whore", "whores",
    "slut", "sluts",
    "twat", "twats",
    "wanker", "wankers",
    "prick", "pricks",
    "douche", "douchebag", "douchebags",
    "jackass", "jackasses",
    "dumbass", "dumbasses",
    "dipshit", "dipshits",
    "shithead", "shitheads",
    "arsehole", "arseholes",
    "bollocks", "tosser", "tossers", "bellend", "bellends",
    "knobhead", "knobheads",
    "porn", "porno", "pornography", "hentai",
    "blowjob", "blowjobs", "handjob", "handjobs",
    "cumshot", "cumshots", "gangbang", "gangbangs",
    "milf", "dildo", "dildos",
    "dm", "dms",
    "kys", "kms", "kill yourself", "hang yourself",
    "rope yourself", "slit your wrists",
    "cocaine", "heroin", "meth", "methamphetamine",
    "ecstasy", "mdma", "lsd", "fentanyl",
    "scheiße", "scheisse", "arschloch", "arschlöcher",
    "wichser", "hurensohn", "hurensöhne", "fotze", "fotzen",
    "ficken", "schwuchtel", "schwuchteln", "spast", "spasti",
    "vollidiot", "vollidioten", "drecksau", "drecksäue",
    "schlampe", "schlampen",
]

# ─── GIF DETECTION ────────────────────────────────────────────────────────────
GIF_URL_PATTERN = re.compile(
    r"(https?://)?(tenor\.com|giphy\.com|media\.tenor\.com|media\.giphy\.com|i\.giphy\.com|[^\s]+\.gif)",
    re.IGNORECASE,
)
INVITE_PATTERN = re.compile(
    r"discord(?:app)?\.(?:com/invite|gg)/([a-zA-Z0-9\-]+)",
    re.IGNORECASE,
)
URL_PATTERN = re.compile(
    r"(https?://[^\s]+|www\.[^\s]+|[^\s]+\.(?:com|net|org|gg|io|co|xyz|me|tv|live|app|dev|link|site|club|shop|info|biz|eu|de|fr|uk|ru|jp|cn)[^\s]*)",
    re.IGNORECASE,
)

warnings = defaultdict(int)
gif_warnings = defaultdict(int)
repeat_tracker: dict = {}

# ─── PERSISTENT STORAGE ───────────────────────────────────────────────────────
DATA_FILE = "bot_data.json"
_save_lock = threading.Lock()

def load_data():
    """Load saved logs, user_stats and warning counters from disk on startup."""
    global dashboard_logs, user_stats
    if not os.path.exists(DATA_FILE):
        return
    try:
        with open(DATA_FILE, "r", encoding="utf-8") as f:
            data = json.load(f)
        dashboard_logs = data.get("logs", [])
        user_stats     = data.get("users", {})
        for uid in data.get("whitelist", []):
            WHITELISTED_USER_IDS.add(int(uid))
        for uid, stats in user_stats.items():
            warnings[int(uid)]     = stats.get("warnings", 0)
            gif_warnings[int(uid)] = stats.get("gif_warnings", 0)
        # Restore any custom words/phrases added via dashboard
        for w in data.get("custom_words", []):
            if w not in BLOCKED_WORDS:
                BLOCKED_WORDS.append(w)
        for p in data.get("custom_phrases", []):
            if p not in BLOCKED_PHRASES:
                BLOCKED_PHRASES.append(p)
        saved_settings = data.get("bot_settings", {})
        BOT_SETTINGS.update(saved_settings)
        print(f"✅ Loaded {len(dashboard_logs)} logs, {len(user_stats)} users, {len(WHITELISTED_USER_IDS)} whitelisted from disk.")
    except Exception as e:
        print(f"⚠️ Could not load {DATA_FILE}: {e}")

def save_data():
    """Write all data to disk atomically."""
    with _save_lock:
        try:
            # Save only words/phrases that were added at runtime (not hardcoded)
            snapshot = {
                "logs":           dashboard_logs,
                "whitelist":      list(WHITELISTED_USER_IDS),
                "custom_words":   BLOCKED_WORDS[:],
                "custom_phrases": BLOCKED_PHRASES[:],
                "bot_settings":   BOT_SETTINGS.copy(),
                "users": {
                    uid: {**u, "gif_warnings": gif_warnings.get(int(uid), 0)}
                    for uid, u in user_stats.items()
                },
            }
            tmp = DATA_FILE + ".tmp"
            with open(tmp, "w", encoding="utf-8") as f:
                json.dump(snapshot, f, ensure_ascii=False, indent=2)
            os.replace(tmp, DATA_FILE)
        except Exception as e:
            print(f"⚠️ Save failed: {e}")

# ─── DASHBOARD DATA STORE ─────────────────────────────────────────────────────
dashboard_logs = []   # list of log dicts (max 500)
user_stats     = {}   # { user_id: { name, warnings, timeouts, kicks, infractions, gif_warnings } }

def add_log(action: str, user_name: str, user_id: int, channel: str, detail: str, punishment: str = ""):
    entry = {
        "timestamp": datetime.utcnow().isoformat(),
        "action":    action,
        "user":      user_name,
        "user_id":   str(user_id),
        "channel":   channel,
        "detail":    detail[:200],
        "punishment": punishment,
    }
    dashboard_logs.insert(0, entry)
    if len(dashboard_logs) > 500:
        dashboard_logs.pop()
    save_data()

def update_user_stats(member: discord.Member, infraction_type: str, punishment: str = ""):
    uid = str(member.id)
    if uid not in user_stats:
        user_stats[uid] = {
            "name":        str(member),
            "avatar":      str(member.display_avatar.url) if member.display_avatar else "",
            "warnings":    0,
            "timeouts":    0,
            "kicks":       0,
            "gif_warnings": 0,
            "infractions": [],
        }
    s = user_stats[uid]
    s["name"] = str(member)
    s["infractions"].insert(0, {
        "type":       infraction_type,
        "punishment": punishment,
        "time":       datetime.utcnow().isoformat(),
    })
    if len(s["infractions"]) > 50:
        s["infractions"].pop()
    if "timeout" in punishment.lower():
        s["timeouts"] += 1
        s["warnings"] += 1
    elif "kick" in punishment.lower():
        s["kicks"] += 1
        s["warnings"] += 1
    elif punishment == "":
        s["warnings"] += 1
    save_data()

# ─── FLASK DASHBOARD ──────────────────────────────────────────────────────────
app = Flask(__name__, static_folder="dashboard")
CORS(app, resources={r"/api/*": {"origins": "*"}})

@app.route("/api/logs")
def get_logs():
    return jsonify(dashboard_logs)

@app.route("/api/users")
def get_users():
    return jsonify(user_stats)

@app.route("/api/stats")
def get_stats():
    total_warnings = sum(u["warnings"] for u in user_stats.values())
    total_timeouts = sum(u["timeouts"] for u in user_stats.values())
    total_kicks = sum(u["kicks"] for u in user_stats.values())
    return jsonify({
        "total_logs": len(dashboard_logs),
        "total_warnings": total_warnings,
        "total_timeouts": total_timeouts,
        "total_kicks": total_kicks,
        "total_users": len(user_stats),
    })

@app.route("/api/channels")
def get_channels():
    """Return all text channels the bot can see, grouped by guild."""
    result = []
    for guild in bot.guilds:
        channels = []
        for ch in guild.text_channels:
            perms = ch.permissions_for(guild.me)
            if perms.send_messages:
                channels.append({"id": str(ch.id), "name": ch.name, "category": ch.category.name if ch.category else ""})
        result.append({"guild": guild.name, "guild_id": str(guild.id), "channels": channels})
    return jsonify(result)

@app.route("/api/send", methods=["POST"])
def send_message():
    """Send a message as the bot to a channel."""
    from flask import request as freq
    data = freq.get_json(force=True)
    channel_id = data.get("channel_id")
    text = data.get("message", "").strip()
    if not channel_id or not text:
        return jsonify({"ok": False, "error": "Missing channel_id or message"}), 400
    if len(text) > 2000:
        return jsonify({"ok": False, "error": "Message exceeds 2000 characters"}), 400
    channel = bot.get_channel(int(channel_id))
    if not channel:
        return jsonify({"ok": False, "error": "Channel not found"}), 404
    # Schedule coroutine from sync Flask thread
    import asyncio
    future = asyncio.run_coroutine_threadsafe(channel.send(text), bot.loop)
    try:
        future.result(timeout=10)
        add_log("💬 Dashboard Message", "Dashboard", 0, channel.name, text[:200])
        return jsonify({"ok": True})
    except Exception as e:
        return jsonify({"ok": False, "error": str(e)}), 500

@app.route("/api/settings", methods=["GET"])
def get_settings():
    return jsonify(BOT_SETTINGS)

@app.route("/api/settings", methods=["POST"])
def update_settings():
    from flask import request as freq
    import asyncio
    data = freq.get_json(force=True)
    changed = False
    if "autoreply" in data:
        val = str(data["autoreply"]).strip()
        if val:
            BOT_SETTINGS["autoreply"] = val
            changed = True
    if "status" in data:
        val = str(data["status"]).strip()
        if val:
            BOT_SETTINGS["status"] = val
            # Update bot presence live
            async def update_presence():
                await bot.change_presence(activity=discord.Game(name=val))
            asyncio.run_coroutine_threadsafe(update_presence(), bot.loop)
            changed = True
    if changed:
        save_data()
        return jsonify({"ok": True})
    return jsonify({"ok": False, "error": "No valid fields provided"}), 400

@app.route("/api/blacklist", methods=["GET"])
def get_blacklist():
    return jsonify({"words": BLOCKED_WORDS, "phrases": BLOCKED_PHRASES})

@app.route("/api/blacklist/add", methods=["POST"])
def blacklist_add():
    from flask import request as freq
    data  = freq.get_json(force=True)
    kind  = data.get("kind")
    value = data.get("value", "").strip().lower()
    if not value:
        return jsonify({"ok": False, "error": "Empty value"}), 400
    if kind == "word":
        if value in BLOCKED_WORDS:
            return jsonify({"ok": False, "error": "Already in word list"}), 400
        BLOCKED_WORDS.append(value)
        add_log("➕ Blacklist Word Added", "Dashboard", 0, "–", value)
    elif kind == "phrase":
        if value in BLOCKED_PHRASES:
            return jsonify({"ok": False, "error": "Already in phrase list"}), 400
        BLOCKED_PHRASES.append(value)
        add_log("➕ Blacklist Phrase Added", "Dashboard", 0, "–", value)
    else:
        return jsonify({"ok": False, "error": "kind must be word or phrase"}), 400
    save_data()
    return jsonify({"ok": True})

@app.route("/api/blacklist/remove", methods=["POST"])
def blacklist_remove():
    from flask import request as freq
    data  = freq.get_json(force=True)
    kind  = data.get("kind")
    value = data.get("value", "").strip().lower()
    if kind == "word":
        if value not in BLOCKED_WORDS:
            return jsonify({"ok": False, "error": "Not in word list"}), 400
        BLOCKED_WORDS.remove(value)
        add_log("➖ Blacklist Word Removed", "Dashboard", 0, "–", value)
    elif kind == "phrase":
        if value not in BLOCKED_PHRASES:
            return jsonify({"ok": False, "error": "Not in phrase list"}), 400
        BLOCKED_PHRASES.remove(value)
        add_log("➖ Blacklist Phrase Removed", "Dashboard", 0, "–", value)
    else:
        return jsonify({"ok": False, "error": "kind must be word or phrase"}), 400
    save_data()
    return jsonify({"ok": True})

@app.route("/")
def index():
    return send_from_directory("dashboard", "index.html")

def run_flask():
    port = int(os.getenv("PORT", 8080))
    app.run(host="0.0.0.0", port=port, debug=False, use_reloader=False)

# ─── INTENTS & BOT ────────────────────────────────────────────────────────────
intents = discord.Intents.default()
intents.message_content = True
intents.members = True
bot = commands.Bot(command_prefix="!", intents=intents)

# ─── HELPERS ──────────────────────────────────────────────────────────────────
def is_immune(member: discord.Member) -> bool:
    return member.id in IMMUNE_USER_IDS

def is_whitelisted(member: discord.Member) -> bool:
    return member.id in WHITELISTED_USER_IDS

def is_exempt(member: discord.Member) -> bool:
    if member.id in CONFIG["exempt_users"]:
        return True
    if any(r.id in CONFIG["exempt_roles"] for r in member.roles):
        return True
    if member.guild_permissions.administrator:
        return True
    return False

def is_allowed_url(url: str) -> bool:
    return any(allowed.lower() in url.lower() for allowed in ALLOWED_URLS)

def get_punishment(warn_count: int) -> dict:
    return PUNISHMENTS[min(warn_count - 1, len(PUNISHMENTS) - 1)]

def find_blocked_symbol(content: str) -> str | None:
    for char in content:
        if char in BLOCKED_SYMBOLS:
            return char
    return None

def find_blocked_phrase(content: str) -> str | None:
    lower = content.lower()
    for phrase in BLOCKED_PHRASES:
        if phrase.lower() in lower:
            return phrase
    return None

def find_blocked_word(content: str) -> str | None:
    lower = content.lower()
    for word in BLOCKED_WORDS:
        pattern = r"(?<![a-z0-9])" + re.escape(word.lower()) + r"(?![a-z0-9])"
        if re.search(pattern, lower):
            return word
    return None

def message_has_gif(message: discord.Message) -> bool:
    if GIF_URL_PATTERN.search(message.content):
        return True
    for embed in message.embeds:
        url = str(embed.url or "")
        proxy = str(embed.thumbnail.proxy_url if embed.thumbnail else "")
        if GIF_URL_PATTERN.search(url) or GIF_URL_PATTERN.search(proxy):
            return True
        if embed.type in ("gifv", "image"):
            return True
    for attachment in message.attachments:
        if attachment.filename.lower().endswith(".gif"):
            return True
        if attachment.content_type and "gif" in attachment.content_type.lower():
            return True
    return False

# ─── PUNISHMENT HANDLER ───────────────────────────────────────────────────────
async def apply_punishment(message, member, warn_count, punishment, saved_content, reason_label, blocked_value, log_title):
    try:
        dm_embed = discord.Embed(title="⚠️ Warning", color=discord.Color.red())
        dm_embed.add_field(name="\u200b", value=f"You are not allowed to send **{reason_label}** here.", inline=False)
        dm_embed.add_field(name="Server",     value=SERVER_NAME, inline=True)
        dm_embed.add_field(name="Warnings",   value=f"{warn_count} / {len(PUNISHMENTS)}", inline=True)
        dm_embed.add_field(name="Punishment", value=punishment["label"], inline=False)
        await member.send(embed=dm_embed)
    except discord.Forbidden:
        pass

    if not message.guild.me.guild_permissions.moderate_members:
        print("❌ Bot missing 'Moderate Members' permission!")
    elif member.top_role >= message.guild.me.top_role:
        print(f"❌ Cannot punish {member} — role too high!")
    else:
        if punishment["timeout_minutes"] is not None:
            try:
                await member.timeout(
                    timedelta(minutes=punishment["timeout_minutes"]),
                    reason=f"Sent {reason_label} (warning {warn_count})"
                )
            except (discord.Forbidden, discord.HTTPException) as e:
                print(f"❌ Timeout failed: {e}")
        else:
            try:
                await member.kick(reason=f"Sent {reason_label} (warning {warn_count})")
            except (discord.Forbidden, discord.HTTPException) as e:
                print(f"❌ Kick failed: {e}")

    update_user_stats(member, reason_label, punishment["label"])
    add_log(log_title, str(member), member.id, message.channel.name, f"{blocked_value} | {saved_content[:100]}", punishment["label"])

    log_channel = message.guild.get_channel(CONFIG["log_channel_id"])
    if not log_channel:
        return
    embed = discord.Embed(title=log_title, color=discord.Color.orange(), timestamp=discord.utils.utcnow())
    embed.add_field(name="User",         value=f"{member.mention} ({member})", inline=True)
    embed.add_field(name="Channel",      value=message.channel.mention, inline=True)
    embed.add_field(name="Warnings",     value=f"{warn_count} / {len(PUNISHMENTS)}", inline=True)
    embed.add_field(name="Detected",     value=f"`{blocked_value}`", inline=True)
    embed.add_field(name="Punishment",   value=punishment["label"], inline=True)
    embed.add_field(name="Full Message", value=saved_content[:800] or "*(empty)*", inline=False)
    try:
        await log_channel.send(embed=embed)
    except discord.Forbidden:
        pass

# ─── SYMBOL HANDLER ───────────────────────────────────────────────────────────
async def handle_blocked_symbol(message: discord.Message, symbol: str):
    member = message.author
    try:
        await message.delete()
    except (discord.NotFound, discord.Forbidden):
        pass
    try:
        dm_embed = discord.Embed(title="⚠️ Message Removed", description="Your message was automatically removed.", color=discord.Color.red(), timestamp=discord.utils.utcnow())
        dm_embed.add_field(name="Server", value=SERVER_NAME, inline=True)
        dm_embed.add_field(name="Reason", value="Your message contained a forbidden symbol or special character.", inline=False)
        dm_embed.set_footer(text="Please follow the server rules.")
        await member.send(embed=dm_embed)
    except discord.Forbidden:
        pass

    update_user_stats(member, "Blocked Symbol", "")
    add_log("🔣 Blocked Symbol", str(member), member.id, message.channel.name, repr(symbol))

    log_channel = message.guild.get_channel(CONFIG["log_channel_id"])
    if log_channel:
        log_embed = discord.Embed(title="🔣 Blocked Symbol Detected", color=discord.Color.orange(), timestamp=discord.utils.utcnow())
        log_embed.add_field(name="User",           value=f"{member.mention} ({member})", inline=True)
        log_embed.add_field(name="Channel",        value=message.channel.mention, inline=True)
        log_embed.add_field(name="Matched Symbol", value=f"`{repr(symbol)}`", inline=True)
        log_embed.add_field(name="Full Message",   value=message.content[:800] or "*(empty)*", inline=False)
        try:
            await log_channel.send(embed=log_embed)
        except discord.Forbidden:
            pass

# ─── PHRASE HANDLER ───────────────────────────────────────────────────────────
async def handle_blocked_phrase(message: discord.Message, phrase: str):
    member = message.author
    try:
        await message.delete()
    except (discord.NotFound, discord.Forbidden):
        pass
    try:
        dm_embed = discord.Embed(title="⚠️ Message Removed", description="Your message was automatically removed.", color=discord.Color.red(), timestamp=discord.utils.utcnow())
        dm_embed.add_field(name="Server", value=SERVER_NAME, inline=True)
        dm_embed.add_field(name="Reason", value="Your message contained a forbidden phrase.", inline=False)
        dm_embed.set_footer(text="Please follow the server rules.")
        await member.send(embed=dm_embed)
    except discord.Forbidden:
        pass

    update_user_stats(member, "Blocked Phrase", "")
    add_log("🚫 Blocked Phrase", str(member), member.id, message.channel.name, phrase)

    log_channel = message.guild.get_channel(CONFIG["log_channel_id"])
    if log_channel:
        log_embed = discord.Embed(title="🚫 Blocked Phrase Detected", color=discord.Color.orange(), timestamp=discord.utils.utcnow())
        log_embed.add_field(name="User",           value=f"{member.mention} ({member})", inline=True)
        log_embed.add_field(name="Channel",        value=message.channel.mention, inline=True)
        log_embed.add_field(name="Matched Phrase", value=f"`{phrase}`", inline=True)
        log_embed.add_field(name="Full Message",   value=message.content[:800] or "*(empty)*", inline=False)
        try:
            await log_channel.send(embed=log_embed)
        except discord.Forbidden:
            pass

# ─── WORD HANDLER ─────────────────────────────────────────────────────────────
async def handle_blocked_word(message: discord.Message, word: str):
    member = message.author
    try:
        await message.delete()
    except (discord.NotFound, discord.Forbidden):
        pass
    try:
        dm_embed = discord.Embed(title="⚠️ Message Removed", description="Your message was automatically removed.", color=discord.Color.red(), timestamp=discord.utils.utcnow())
        dm_embed.add_field(name="Server", value=SERVER_NAME, inline=True)
        dm_embed.add_field(name="Reason", value="Your message contained a forbidden word.", inline=False)
        dm_embed.set_footer(text="Please follow the server rules.")
        await member.send(embed=dm_embed)
    except discord.Forbidden:
        pass

    update_user_stats(member, "Blocked Word", "")
    add_log("🤬 Blocked Word", str(member), member.id, message.channel.name, word)

    log_channel = message.guild.get_channel(CONFIG["log_channel_id"])
    if log_channel:
        log_embed = discord.Embed(title="🤬 Blocked Word Detected", color=discord.Color.orange(), timestamp=discord.utils.utcnow())
        log_embed.add_field(name="User",         value=f"{member.mention} ({member})", inline=True)
        log_embed.add_field(name="Channel",      value=message.channel.mention, inline=True)
        log_embed.add_field(name="Matched Word", value=f"`{word}`", inline=True)
        log_embed.add_field(name="Full Message", value=message.content[:800] or "*(empty)*", inline=False)
        try:
            await log_channel.send(embed=log_embed)
        except discord.Forbidden:
            pass

# ─── @EVERYONE / @HERE HANDLER ────────────────────────────────────────────────
async def handle_mass_mention(message: discord.Message, mention_type: str):
    member = message.author
    try:
        await message.delete()
    except (discord.NotFound, discord.Forbidden):
        pass
    try:
        dm_embed = discord.Embed(title="⚠️ Message Removed", description="Your message was automatically removed.", color=discord.Color.red(), timestamp=discord.utils.utcnow())
        dm_embed.add_field(name="Server", value=SERVER_NAME, inline=True)
        dm_embed.add_field(name="Reason", value=f"You are not allowed to use `@{mention_type}` here.", inline=False)
        dm_embed.set_footer(text="Please follow the server rules.")
        await member.send(embed=dm_embed)
    except discord.Forbidden:
        pass

    update_user_stats(member, f"@{mention_type}", "")
    add_log(f"📢 @{mention_type} blocked", str(member), member.id, message.channel.name, f"Used @{mention_type}")

    log_channel = message.guild.get_channel(CONFIG["log_channel_id"])
    if log_channel:
        log_embed = discord.Embed(title=f"📢 @{mention_type} Blocked", color=discord.Color.red(), timestamp=discord.utils.utcnow())
        log_embed.add_field(name="User",    value=f"{member.mention} ({member})", inline=True)
        log_embed.add_field(name="Channel", value=message.channel.mention, inline=True)
        log_embed.add_field(name="Full Message", value=message.content[:800] or "*(empty)*", inline=False)
        try:
            await log_channel.send(embed=log_embed)
        except discord.Forbidden:
            pass

# ─── EVENTS ───────────────────────────────────────────────────────────────────
@bot.event
async def on_ready():
    load_data()
    print(f"✅ Logged in as {bot.user} ({bot.user.id})")
    bot.tree.clear_commands(guild=None)
    for guild in bot.guilds:
        bot.tree.clear_commands(guild=guild)
        await bot.tree.sync(guild=guild)
    await bot.tree.sync()
    print(f"✅ Blocked symbols: {len(BLOCKED_SYMBOLS)} chars")
    print(f"✅ Blocked phrases: {len(BLOCKED_PHRASES)}")
    print(f"✅ Blocked words: {len(BLOCKED_WORDS)}")
    print(f"✅ Immune users: {IMMUNE_USER_IDS}")
    print("✅ @everyone and @here blocking active.")
    print("✅ Dashboard running on http://localhost:5000")
    await bot.change_presence(activity=discord.Game(name=BOT_SETTINGS["status"]))

async def handle_dm(message: discord.Message):
    """Check DMs against all blacklists and log violations to the log channel."""
    user = message.author
    content = message.content

    if is_immune(user):
        return

    triggered = None
    matched   = None

    if message_has_gif(message):
        triggered = "🎞️ GIF in DM"
        matched   = "GIF"
    elif find_blocked_phrase(content):
        matched   = find_blocked_phrase(content)
        triggered = "🚫 Blocked Phrase in DM"
    elif find_blocked_word(content):
        matched   = find_blocked_word(content)
        triggered = "🤬 Blocked Word in DM"
    else:
        invite_m = INVITE_PATTERN.search(content)
        if invite_m:
            matched   = f"discord.gg/{invite_m.group(1)}"
            triggered = "⛔ Discord Invite in DM"
        else:
            url_m = URL_PATTERN.search(content)
            if url_m and not is_allowed_url(url_m.group(0)):
                matched   = url_m.group(0)
                triggered = "⛔ Link in DM"

    if not triggered:
        return

    # Log to dashboard
    add_log(triggered, str(user), user.id, "DM", f"{matched} | {content[:100]}")

    # Find log channel from any guild the bot shares with the user
    log_channel = None
    for guild in bot.guilds:
        ch = guild.get_channel(CONFIG["log_channel_id"])
        if ch:
            log_channel = ch
            break

    if not log_channel:
        return

    embed = discord.Embed(
        title=triggered,
        color=discord.Color.red(),
        timestamp=discord.utils.utcnow()
    )
    embed.add_field(name="User",         value=f"{user.mention} ({user})", inline=True)
    embed.add_field(name="User ID",      value=str(user.id), inline=True)
    embed.add_field(name="Channel",      value="📬 Direct Message", inline=True)
    embed.add_field(name="Detected",     value=f"`{matched}`", inline=True)
    embed.add_field(name="Full Message", value=content[:800] or "*(empty)*", inline=False)
    embed.set_thumbnail(url=str(user.display_avatar.url))
    try:
        await log_channel.send(embed=embed)
    except discord.Forbidden:
        pass

    # Warn the user via DM
    try:
        warn_embed = discord.Embed(
            title="⚠️ DM Warning",
            description="Your DM to this bot was flagged by the moderation system.",
            color=discord.Color.red(),
            timestamp=discord.utils.utcnow()
        )
        warn_embed.add_field(name="Reason",  value=triggered, inline=False)
        warn_embed.add_field(name="Server",  value=SERVER_NAME, inline=True)
        warn_embed.set_footer(text="Your message has been reported to the moderators.")
        await user.send(embed=warn_embed)
    except discord.Forbidden:
        pass


@bot.event
async def on_message(message: discord.Message):
    if message.author.bot:
        return

    # ── DM HANDLING ───────────────────────────────────────────────────────────
    if not message.guild:
        await handle_dm(message)
        return

    member = message.author
    content = message.content

    # Ping-Reply
    if bot.user.mentioned_in(message) and not message.mention_everyone:
        await message.channel.send(BOT_SETTINGS["autoreply"])
        return

    # ── IMMUNE USER — skip ALL checks + can use .kick / .timeout ────────────
    if is_immune(member):

        # ── .whitelistshow ────────────────────────────────────────────────────
        if content.startswith(".whitelistshow"):
            if not WHITELISTED_USER_IDS:
                await message.channel.send("📋 Whitelist is empty.")
            else:
                mentions = "\n".join(f"• <@{uid}>" for uid in sorted(WHITELISTED_USER_IDS))
                await message.channel.send(f"📋 **Whitelisted users ({len(WHITELISTED_USER_IDS)}):**\n{mentions}")
            return

        # ── .unwhitelist <userid> ─────────────────────────────────────────────
        if content.startswith(".unwhitelist"):
            parts = content.split()
            if len(parts) < 2:
                await message.channel.send("❌ Usage: `.unwhitelist <user_id>`")
                return
            try:
                wid = int(parts[1])
            except ValueError:
                await message.channel.send("❌ Invalid user ID.")
                return
            if wid not in WHITELISTED_USER_IDS:
                await message.channel.send(f"❌ User `{wid}` is not whitelisted.")
                return
            WHITELISTED_USER_IDS.discard(wid)
            save_data()
            await message.channel.send(f"✅ User `{wid}` has been **removed** from the whitelist.")
            add_log("❌ Whitelist Remove", str(member), member.id, message.channel.name, f"Removed whitelist for {wid}")
            return

        # ── .whitelist <userid> ──────────────────────────────────────────────
        if content.startswith(".whitelist"):
            parts = content.split()
            if len(parts) < 2:
                await message.channel.send("❌ Usage: `.whitelist <user_id>`")
                return
            try:
                wid = int(parts[1])
            except ValueError:
                await message.channel.send("❌ Invalid user ID.")
                return
            if wid in IMMUNE_USER_IDS:
                await message.channel.send("❌ That user is already fully immune.")
                return
            WHITELISTED_USER_IDS.add(wid)
            save_data()
            await message.channel.send(f"✅ User `{wid}` has been **whitelisted** — they can now use blocked words freely.")
            add_log("✅ Whitelist Add", str(member), member.id, message.channel.name, f"Whitelisted user {wid}")
            return

        # ── .untimeout @user / userid ────────────────────────────────────────
        if content.startswith(".untimeout"):
            target = message.mentions[0] if message.mentions else None
            if not target:
                parts = content.split()
                if len(parts) > 1:
                    try:
                        target = message.guild.get_member(int(parts[1]))
                    except ValueError:
                        pass
            if target is None:
                await message.channel.send("❌ Usage: `.untimeout @user` or `.untimeout <user_id>`")
                return
            if target.id in IMMUNE_USER_IDS:
                await message.channel.send("❌ Cannot untimeout an immune user.")
                return
            try:
                await target.timeout(None, reason=f"Timeout removed by {member}")
                await message.channel.send(f"✅ **{target}** has been un-timed out.")
                add_log("✅ Timeout Removed", str(member), member.id, message.channel.name, f"Removed timeout from {target}")
                log_channel = message.guild.get_channel(CONFIG["log_channel_id"])
                if log_channel:
                    embed = discord.Embed(title="✅ Timeout Removed", color=discord.Color.green(), timestamp=discord.utils.utcnow())
                    embed.add_field(name="Removed by", value=f"{member.mention} ({member})", inline=True)
                    embed.add_field(name="Target",     value=f"{target.mention} ({target})", inline=True)
                    await log_channel.send(embed=embed)
            except discord.Forbidden:
                await message.channel.send("❌ Bot does not have permission to remove this timeout.")
            except discord.HTTPException as e:
                await message.channel.send(f"❌ Error: {e}")
            return

        # ── .kick @user [reason] ──────────────────────────────────────────────
        if content.startswith(".kick"):
            target = message.mentions[0] if message.mentions else None
            if not target:
                # try raw ID after .kick
                parts = content.split()
                if len(parts) > 1:
                    try:
                        target = message.guild.get_member(int(parts[1]))
                    except ValueError:
                        pass
            if target is None:
                await message.channel.send("❌ Usage: `.kick @user [reason]`")
                return
            if target.id in IMMUNE_USER_IDS:
                await message.channel.send("❌ Cannot kick an immune user.")
                return
            parts = content.split(maxsplit=2)
            reason = parts[2] if len(parts) > 2 else "Kicked by authorized user"
            try:
                await target.kick(reason=reason)
                await message.channel.send(f"👢 **{target}** has been kicked. Reason: {reason}")
                add_log("👢 Manual Kick", str(member), member.id, message.channel.name, f"Kicked {target} — {reason}")
                log_channel = message.guild.get_channel(CONFIG["log_channel_id"])
                if log_channel:
                    embed = discord.Embed(title="👢 Manual Kick", color=discord.Color.red(), timestamp=discord.utils.utcnow())
                    embed.add_field(name="Kicked by", value=f"{member.mention} ({member})", inline=True)
                    embed.add_field(name="Target",    value=f"{target.mention} ({target})", inline=True)
                    embed.add_field(name="Reason",    value=reason, inline=False)
                    await log_channel.send(embed=embed)
            except discord.Forbidden:
                await message.channel.send("❌ Bot does not have permission to kick this user.")
            except discord.HTTPException as e:
                await message.channel.send(f"❌ Error: {e}")
            return

        # ── .timeout @user <duration> [reason] ───────────────────────────────
        # Duration examples: 10s  5m  2h  1d  (seconds/minutes/hours/days)
        if content.startswith(".timeout"):
            target = message.mentions[0] if message.mentions else None
            parts = content.split()
            # parse: .timeout @user 10m [reason...]
            # parts[0]=.timeout  parts[1]=mention_or_id  parts[2]=duration  parts[3+]=reason
            if target is None and len(parts) > 1:
                try:
                    target = message.guild.get_member(int(parts[1]))
                except ValueError:
                    pass
            if target is None:
                await message.channel.send("❌ Usage: `.timeout @user <duration> [reason]`\nDuration: `10s` `5m` `2h` `1d`")
                return
            if target.id in IMMUNE_USER_IDS:
                await message.channel.send("❌ Cannot timeout an immune user.")
                return
            # find duration arg (first arg that is not a mention / ID)
            duration_str = None
            reason_start = 3
            for i, p in enumerate(parts[1:], 1):
                if not p.startswith("<@") and not p.lstrip("-").isdigit():
                    duration_str = p
                    reason_start = i + 1
                    break
            if not duration_str:
                await message.channel.send("❌ Please provide a duration. Examples: `10s` `5m` `2h` `1d`")
                return
            # parse duration
            unit_map = {"s": 1, "m": 60, "h": 3600, "d": 86400}
            unit = duration_str[-1].lower()
            if unit not in unit_map or not duration_str[:-1].isdigit():
                await message.channel.send("❌ Invalid duration. Use `10s`, `5m`, `2h`, `1d`.")
                return
            seconds = int(duration_str[:-1]) * unit_map[unit]
            if seconds < 1:
                await message.channel.send("❌ Duration must be at least 1 second.")
                return
            if seconds > 86400 * 28:
                await message.channel.send("❌ Maximum timeout is 28 days.")
                return
            reason = " ".join(parts[reason_start:]) if len(parts) > reason_start else "Timed out by authorized user"
            label = duration_str.lower()
            try:
                await target.timeout(timedelta(seconds=seconds), reason=reason)
                await message.channel.send(f"⏱️ **{target}** has been timed out for **{label}**. Reason: {reason}")
                add_log("⏱️ Manual Timeout", str(member), member.id, message.channel.name, f"Timed out {target} for {label} — {reason}", f"{label} timeout")
                log_channel = message.guild.get_channel(CONFIG["log_channel_id"])
                if log_channel:
                    embed = discord.Embed(title="⏱️ Manual Timeout", color=discord.Color.orange(), timestamp=discord.utils.utcnow())
                    embed.add_field(name="Issued by", value=f"{member.mention} ({member})", inline=True)
                    embed.add_field(name="Target",    value=f"{target.mention} ({target})", inline=True)
                    embed.add_field(name="Duration",  value=label, inline=True)
                    embed.add_field(name="Reason",    value=reason, inline=False)
                    await log_channel.send(embed=embed)
            except discord.Forbidden:
                await message.channel.send("❌ Bot does not have permission to timeout this user.")
            except discord.HTTPException as e:
                await message.channel.send(f"❌ Error: {e}")
            return

        await bot.process_commands(message)
        return

    # ── 1. GIF CHECK — applies to everyone (except immune) ────────────────────
    if message_has_gif(message):
        try:
            await message.delete()
        except (discord.NotFound, discord.Forbidden):
            pass
        gif_warnings[member.id] += 1
        warn_count = gif_warnings[member.id]
        punishment = get_punishment(warn_count)
        await apply_punishment(message, member, warn_count, punishment, content, "GIFs", "GIF", "🎞️ Blocked GIF Detected")
        return

    # ── Below checks respect admin exemption ──────────────────────────────────
    if is_exempt(member):
        await bot.process_commands(message)
        return

    # ── 2. @EVERYONE / @HERE CHECK ────────────────────────────────────────────
    if message.mention_everyone:
        if "@everyone" in content:
            await handle_mass_mention(message, "everyone")
        elif "@here" in content:
            await handle_mass_mention(message, "here")
        return

    # ── 3. PHRASE CHECK ───────────────────────────────────────────────────────
    phrase = find_blocked_phrase(content)
    if phrase:
        await handle_blocked_phrase(message, phrase)
        return

    # ── 4. WORD CHECK — skipped for whitelisted users ────────────────────────
    if not is_whitelisted(member):
        bad_word = find_blocked_word(content)
        if bad_word:
            await handle_blocked_word(message, bad_word)
            return

    # ── 5. SYMBOL CHECK ───────────────────────────────────────────────────────
    symbol = find_blocked_symbol(content)
    if symbol:
        await handle_blocked_symbol(message, symbol)
        return

    # ── 6. REPEAT MESSAGE CHECK ───────────────────────────────────────────────
    normalized = content.strip().lower()
    if normalized:
        tracker = repeat_tracker.get(member.id, {"content": "", "count": 0})
        if normalized == tracker["content"]:
            tracker["count"] += 1
        else:
            tracker = {"content": normalized, "count": 1}
        repeat_tracker[member.id] = tracker

        if tracker["count"] >= 3:
            repeat_tracker[member.id] = {"content": "", "count": 0}
            try:
                await message.delete()
            except (discord.NotFound, discord.Forbidden):
                pass
            try:
                await member.timeout(timedelta(minutes=1), reason="Repeated same message 3 times")
            except (discord.Forbidden, discord.HTTPException) as e:
                print(f"Repeat timeout failed: {e}")
            try:
                dm_embed = discord.Embed(title="Warning Spam", description="You have been timed out for 1 minute.", color=discord.Color.red(), timestamp=discord.utils.utcnow())
                dm_embed.add_field(name="Server", value=SERVER_NAME, inline=True)
                dm_embed.add_field(name="Reason", value="You sent the same message 3 times in a row.", inline=False)
                dm_embed.set_footer(text="Please follow the server rules.")
                await member.send(embed=dm_embed)
            except discord.Forbidden:
                pass

            update_user_stats(member, "Repeat Spam", "1 minute timeout")
            add_log("🔁 Repeat Spam", str(member), member.id, message.channel.name, content[:100], "1 minute timeout")

            log_channel = message.guild.get_channel(CONFIG["log_channel_id"])
            if log_channel:
                log_embed = discord.Embed(title="Repeat Spam Detected", color=discord.Color.orange(), timestamp=discord.utils.utcnow())
                log_embed.add_field(name="User",       value=f"{member.mention} ({member})", inline=True)
                log_embed.add_field(name="Channel",    value=message.channel.mention, inline=True)
                log_embed.add_field(name="Message",    value=content[:800] or "*(empty)*", inline=False)
                log_embed.add_field(name="Punishment", value="1 minute timeout", inline=True)
                try:
                    await log_channel.send(embed=log_embed)
                except discord.Forbidden:
                    pass
            return

    # ── 7. LINK / INVITE CHECK ────────────────────────────────────────────────
    blocked_url = None
    invite_match = INVITE_PATTERN.search(content)
    if invite_match:
        blocked_url = f"discord.gg/{invite_match.group(1)}"
    if not blocked_url:
        url_match = URL_PATTERN.search(content)
        if url_match:
            url = url_match.group(0)
            if not is_allowed_url(url):
                blocked_url = url

    if blocked_url:
        try:
            await message.delete()
        except (discord.NotFound, discord.Forbidden):
            pass
        warnings[member.id] += 1
        warn_count = warnings[member.id]
        punishment = get_punishment(warn_count)
        await apply_punishment(message, member, warn_count, punishment, content, "links", blocked_url, "⛔ Blocked Link Detected")
        return

    await bot.process_commands(message)

# ─── RUN ──────────────────────────────────────────────────────────────────────
if __name__ == "__main__":
    # Start Flask dashboard in background thread
    flask_thread = threading.Thread(target=run_flask, daemon=True)
    flask_thread.start()

    load_data()
    if not TOKEN or TOKEN == "your bot token":
        print("❌ Please set DISCORD_TOKEN as an environment variable.")
    else:
        bot.run(TOKEN)
