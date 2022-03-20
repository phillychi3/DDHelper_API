import re
import discord 
from discord.ext import commands
import sqlite3
import discord_webhook
from matplotlib.pyplot import get
import json

intents = discord.Intents.all()
bot = commands.Bot(command_prefix="dd.", intents=intents)
bot.remove_command("help")

def valid_user():

    def predicate(ctx):
        istrue = ctx.message.author.id in [762484891945664542]
        if istrue:
            return istrue
        else:
            raise commands.errors.CheckFailure('你不是管理員')
    return commands.check(predicate)


def getdata():
    conn = sqlite3.connect('images_data.db')
    c=conn.cursor()
    c.execute('SELECT * FROM images WHERE verify ISNULL')
    data = c.fetchall()
    conn.close()
    return data

@bot.command()
async def uncheck(ctx):
    data = getdata()
    data = json.dumps(data)
    await ctx.send(data)

@valid_user()
@bot.command()
async def verify(ctx,image):
    conn = sqlite3.connect('images_data.db')
    c=conn.cursor()
    c.execute(f'UPDATE images SET verify = "True" WHERE name = "{image}"')
    conn.commit()
    conn.close()
    await ctx.send("Image verified")
    
@valid_user()
@bot.command()
async def unverify(ctx,image):
    conn = sqlite3.connect('images_data.db')
    c=conn.cursor()
    c.execute(f'UPDATE images SET verify = NULL WHERE name = "{image}"')
    conn.commit()
    conn.close()
    await ctx.send("Image unverified")

bot.run("OTQ4NTgxNDM1NjA0ODkzNzk3.Yh95Tg.wDbsQI0TS8B8HeoGMWKCtdshCKA")