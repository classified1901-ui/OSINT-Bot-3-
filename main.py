import discord
from discord.ext import commands
import os
import asyncio
import subprocess
import hashlib
import aiohttp
import dns.resolver
import re
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime, timezone
import phonenumbers
from phonenumbers import geocoder, carrier, timezone as phone_tz
from faker import Faker
from urllib.parse import quote_plus

executor = ThreadPoolExecutor(max_workers=2)
fake = Faker()

ALLOWED_ROLE_NAME = "Bot Search Access"
ALLOWED_USERS = {
1100376229544202263,  # ← غيّر الرقم ده لـ User ID بتاعك
}

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

def clean_ansi(text):
    return re.sub(r'\x1b\[[0-9;]*[a-zA-Z]', '', text)

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
    found = []
    for line in lines:
        line = line.strip()
        if line.startswith("[+]"):
            found.append(line)
    if found:
        return "**Registered on:**\n" + "\n".join(found[:30])
    return "No clear positive results"

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

def run_user_scanner(target, is_email=True):
    try:
        if is_email:
            cmd = ["user-scanner", "-e", target, "--no-nsfw"]
        else:
            cmd = ["user-scanner", "-u", target, "--no-nsfw"]
        r = subprocess.run(cmd, capture_output=True, text=True, timeout=180)
        output = clean_ansi(r.stdout + "\n" + r.stderr)
        lines = [line for line in output.splitlines() if line.strip()]
        # نحتفظ بالنتائج المفيدة فقط
        useful = []
        for line in lines:
            lower = line.lower()
            if any(x in lower for x in ["found", "exists", "registered", "taken", "http", "https", "[+]", "profile", "username", "email"]):
                useful.append(line)
            elif "error" in lower or "timeout" in lower:
                useful.append(line)
        if useful:
            return "\n".join(useful[:80])
        return output[:3000] if output else "No useful results or scan failed"
    except subprocess.TimeoutExpired:
        return "⏱️ Scan timed out (too long). Try again later or use lighter tools (!email / !user)."
    except Exception as e:
        return f"user-scanner error: {e}"

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
        tz = ", ".join(phone_tz.time_zones_for_number(parsed)) or "Unknown"
        num_type = phonenumbers.number_type(parsed)
        type_map = {
            0: "Fixed line", 1: "Mobile", 2: "Fixed or Mobile",
            3: "Toll free", 4: "Premium rate", 5: "Shared cost",
            6: "VoIP", 7: "Personal number", 8: "Pager",
            9: "UAN", 10: "Voicemail", 99: "Unknown"
        }
        line_type = type_map.get(num_type, "Unknown")
        e164 = phonenumbers.format_number(parsed, phonenumbers.PhoneNumberFormat.E164)
        international = phonenumbers.format_number(parsed, phonenumbers.PhoneNumberFormat.INTERNATIONAL)
        national = phonenumbers.format_number(parsed, phonenumbers.PhoneNumberFormat.NATIONAL)
        wa = f"https://wa.me/{e164.replace('+', '')}"
        dorks = [
            f"https://www.google.com/search?q=%22{quote_plus(e164)}%22",
            f"https://www.google.com/search?q=%22{quote_plus(international)}%22",
            f"https://www.google.com/search?q=%22{quote_plus(e164)}%22+(site:facebook.com+OR+site:instagram.com+OR+site:twitter.com+OR+site:x.com)",
            f"https://www.google.com/search?q=%22{quote_plus(e164)}%22+(filetype:pdf+OR+filetype:xls)",
            f"https://www.google.com/search?q=%22{quote_plus(e164)}%22+site:truecaller.com",
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
            f"1. {dorks[0]}\n"
            f"2. {dorks[1]}\n"
            f"3. Social: {dorks[2]}\n"
            f"4. Documents: {dorks[3]}\n"
            f"5. Truecaller: {dorks[4]}"
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
    try:
        url = f"https://crt.sh/?q=%.{domain}&output=json"
        async with aiohttp.ClientSession() as session:
            async with session.get(url, timeout=15) as resp:
                if resp.status == 200:
                    data = await resp.json()
                    subs = set()
                    for entry in data[:50]:
                        name = entry.get("name_value", "")
                        for line in name.split("\n"):
                            line = line.strip().lower()
                            if domain in line and "*" not in line:
                                subs.add(line)
                    if subs:
                        result.append("\n**Subdomains (crt.sh):**")
                        for s in sorted(list(subs))[:25]:
                            result.append(f"- {s}")
                    else:
                        result.append("\n**Subdomains:** No results")
    except Exception as e:
        result.append(f"\n**Subdomains error:** {e}")
    return "\n".join(result)

def discord_id_lookup(user_id):
    try:
        uid = int(user_id)
        timestamp_ms = (uid >> 22) + 1420070400000
        created = datetime.fromtimestamp(timestamp_ms / 1000, tz=timezone.utc)
        created_str = created.strftime("%Y-%m-%d %H:%M:%S UTC")
        return (
            f"**Discord User ID Lookup**\n\n"
            f"**ID:** `{uid}`\n"
            f"**Account Created:** {created_str}\n\n"
            f"**Public Lookup Links:**\n"
            f"• https://discord.id/?id={uid}\n"
            f"• https://discordlookup.com/user/{uid}\n"
            f"• https://discord.com/users/{uid}\n\n"
            f"⚠️ Only public creation date + links. Cannot retrieve email or private data."
        )
    except Exception as e:
        return f"❌ Invalid Discord ID or error: {e}"