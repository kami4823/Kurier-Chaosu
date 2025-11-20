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
    if ilosc > max_q:
        await interaction.response.send_message(f"⚠️ Maksymalna ilość dla `{produkt}` to {max_q} szt.", ephemeral=True)
        return

    producent_info = produkt_info["producent"]
    order_id = str(uuid.uuid4())[:8]

    # Embed do producenta
    embed = nextcord.Embed(title="📦 Nowe zamówienie", color=0x3498db)
    embed.add_field(name="Produkt", value=produkt, inline=False)
    embed.add_field(name="Ilość", value=str(ilosc), inline=False)
    embed.add_field(name="Zamawiający", value=f"{interaction.user.mention}", inline=False)
    embed.set_footer(text=f"Order ID: {order_id}")

    # Przyciski "Zakończone"
    class DoneView(View):
        def __init__(self, order_id, buyer_id, product_name, qty):
            super().__init__(timeout=None)
            self.order_id = order_id
            self.buyer_id = buyer_id
            self.product_name = product_name
            self.qty = qty

        @nextcord.ui.button(label="Zakończone", style=ButtonStyle.green, custom_id="done_button")
        async def done_button(self, button: Button, interaction_btn: Interaction):
            caller = interaction_btn.user
            buyer = bot.get_user(self.buyer_id)
            if buyer:
                try:
                    await buyer.send(f"🍽️ Twoje zamówienie ({self.qty}x {self.product_name}) jest gotowe do odbioru! Producent: {caller.mention}")
                    await interaction_btn.response.send_message("Potwierdzone — kupujący został powiadomiony.", ephemeral=True)
                except Exception:
                    await interaction_btn.response.send_message("Nie udało się wysłać wiadomości.", ephemeral=True)
            else:
                await interaction_btn.response.send_message("Nie znaleziono kupującego.", ephemeral=True)

    view = DoneView(order_id, interaction.user.id, produkt, ilosc)

    # Wyślij PW do producenta (mention lub nazwa)
    sent = False
    if producent_info.startswith("<@") and ">" in producent_info:
        try:
            uid = int(producent_info.replace("<@", "").replace("!", "").replace(">", ""))
            user = bot.get_user(uid) or await bot.fetch_user(uid)
            if user:
                await user.send(embed=embed, view=view)
                sent = True
        except:
            sent = False

    if not sent and interaction.guild:
        for m in interaction.guild.members:
            if producent_info.lower().strip("@") in (m.display_name.lower() + m.name.lower()):
                try:
                    await m.send(embed=embed, view=view)
                    sent = True
                    break
                except:
                    sent = False

    if not sent:
        await interaction.response.send_message("Nie udało się wysłać wiadomości do producenta. Sprawdź `/dodaj_produkt`.", ephemeral=True)
        return

    await interaction.response.send_message(f"✅ Zamówienie wysłane. Order ID: {order_id}", ephemeral=True)

# --------- Uruchom bot ---------
if __name__ == "__main__":
    token = os.environ.get("BOT_TOKEN")
    if not token:
        print("Brak BOT_TOKEN w zmiennych środowiskowych!")
    else:
        bot.run(token)
