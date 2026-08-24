import discord
from discord.ext import commands
import os
import asyncio
import subprocess
import hashlib
import aiohttp
from concurrent.futures import ThreadPoolExecutor

executor = ThreadPoolExecutor(max_workers=3)

intents = discord.Intents.default()
intents.message_content = True
bot = commands.Bot(command_prefix="!", intents=intents)

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
    return "\n".join(clean[:25]) if clean else "No clear results"

def run_holehe(email):
    try:
        r = subprocess.run(["holehe", email, "--only-used", "--no-color"],
                           capture_output=True, text=True, timeout=50)
        return clean_holehe(r.stdout)
    except Exception as e:
        return f"Holehe error: {e}"

def run_sherlock(username):
    try:
        r = subprocess.run(["sherlock", username, "--print-found", "--timeout", "7", "--no-color"],
                           capture_output=True, text=True, timeout=55)
        out = r.stdout.strip()
        return out[:1200] if out else "No results"
    except Exception as e:
        return f"Sherlock error: {e}"

def run_maigret(username):
    try:
        r = subprocess.run(["maigret", username, "--no-color", "--timeout", "8"],
                           capture_output=True, text=True, timeout=80)
        out = r.stdout.strip()
        return out[:1500] if out else "No results"
    except Exception as e:
        return f"Maigret error: {e}"

def run_socialscan(query):
    try:
        r = subprocess.run(["socialscan", query],
                           capture_output=True, text=True, timeout=25)
        out = r.stdout.strip()
        return out[:800] if out else "No results"
    except Exception as e:
        return f"socialscan error: {e}"

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
        f"**Maigret (deep):**\n```\n{maigret_res}\n```\n\n"
        f"**socialscan:**\n```\n{social_res}\n```"
    )

@bot.event
async def on_ready():
    print(f"Bot is online: {bot.user}")

@bot.command(name="email")
@commands.cooldown(1, 60, commands.BucketType.user)
async def email_cmd(ctx, email: str):
    if "@" not in email:
        return await ctx.reply("Invalid email.")
    msg = await ctx.reply("Searching email (this may take 30-60 sec)...")
    try:
        result = await email_osint(email)
        await msg.edit(content=result)
    except Exception as e:
        await msg.edit(content=f"Error: {e}")

@bot.command(name="user")
@commands.cooldown(1, 60, commands.BucketType.user)
async def user_cmd(ctx, username: str):
    msg = await ctx.reply("Searching username across tools (this may take 40-90 sec)...")
    try:
        result = await username_osint(username)
        await msg.edit(content=result)
    except Exception as e:
        await msg.edit(content=f"Error: {e}")

bot.run(os.environ["DISCORD_TOKEN"])