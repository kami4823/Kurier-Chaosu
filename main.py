import nextcord
from nextcord.ext import commands
from nextcord import Interaction, SlashOption, ButtonStyle
from nextcord.ui import Button, View
import json
import uuid
import os

# --------- Konfiguracja ----------
intents = nextcord.Intents.default()
intents.members = True

bot = commands.Bot(intents=intents, command_prefix="!")

ADMIN_ROLE = "Admin"       # rola która może dodawać/usuń produkty
BUYER_ROLE = "Kupujący"    # rola która może zamawiać
PROD_ROLE = "Producent"    # rola producenta

PRODUCTS_FILE = "products.json"  # plik z produktami

# --------- Utility: zapisz/wczytaj produkty ----------
def load_products():
    if not os.path.exists(PRODUCTS_FILE):
        with open(PRODUCTS_FILE, "w") as f:
            json.dump({}, f)
    with open(PRODUCTS_FILE, "r") as f:
        return json.load(f)

def save_products(data):
    with open(PRODUCTS_FILE, "w") as f:
        json.dump(data, f, indent=2)

# --------- Start ----------
@bot.event
async def on_ready():
    print(f"Bot is ready. Logged in as {bot.user} (id: {bot.user.id})")

# --------- Dodaj produkt (Admin) ----------
@bot.slash_command(name="dodaj_produkt", description="Dodaj produkt i przypisz producenta")
async def dodaj_produkt(interaction: Interaction,
                        nazwa: str = SlashOption(description="Nazwa produktu"),
                        producent: str = SlashOption(description="@Producent (mention lub ID)")):
    roles = [r.name for r in interaction.user.roles]
    if ADMIN_ROLE not in roles:
        await interaction.response.send_message("Nie masz uprawnień (tylko Admin).", ephemeral=True)
        return

    data = load_products()
    data[nazwa.lower()] = {
        "producent": producent,
        "max_quantity": 10  # domyślny limit = 10 sztuk
    }
    save_products(data)
    await interaction.response.send_message(f"✅ Dodano produkt `{nazwa}` -> producent: {producent} (limit: 10 szt.)", ephemeral=True)

# --------- Usuń produkt (Admin) ----------
@bot.slash_command(name="usun_produkt", description="Usuń produkt z listy")
async def usun_produkt(interaction: Interaction,
                       nazwa: str = SlashOption(description="Nazwa produktu")):
    roles = [r.name for r in interaction.user.roles]
    if ADMIN_ROLE not in roles:
        await interaction.response.send_message("Nie masz uprawnień.", ephemeral=True)
        return

    data = load_products()
    key = nazwa.lower()
    if key in data:
        del data[key]
        save_products(data)
        await interaction.response.send_message(f"🗑️ Usunięto produkt `{nazwa}`.", ephemeral=True)
    else:
        await interaction.response.send_message("Nie znaleziono produktu.", ephemeral=True)

# --------- Ustaw limit (Admin) ----------
@bot.slash_command(name="ustaw_limit", description="Ustaw maksymalną ilość sztuk danego produktu")
async def ustaw_limit(interaction: Interaction,
                      nazwa: str = SlashOption(description="Nazwa produktu"),
                      limit: int = SlashOption(description="Maksymalna ilość", min_value=1)):
    roles = [r.name for r in interaction.user.roles]
    if ADMIN_ROLE not in roles:
        await interaction.response.send_message("Nie masz uprawnień.", ephemeral=True)
        return

    data = load_products()
    key = nazwa.lower()
    if key not in data:
        await interaction.response.send_message("Nie znaleziono produktu.", ephemeral=True)
        return

    data[key]["max_quantity"] = limit
    save_products(data)
    await interaction.response.send_message(f"✅ Limit dla `{nazwa}` ustawiony na {limit} szt.", ephemeral=True)

# --------- Lista produktów ----------
@bot.slash_command(name="lista_produktow", description="Lista produktów i producentów")
async def lista_produktow(interaction: Interaction):
    data = load_products()
    if not data:
        await interaction.response.send_message("Brak produktów.", ephemeral=True)
        return
    lines = []
    for k, v in data.items():
        producent = v["producent"]
        limit = v.get("max_quantity", 10)
        lines.append(f"• **{k}** → {producent} (limit: {limit})")
    await interaction.response.send_message("\n".join(lines), ephemeral=True)

# --------- Menu publiczne ----------
@bot.slash_command(name="menu", description="Pokaż menu produktów")
async def menu(interaction: Interaction):
    data = load_products()
    if not data:
        await interaction.response.send_message("Menu jest puste.", ephemeral=True)
        return
    embed = nextcord.Embed(title="📜 Menu produktów", color=0x2ecc71)
    for name, info in data.items():
        producent = info["producent"]
        limit = info.get("max_quantity", 10)
        embed.add_field(name=name, value=f"Producent: {producent}\nLimit: {limit} szt.", inline=False)
    await interaction.response.send_message(embed=embed, ephemeral=False)

# --------- Zamów (Kupujący) ----------
@bot.slash_command(name="zamow", description="Złóż zamówienie")
async def zamow(interaction: Interaction,
                produkt: str = SlashOption(description="Nazwa produktu"),
                ilosc: int = SlashOption(description="Ilość", min_value=1)):
    roles = [r.name for r in interaction.user.roles]
    if BUYER_ROLE not in roles:
        await interaction.response.send_message("Tylko Kupujący mogą zamawiać.", ephemeral=True)
        return

    data = load_products()
    key = produkt.lower()
    if key not in data:
        await interaction.response.send_message("Nie znaleziono produktu.", ephemeral=True)
        return

    produkt_info = data[key]
    max_q = produkt_info.get("max_quantity", 10)
    if ilosc > m
