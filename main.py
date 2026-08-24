import discord
from discord.ext import commands
import os
import asyncio
import subprocess
import hashlib
import aiohttp
import dns.resolver
from concurrent.futures import ThreadPoolExecutor
import phonenumbers
from phonenumbers import geocoder, carrier, timezone
from faker import Faker
from urllib.parse import quote_plus

executor = ThreadPoolExecutor(max_workers=3)
fake = Faker()

# ========== إعدادات الحماية ==========
ALLOWED_ROLE_NAME = "Bot Search Access"
ALLOWED_USERS = {
    123456789012345678,   # ← غيّر الرقم ده لـ User ID بتاعك
}

# اختياري: حط ID قناة عشان يسجل فيها عمليات البحث (سيبه 0 لو مش عايز)
LOG_CHANNEL_ID = 0

intents = discord.Intents.default()
intents.message_content = True
bot = commands.Bot(command_prefix="!", intents=intents, help_command=None)

def is_allowed(ctx):
    if ctx.author.id in ALLOWED_USERS:
        return True
    if ctx.guild:
        role = discord.utils.get(ctx.guild.roles, name=ALLOWED_ROLE_NAME)
        if role and role in ctx.author.roles:
            return True
    return False

async def send_long(msg, text, max_len=1900):
    if len(text) <= max_len:
        await msg.edit(content=text)
        return
    chunks = []
    while text:
        if len(text) <= max_len:
            chunks.append(text)
            break
        split_at = text.rfind("\n", 0, max_len)
        if split_at == -1:
            split_at = max_len
        chunks.append(text[:split_at])
        text = text[split_at:].lstrip("\n")
    await msg.edit(content=chunks[0])
    for chunk in chunks[1:]:
        await msg.channel.send(chunk)

async def log_search(ctx, command_name, target):
    if LOG_CHANNEL_ID == 0:
        return
    try:
        channel = bot.get_channel(LOG_CHANNEL_ID)
        if channel:
            await channel.send(f"**Log:** `{ctx.author}` used `{command_name}` on `{target}`")
    except:
        pass

# ========== أدوات المساعدة ==========

async def check_gravatar(email):
    email = email.strip().lower()
    h = hashlib.md5(email.encode()).hexdigest()
    url = f"https://www.gravatar.com/avatar/{h}?d=404"
    try:
        async with aiohttp.ClientSession() as session:
            async with session.get(url, timeout=8) as resp:
                if resp.status == 200:
                    return f"✅ Gravatar found\nhttps://www.gravatar.com/{h}"
                return "❌ No Gravatar"
    except:
        return "⚠️ Failed to check Gravatar"

def clean_holehe(output):
    lines = output.splitlines()
    clean = []
    for line in lines:
        line = line.strip()
        if line.startswith("[+]") or line.startswith("[-]") or line.startswith("[x]"):
            clean.append(line)
        elif "websites checked" in line.lower():
            clean.append(line)
    return "\n".join(clean[:40]) if clean else "No clear results"

def run_holehe(email):
    try:
        r = subprocess.run(["holehe", email, "--only-used", "--no-color"],
                           capture_output=True, text=True, timeout=50)
        return clean_holehe(r.stdout)
    except Exception as e:
        return f"Holehe error: {e}"

def run_sherlock(username):
    try:
        r = subprocess.run(["sherlock", username, "--print-found", "--timeout", "8", "--no-color"],
                           capture_output=True, text=True, timeout=60)
        out = r.stdout.strip()
        return out if out else "No results"
    except Exception as e:
        return f"Sherlock error: {e}"

def run_maigret(username):
    try:
        r = subprocess.run(["maigret", username, "--no-color", "--timeout", "10"],
                           capture_output=True, text=True, timeout=90)
        out = r.stdout.strip()
        return out if out else "No results"
    except Exception as e:
        return f"Maigret error: {e}"

def run_socialscan(query):
    try:
        r = subprocess.run(["socialscan", query],
                           capture_output=True, text=True, timeout=25)
        out = r.stdout.strip()
        return out if out else "No results"
    except Exception as e:
        return f"socialscan error: {e}"

