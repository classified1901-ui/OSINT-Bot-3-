import asyncio
import subprocess
import hashlib
import aiohttp
from concurrent.futures import ThreadPoolExecutor

executor = ThreadPoolExecutor(max_workers=2)

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
    if not clean:
        return "No clear results found"
    return "\n".join(clean[:30])

def run_holehe_sync(email):
    try:
        r = subprocess.run(
            ["holehe", email, "--only-used", "--no-color"],
            capture_output=True, text=True, timeout=50
        )
        return clean_holehe(r.stdout)
    except subprocess.TimeoutExpired:
        return "⏱️ Holehe timed out"
    except Exception as e:
        return f"Holehe error: {e}"

def run_sherlock_sync(username):
    try:
        r = subprocess.run(
            ["sherlock", username, "--print-found", "--timeout", "8", "--no-color"],
            capture_output=True, text=True, timeout=60
        )
        out = r.stdout.strip()
        return out[:1400] if out else "No results from Sherlock"
    except subprocess.TimeoutExpired:
        return "⏱️ Sherlock timed out"
    except Exception as e:
        return f"Sherlock error: {e}"

async def email_osint(email):
    gravatar = await check_gravatar(email)
    loop = asyncio.get_event_loop()
    holehe = await loop.run_in_executor(executor, run_holehe_sync, email)
    return f"**Email OSINT for:** `{email}`\n\n**Gravatar:**\n{gravatar}\n\n**Holehe:**\n```\n{holehe}\n```"

async def username_osint(username):
    loop = asyncio.get_event_loop()
    result = await loop.run_in_executor(executor, run_sherlock_sync, username)
    return f"**Username OSINT for:** `{username}`\n```\n{result}\n```"