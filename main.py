import nextcord
from nextcord.ext import commands
from nextcord import Interaction, SlashOption, ButtonStyle
from nextcord.ui import Button, View
import json
import uuid
import os

# ---------- Konfiguracja ----------
intents = nextcord.Intents.default()
intents.members = True

bot = commands.Bot(intents=intents, command_prefix="!")

ADMIN_ROLE = "Admin"
BUYER_ROLE = "Kupujący"
PROD_ROLE = "Producent"

PRODUCTS_FILE = "products.json"

# ---------- Utils ----------
def load_products():
    if not os.path.exists(PRODUCTS_FILE):
        with open(PRODUCTS_FILE, "w") as f:
            json.dump({}, f)
    with open(PRODUCTS_FILE, "r") as f:
        return json.load(f)

def save_products(data):
    with open(PRODUCTS_FILE, "w") as f:
        json.dump(data, f, indent=2)

# ---------- Start ----------
@bot.event
async def on_ready():
    await bot.sync_all_application_commands()
    print(f"✅ Bot jest gotowy jako {bot.user} (ID: {bot.user.id})")
    for guild in bot.guilds:
        print(f"➡️  Zsynchronizowano komendy dla: {guild.name} ({guild.id})")

# ---------- Dodaj produkt ----------
@bot.slash_command(name="dodaj_produkt", description="Dodaj produkt i przypisz producenta (tylko Admin)")
async def dodaj_produkt(interaction: Interaction,
                       nazwa: str = SlashOption(description="Nazwa produktu"),
                       producent: str = SlashOption(description="@Producent (względnie ID lub nazwa)")):
    roles = [r.name for r in interaction.user.roles]
    if ADMIN_ROLE not in roles:
        return await interaction.response.send_message("Nie masz uprawnień (tylko Admin).", ephemeral=True)

    data = load_products()
    data[nazwa.lower()] = {
        "producent": producent,
        "max_quantity": 10
    }
    save_products(data)
    await interaction.response.send_message(f"✅ Dodano produkt `{nazwa}` (limit: 10 szt.)", ephemeral=True)

# ---------- Usuń produkt ----------
@bot.slash_command(name="usun_produkt", description="Usuń produkt (tylko Admin)")
async def usun_produkt(interaction: Interaction,
                       nazwa: str = SlashOption(description="Nazwa produktu")):
    roles = [r.name for r in interaction.user.roles]
    if ADMIN_ROLE not in roles:
        return await interaction.response.send_message("Nie masz uprawnień.", ephemeral=True)

    data = load_products()
    key = nazwa.lower()
    if key in data:
        del data[key]
        save_products(data)
        await interaction.response.send_message(f"🗑️ Usunięto produkt `{nazwa}`.", ephemeral=True)
    else:
        await interaction.response.send_message("Nie znaleziono produktu.", ephemeral=True)

# ---------- Ustaw limit ----------
@bot.slash_command(name="ustaw_limit", description="Ustaw maksymalny limit sztuk (tylko Admin)")
async def ustaw_limit(interaction: Interaction,
                      nazwa: str = SlashOption(description="Nazwa produktu"),
                      limit: int = SlashOption(description="Limit", min_value=1)):
    roles = [r.name for r in interaction.user.roles]
    if ADMIN_ROLE not in roles:
        return await interaction.response.send_message("Nie masz uprawnień.", ephemeral=True)

    data = load_products()
    key = nazwa.lower()
    if key not in data:
        return await interaction.response.send_message("Nie znaleziono produktu.", ephemeral=True)

    data[key]["max_quantity"] = limit
    save_products(data)
    await interaction.response.send_message(f"✅ Limit `{nazwa}` ustawiony na {limit} szt.", ephemeral=True)

# ---------- Lista produktów ----------
@bot.slash_command(name="lista_produktow", description="Pokaż listę produktów")
async def lista_produktow(interaction: Interaction):
    data = load_products()
    if not data:
        return await interaction.response.send_message("Brak produktów.", ephemeral=True)
    msg = "\n".join([f"• **{k}** → {v['producent']} (limit: {v.get('max_quantity',10)})" for k,v in data.items()])
    await interaction.response.send_message(msg, ephemeral=True)

# ---------- Menu ----------
@bot.slash_command(name="menu", description="Pokaż menu dostępnych produktów")
async def menu(interaction: Interaction):
    data = load_products()
    if not data:
        return await interaction.response.send_message("Menu puste.", ephemeral=True)
    embed = nextcord.Embed(title="📜 Menu produktów", color=0x2ecc71)
    for name, info in data.items():
        embed.add_field(name=name, value=f"Producent: {info['producent']}\nLimit: {info.get('max_quantity', 10)} szt.", inline=False)
    await interaction.response.send_message(embed=embed)

# ---------- Zamów ----------
@bot.slash_command(name="zamow", description="Złóż zamówienie")
async def zamow(interaction: Interaction,
                produkt: str = SlashOption(description="Nazwa produktu"),
                ilosc: int = SlashOption(description="Ilość", min_value=1)):
    roles = [r.name for r in interaction.user.roles]
    if BUYER_ROLE not in roles:
        return await interaction.response.send_message("Tylko Kupujący mogą składać zamówienia.", ephemeral=True)

    data = load_products()
    key = produkt.lower()
    if key not in data:
        return await interaction.response.send_message("Nie znaleziono produktu.", ephemeral=True)

    info = data[key]
    if ilosc > info.get("max_quantity", 10):
        return await interaction.response.send_message(f"⚠️ Limit to {info.get('max_quantity',10)} szt.", ephemeral=True)

    producent = info["producent"]
    order_id = str(uuid.uuid4())[:8]

    embed = nextcord.Embed(title="📦 Nowe zamówienie", color=0x3498db)
    embed.add_field(name="Produkt", value=produkt)
    embed.add_field(name="Ilość", value=str(ilosc))
    embed.add_field(name="Zamawiający", value=interaction.user.mention)
    embed.set_footer(text=f"Order ID: {order_id}")

    class DoneView(View):
        @nextcord.ui.button(label="Zakończone", style=ButtonStyle.green)
        async def done(self, button, inter):
            buyer = bot.get_user(interaction.user.id)
            if buyer:
                await buyer.send(f"🍽️ Twoje zamówienie ({ilosc}x {produkt}) jest gotowe! Producent: {inter.user.mention}")
                await inter.response.send_message("✅ Powiadomiono kupującego.", ephemeral=True)

    # wysyłka do producenta
    sent = False
    if producent.startswith("<@"):
        try:
            uid = int(producent.replace("<@", "").replace("!", "").replace(">", ""))
            user = bot.get_user(uid) or await bot.fetch_user(uid)
            if user:
                await user.send(embed=embed, view=DoneView())
                sent = True
        except:
            pass

    if not sent:
        await interaction.response.send_message("Nie udało się wysłać wiadomości do producenta.", ephemeral=True)
        return

    await interaction.response.send_message("✅ Zamówienie wysłane do producenta!", ephemeral=True)

# ---------- Start ----------
if __name__ == "__main__":
    token = os.getenv("BOT_TOKEN")
    if not token:
        print("❌ Brak BOT_TOKEN w zmiennych Render!")
    else:
        bot.run(token)
