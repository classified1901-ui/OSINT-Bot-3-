import discord
from discord.ext import commands
import os
from osint_tools import email_osint, username_osint

intents = discord.Intents.default()
intents.message_content = True

bot = commands.Bot(command_prefix="!", intents=intents)

@bot.event
async def on_ready():
    print(f"Bot is online: {bot.user}")

@bot.command(name="email")
@commands.cooldown(1, 45, commands.BucketType.user)
async def email_cmd(ctx, email: str):
    if "@" not in email:
        return await ctx.reply("Invalid email address.")
    
    msg = await ctx.reply("Searching email... please wait ⏳")
    try:
        result = await email_osint(email)
        await msg.edit(content=result)
    except Exception as e:
        await msg.edit(content=f"Error: {e}")

@bot.command(name="user")
@commands.cooldown(1, 45, commands.BucketType.user)
async def user_cmd(ctx, username: str):
    msg = await ctx.reply("Searching username across multiple tools... please wait ⏳")
    try:
        result = await username_osint(username)
        await msg.edit(content=result)
    except Exception as e:
        await msg.edit(content=f"Error: {e}")

bot.run(os.environ["DISCORD_TOKEN"])