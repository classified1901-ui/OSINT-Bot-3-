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

ALLOWED_ROLE_NAME = "Bot Search Access"
ALLOWED_USERS = {
    123456789012345678,  # ← غيّر الرقم ده لـ User ID بتاعك
}

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

async def check_gravatar(email):
    email = email.strip