import os
import requests
import sqlite3
from dotenv import load_dotenv
import discord
from discord.ext import commands

# Betöltjük a környezeti változókat
load_dotenv()

RIOT_API_KEY = os.getenv('RIOT_API_KEY')

# Beállítjuk a Discord botot
intents = discord.Intents.default()
intents.message_content = True
bot = commands.Bot(command_prefix="!", intents=intents)

# Riot API alap URL-je
RIOT_API_URL = "https://api.riotgames.com/val/"

# Adatbázis kapcsolat létrehozása
conn = sqlite3.connect('valorant_stats.db')
cursor = conn.cursor()

# Táblák létrehozása, ha még nem léteznek
cursor.execute('''
    CREATE TABLE IF NOT EXISTS players (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        player_name TEXT UNIQUE,
        kills INTEGER,
        deaths INTEGER,
        assists INTEGER
    )
''')
conn.commit()

# Helper function: Adatok lekérése Riot API-ból
def get_player_stats(player_name):
    url = f"{RIOT_API_URL}player/{player_name}"
    headers = {
        "X-Riot-Token": RIOT_API_KEY
    }
    response = requests.get(url, headers=headers)

    if response.status_code == 200:
        return response.json()
    else:
        return None

# Helper function: Játékos statisztikáinak mentése adatbázisba
def save_player_stats(player_name, stats):
    cursor.execute('''
        INSERT OR REPLACE INTO players (player_name, kills, deaths, assists)
        VALUES (?, ?, ?, ?)
    ''', (player_name, stats['kills'], stats['deaths'], stats['assists']))
    conn.commit()

# Helper function: Játékos statisztikáinak lekérdezése adatbázisból
def get_saved_stats(player_name):
    cursor.execute('''
        SELECT kills, deaths, assists FROM players WHERE player_name = ?
    ''', (player_name,))
    return cursor.fetchone()

# Parancs a bot számára: játékos statisztikák
@bot.command(name="stats")
async def stats(ctx, player_name: str):
    # Megpróbáljuk lekérni a statisztikákat az adatbázisból
    saved_stats = get_saved_stats(player_name)
    
    if saved_stats:
        kills, deaths, assists = saved_stats
        embed = discord.Embed(title=f"{player_name} (mentett statisztikák)", color=discord.Color.green())
        embed.add_field(name="Ölések", value=kills, inline=True)
        embed.add_field(name="Halálok", value=deaths, inline=True)
        embed.add_field(name="Asszisztok", value=assists, inline=True)
        await ctx.send(embed=embed)
    else:
        # Ha nincsenek mentett statisztikák, lekérjük az API-ból
        stats = get_player_stats(player_name)
        if stats:
            embed = discord.Embed(title=f"{player_name} statisztikái", color=discord.Color.blue())
            embed.add_field(name="Ölések", value=stats["kills"], inline=True)
            embed.add_field(name="Halálok", value=stats["deaths"], inline=True)
            embed.add_field(name="Asszisztok", value=stats["assists"], inline=True)
            await ctx.send(embed=embed)
            
            # Statisztikák mentése adatbázisba
            save_player_stats(player_name, stats)
        else:
            await ctx.send(f"Nem találtam adatokat a {player_name} nevű játékoshoz.")

# Discord bot futtatása
bot.run(os.getenv('DISCORD_BOT_TOKEN'))

# Bot leállításakor az adatbázis kapcsolat lezárása
@bot.event
async def on_ready():
    print(f'{bot.user} bejelentkezett.')

@bot.event
async def on_disconnect():
    conn.close()
