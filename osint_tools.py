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
    return "\n