def analyze_phone(number):
    try:
        if not number.startswith("+"):
            parsed = phonenumbers.parse(number, "EG")
        else:
            parsed = phonenumbers.parse(number, None)
        if not phonenumbers.is_valid_number(parsed):
            return "❌ Invalid phone number"
        country = geocoder.country_name_for_number(parsed, "en")
        region = geocoder.description_for_number(parsed, "en")
        car = carrier.name_for_number(parsed, "en") or "Unknown"
        tz = ", ".join(timezone.time_zones_for_number(parsed)) or "Unknown"
        num_type = phonenumbers.number_type(parsed)
        type_map = {0: "Fixed line", 1: "Mobile", 2: "Fixed or Mobile", 3: "Toll free", 4: "Premium rate", 5: "Shared cost", 6: "VoIP", 7: "Personal number", 8: "Pager", 9: "UAN", 10: "Voicemail", 99: "Unknown"}
        line_type = type_map.get(num_type, "Unknown")
        e164 = phonenumbers.format_number(parsed, phonenumbers.PhoneNumberFormat.E164)
        international = phonenumbers.format_number(parsed, phonenumbers.PhoneNumberFormat.INTERNATIONAL)
        national = phonenumbers.format_number(parsed, phonenumbers.PhoneNumberFormat.NATIONAL)
        wa = f"https://wa.me/{e164.replace('+', '')}"
        dorks = [
            f"https://www.google.com/search?q=%22{quote_plus(e164)}%22",
            f"https://www.google.com/search?q=%22{quote_plus(international)}%22",
            f"https://www.google.com/search?q=%22{quote_plus(e164)}%22+(site:facebook.com+OR+site:instagram.com+OR+site:twitter.com+OR+site:x.com)",
            f"https://www.google.com/search?q=%22{quote_plus(e164)}%22+(filetype:pdf+OR+filetype:xls+OR+filetype:csv)",
            f"https://www.google.com/search?q=%22{quote_plus(e164)}%22+site:pastebin.com+OR+site:ghostbin.com",
        ]
        return (
            f"**Phone OSINT**\n\n"
            f"**Number:** `{e164}`\n"
            f"**International:** `{international}`\n"
            f"**National:** `{national}`\n\n"
            f"**Valid:** ✅\n"
            f"**Country:** {country}\n"
            f"**Region:** {region or 'N/A'}\n"
            f"**Carrier:** {car}\n"
            f"**Line Type:** {line_type}\n"
            f"**Timezone:** {tz}\n\n"
            f"**WhatsApp:** {wa}\n\n"
            f"**Google Dorks:**\n"
            f"1. Exact: {dorks[0]}\n"
            f"2. International: {dorks[1]}\n"
            f"3. Social: {dorks[2]}\n"
            f"4. Documents: {dorks[3]}\n"
            f"5. Pastes: {dorks[4]}"
        )
    except Exception as e:
        return f"❌ Error: {e}"

async def lookup_ip(ip):
    try:
        url = f"http://ip-api.com/json/{ip}?fields=status,message,country,countryCode,regionName,city,zip,lat,lon,timezone,isp,org,as,asname,mobile,proxy,hosting,query"
        async with aiohttp.ClientSession() as session:
            async with session.get(url, timeout=10) as resp:
                data = await resp.json()
        if data.get("status") != "success":
            return f"❌ Failed: {data.get('message', 'Unknown error')}"
        return (
            f"**IP OSINT:** `{data.get('query')}`\n\n"
            f"**Country:** {data.get('country')} ({data.get('countryCode')})\n"
            f"**Region:** {data.get('regionName')}\n"
            f"**City:** {data.get('city')}\n"
            f"**ZIP:** {data.get('zip') or 'N/A'}\n"
            f"**Coords:** {data.get('lat')}, {data.get('lon')}\n"
            f"**Timezone:** {data.get('timezone')}\n\n"
            f"**ISP:** {data.get('isp')}\n"
            f"**Org:** {data.get('org')}\n"
            f"**ASN:** {data.get('as')}\n"
            f"**AS Name:** {data.get('asname')}\n\n"
            f"**Mobile:** {'Yes' if data.get('mobile') else 'No'}\n"
            f"**Proxy/VPN:** {'Yes' if data.get('proxy') else 'No'}\n"
            f"**Hosting:** {'Yes' if data.get('hosting') else 'No'}"
        )
    except Exception as e:
        return f"❌ IP error: {e}"

async def domain_osint(domain):
    domain = domain.lower().strip().replace("http://", "").replace("https://", "").split("/")[0]
    result = [f"**Domain OSINT:** `{domain}`\n"]

    # DNS Records
    try:
        result.append("**DNS Records:**")
        for rtype in ["A", "AAAA", "MX", "NS", "TXT", "CNAME"]:
            try:
                answers = dns.resolver.resolve(domain, rtype)
                for rdata in answers:
                    result.append(f"`{rtype}` → {rdata.to_text()}")
            except:
                pass
    except Exception as e:
        result.append(f"DNS error: {e}")

    # Subdomains from crt.sh
    try:
        url = f"https://crt.sh/?q=%.{domain}&output=json"
        async with aiohttp.ClientSession() as session:
            async with session.get(url, timeout=15) as resp:
                if resp.status == 200:
                    data = await resp.json()
                    subs = set()
                    for entry in data[:80]:
                        name = entry.get("name_value", "")
                        for line in name.split("\n"):
                            line = line.strip().lower()
                            if domain in line and "*" not in line:
                                subs.add(line)
                    if subs:
                        result.append("\n**Subdomains (crt.sh):**")
                        for s in sorted(list(subs))[:40]:
                            result.append(f"- {s}")
                    else:
                        result.append("\n**Subdomains:** No results")
                else:
                    result.append("\n**Subdomains:** Failed to fetch")
    except Exception as e:
        result.append(f"\n**Subdomains error:** {e}")

    return "\n".join(result)

