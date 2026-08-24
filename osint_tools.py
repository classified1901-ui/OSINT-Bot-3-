import asyncio
import subprocess
import hashlib
import aiohttp
from concurrent.futures import ThreadPoolExecutor

executor = ThreadPoolExecutor(max_workers=3)

async def check_gravatar(email: str) -> str:
    email = email.strip().lower()
    hash_email = hashlib.md5(email.encode()).hexdigest()
    url = f"https://www.gravatar.com/avatar/{hash_email}?d=404"
    try:
        async with aiohttp.ClientSession() as session:
            async with session.get(url, timeout=8) as resp:
                if resp.status == 200:
                    return f"✅ Gravatar found\nhttps://www.gravatar.com/{hash_email}"
                return "❌ No Gravatar"
    except:
        return "⚠️ Failed to check Gravatar"

def clean_holehe(output: str) -> str:
    lines = output.splitlines()
    clean = []
    for line in lines:
        line = line.strip()
        if not line:
            continue
        if line.startswith("[+]") or line.startswith("[-]") or line.startswith("[x]") or line.startswith("[!]"):
            clean.append(line)
        elif "websites checked" in line.lower() or "checked in" in line.lower():
            clean.append(line)
    if not clean:
        return "No clear results found"
    return "\n".join(clean[:40])

def run_holehe_sync(email: str) -> str:
    try:
        result = subprocess.run(
            ["holehe", email, "--only-used", "--no-color"],
            capture_output=True,
            text=True,
            timeout=55
        )
        return clean_holehe(result.stdout)
    except subprocess.TimeoutExpired:
        return "⏱️ Holehe timed out"
    except Exception as e:
        return f"Holehe error: {e}"

def run_sherlock_sync(username: str) -> str:
    try:
        result = subprocess.run(
            ["sherlock", username, "--print-found", "--timeout", "8", "--no-color"],
            capture_output=True,
            text=True,
            timeout=70
        )
        output = result.stdout.strip()
        return output[:1500] if output else "No results from Sherlock"
    except subprocess.TimeoutExpired:
        return "⏱️ Sherlock timed out"
    except Exception as e:
        return f"Sherlock error: {e}"

def run_maigret_sync(username: str) -> str:
    try:
        result = subprocess.run(
            ["maigret", username, "--no-color", "--timeout", "10"],
            capture_output=True,
            text=True,
            timeout=90
        )
        output = result.stdout.strip()
        return output[:1800] if output else "No results from Maigret"
    except subprocess.TimeoutExpired:
        return "⏱️ Maigret timed out"
    except Exception as e:
        return f"Maigret error: {e}"

async def email_osint(email: str) -> str:
    gravatar = await check_gravatar(email)
    loop = asyncio.get_event