def generate_dorks(query):
    q = quote_plus(query)
    return (
        f"**Google Dorks for:** `{query}`\n\n"
        f"1. Exact match:\nhttps://www.google.com/search?q=%22{q}%22\n\n"
        f"2. Social media:\nhttps://www.google.com/search?q=%22{q}%22+(site:facebook.com+OR+site:instagram.com+OR+site:twitter.com+OR+site:x.com+OR+site:linkedin.com)\n\n"
        f"3. Documents:\nhttps://www.google.com/search?q=%22{q}%22+(filetype:pdf+OR+filetype:doc+OR+filetype:xls+OR+filetype:txt)\n\n"
        f"4. Pastes & leaks:\nhttps://www.google.com/search?q=%22{q}%22+(site:pastebin.com+OR+site:ghostbin.com+OR+site:hastebin.com)\n\n"
        f"5. Code & GitHub:\nhttps://www.google.com/search?q=%22{q}%22+site:github.com\n\n"
        f"6. Index of:\nhttps://www.google.com/search?q=intitle:%22index+of%22+%22{q}%22"
    )

def generate_fake_persona():
    return (
        f"**[FAKE DATA - TRAINING ONLY]**\n\n"
        f"**Name:** {fake.name()}\n"
        f"**Username:** {fake.user_name()}\n"
        f"**Email:** {fake.email()}\n"
        f"**Phone:** {fake.phone_number()}\n"
        f"**Address:** {fake.address().replace(chr(10), ', ')}\n"
        f"**Job:** {fake.job()}\n"
        f"**Company:** {fake.company()}\n"
        f"**Bio:** {fake.text(max_nb_chars=100)}\n\n"
        f"⚠️ Completely synthetic data for social engineering awareness training only."
    )

async def email_osint(email):
    gravatar = await check_gravatar(email)
    loop = asyncio.get_event_loop()
    holehe_res = await loop.run_in_executor(executor, run_holehe, email)
    social_res = await loop.run_in_executor(executor, run_socialscan, email)
    return (
        f"**Email OSINT:** `{email}`\n\n"
        f"**Gravatar:**\n{gravatar}\n\n"
        f"**Holehe:**\n```\n{holehe_res}\n```\n\n"
        f"**socialscan:**\n```\n{social_res}\n```"
    )

async def username_osint(username):
    loop = asyncio.get_event_loop()
    sherlock_res = await loop.run_in_executor(executor, run_sherlock, username)
    maigret_res = await loop.run_in_executor(executor, run_maigret, username)
    social_res = await loop.run_in_executor(executor, run_socialscan, username)
    return (
        f"**Username OSINT:** `{username}`\n\n"
        f"**Sherlock:**\n```\n{sherlock_res}\n```\n\n"
        f"**Maigret:**\n```\n{maigret_res}\n```\n\n"
        f"**socialscan:**\n```\n{social_res}\n```"
    )

# ========== الأوامر ==========

@bot.event
async def on_ready():
    print(f"Bot is online: {bot.user}")

@bot.command(name="help")
async def help_cmd(ctx):
    if not is_allowed(ctx):
        return await ctx.reply("⛔ Not authorized.")
    embed = discord.Embed(title="OSINT Bot Commands", color=0x2b2d31)
    embed.add_field(name="!email <email>", value="Email registration check", inline=False)
    embed.add_field(name="!user <username>", value="Username search (multi-tool)", inline=False)
    embed.add_field(name="!phone <number>", value="Phone analysis + dorks", inline=False)
    embed.add_field(name="!ip <ip>", value="IP geolocation + ISP", inline=False)
    embed.add_field(name="!domain <domain>", value="DNS + Subdomains", inline=False)
    embed.add_field(name="!dork <query>", value="Generate Google Dorks", inline=False)
    embed.add_field(name="!fake", value="Fake persona (SE training)", inline=False)
    embed.set_footer(text="Authorized users only • Public OSINT tools")
    await ctx.reply(embed=embed)

@bot.command(name="email")
@commands.cooldown(1, 60, commands.BucketType.user)
async def email_cmd(ctx, email: str):
    if not is_allowed(ctx):
        return await ctx.reply("⛔ Not authorized.")
    if "@" not in email:
        return await ctx.reply("Invalid email.")
    await log_search(ctx, "email", email)
    msg = await ctx.reply("Searching email...")
    try:
        result = await email_osint(email)
        await send_long(msg, result)
    except Exception as e:
        await msg.edit(content=f"Error: {e}")

@bot.command(name="user")
@commands.cooldown(1, 60, commands.BucketType.user)
async def user_cmd(ctx, username: str):
    if not is_allowed(ctx):
        return await ctx.reply("⛔ Not authorized.")
    await log_search(ctx, "user", username)
    msg = await ctx.reply("Searching username...")
    try:
        result = await username_osint(username)
        await send_long(msg, result)
    except Exception as e:
        await msg.edit(content=f"Error: {e}")

@bot.command(name="phone")
@commands.cooldown(1, 20, commands.BucketType.user)
async def phone_cmd(ctx, *, number: str):
    if not is_allowed(ctx):
        return await ctx.reply("⛔ Not authorized.")
    await log_search(ctx, "phone", number)
    msg = await ctx.reply("Analyzing phone...")
    try:
        result = analyze_phone(number)
        await send_long(msg, result