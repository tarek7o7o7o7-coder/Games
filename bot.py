import re
import asyncio
from urllib.parse import quote_plus, urljoin

import requests
from bs4 import BeautifulSoup
import discord
from discord import app_commands
from discord.ext import commands

# =========================
# الإعدادات
# =========================
DISCORD_TOKEN = "PUT_YOUR_NEW_BOT_TOKEN_HERE"
BASE_URL = "https://vpesports.com/sharedsteam"
VIDEO_URL = "https://drive.google.com/file/d/1_axgvGNRUJ2Ej05YO4wrtDJvLU7OuQHw/view?usp=sharing"
START_CODE = "1973"
REQUEST_TIMEOUT = 20

# =========================
# إعداد البوت
# =========================
intents = discord.Intents.default()
bot = commands.Bot(command_prefix="!", intents=intents)

authorized_users = set()

# =========================
# أدوات مساعدة
# =========================
def fetch_page(url: str) -> str:
    headers = {
        "User-Agent": "Mozilla/5.0"
    }
    response = requests.get(url, headers=headers, timeout=REQUEST_TIMEOUT)
    response.raise_for_status()
    return response.text


def normalize_text(text: str) -> str:
    text = text.lower().strip()
    text = text.replace("’", "'").replace("‘", "'")
    text = re.sub(r"\s+", " ", text)
    return text


def slugify(text: str) -> str:
    text = text.lower()
    text = text.replace("’", "").replace("‘", "").replace("'", "")
    text = re.sub(r"[^a-z0-9\s\-]", "", text)
    text = re.sub(r"\s+", "-", text).strip("-")
    return text


def find_game_result(html: str, game_name: str):
    soup = BeautifulSoup(html, "html.parser")
    wanted = normalize_text(game_name)
    wanted_slug = slugify(game_name)

    links = soup.find_all("a", href=True)

    for a in links:
        href = a["href"].strip()
        full_url = urljoin(BASE_URL, href)

        if "/sharedsteam/" not in full_url:
            continue

        if full_url.rstrip("/") == BASE_URL.rstrip("/"):
            continue

        block_text = a.parent.get_text(" ", strip=True)
        block_text_norm = normalize_text(block_text)
        href_norm = normalize_text(full_url)

        if (
            wanted in block_text_norm
            or wanted_slug in href_norm
            or wanted_slug in slugify(block_text_norm)
        ):
            parent_text = block_text_norm
            if "get account" in parent_text or "get an account" in parent_text:
                return full_url

    buttons = soup.find_all(string=re.compile(r"get account", re.I))
    if buttons:
        guessed_url = f"{BASE_URL}/{wanted_slug}"
        try:
            guessed_html = fetch_page(guessed_url)
            guessed_text = normalize_text(
                BeautifulSoup(guessed_html, "html.parser").get_text(" ", strip=True)
            )
            if wanted.split()[0] in guessed_text:
                return guessed_url
        except Exception:
            pass

    return None


# =========================
# الأزرار
# =========================
class GameView(discord.ui.View):
    def __init__(self, page_url: str):
        super().__init__(timeout=None)

        self.add_item(
            discord.ui.Button(
                label="فتح صفحة اللعبة",
                style=discord.ButtonStyle.link,
                url=page_url,
                emoji="🎮"
            )
        )

        self.add_item(
            discord.ui.Button(
                label="فيديو الشرح",
                style=discord.ButtonStyle.link,
                url=VIDEO_URL,
                emoji="🎥"
            )
        )


# =========================
# الإيمبد
# =========================
def build_start_ok_embed() -> discord.Embed:
    embed = discord.Embed(
        title="تم التفعيل بنجاح ✅",
        color=0x2ecc71
    )

    embed.add_field(
        name="طريقة البحث",
        value="`/game اسم_اللعبة_كامل`",
        inline=False
    )

    embed.add_field(
        name="ملاحظات",
        value=(
            "• اكتب اسم اللعبة كاملًا.\n"
            "• اكتب اسم اللعبة من Steam.\n"
            "• لو اللعبة متوفرة سيظهر لك رابطها والخطوات.\n"
            "• معظم الألعاب غير متوفرة في الوقت الحالي."
        ),
        inline=False
    )

    embed.set_footer(text="𝕺𝖓𝖎 Games")
    return embed


def build_start_fail_embed() -> discord.Embed:
    embed = discord.Embed(
        title="رمز التفعيل غير صحيح ❌",
        description="تأكد من الرمز ثم حاول مرة أخرى.",
        color=0xe74c3c
    )
    embed.set_footer(text="𝕺𝖓𝖎 Games")
    return embed


def build_not_authorized_embed() -> discord.Embed:
    embed = discord.Embed(
        title="يجب التفعيل أولاً ❌",
        description="استخدم الأمر التالي:\n`/start 1973`",
        color=0xe74c3c
    )
    embed.set_footer(text="𝕺𝖓𝖎 Games")
    return embed


def build_found_embed(game_name: str, page_url: str) -> discord.Embed:
    embed = discord.Embed(
        title="اللعبة متوفرة ✅",
        color=0x2ecc71
    )

    embed.add_field(
        name="اسم اللعبة",
        value=f"`{game_name}`",
        inline=False
    )

    embed.add_field(
        name="رابط الصفحة",
        value=f"[اضغط هنا لفتح الصفحة]({page_url})",
        inline=False
    )

    embed.add_field(
        name="الخطوات",
        value=(
            "1) سجّل دخولك بحسابك في الموقع.\n"
            "2) افتح صفحة اللعبة المطلوبة.\n"
            "3) اضغط على Get Account ثم Play Game.\n"
            "4) شاهد الإعلان حتى يظهر لك الكود، ثم انسخه.\n"
            "5) تأكّد أن لديك حساب تيليجرام.\n"
            "6) ابحث عن البوت @LootAccessBot وافتحه.\n"
            "7) اكتب الأمر /start داخل البوت.\n"
            "8) بعد ذلك، أرسل الكود الذي نسخته.\n"
            "9) ستظهر لك بيانات الحساب، ومنها اسم الحساب والرمز.\n"
            "10) افتح Steam وسجّل الدخول باستخدام البيانات الظاهرة.\n"
            "11) إذا طلب منك Steam كود تأكيد، ارجع إلى البوت.\n"
            "12) اضغط على Next ثم Get Code.\n"
            "13) انسخ الكود الجديد بسرعة وأدخله في Steam.\n"
            "14) بعد تسجيل الدخول، افتح الحساب وحمّل اللعبة.\n"
            "15) بعد انتهاء التحميل، فعّل Offline Mode لتجربة أفضل."
        ),
        inline=False
    )

    embed.set_footer(text="𝕺𝖓𝖎 Games")
    return embed


def build_not_found_embed() -> discord.Embed:
    embed = discord.Embed(
        title="اللعبة غير متاحة حالياً ❌",
        description="سوف يتم توفيرها لاحقًا، حاول مرة أخرى في وقت آخر.",
        color=0xe74c3c
    )
    embed.set_footer(text="𝕺𝖓𝖎 Games")
    return embed


def build_error_embed(message: str) -> discord.Embed:
    embed = discord.Embed(
        title="حدث خطأ ❌",
        description=message,
        color=0xe74c3c
    )
    embed.set_footer(text="𝕺𝖓𝖎 Games")
    return embed


# =========================
# الأحداث
# =========================
@bot.event
async def on_ready():
    try:
        synced = await bot.tree.sync()
        print(f"تم تسجيل {len(synced)} أمر slash.")
    except Exception as e:
        print(f"خطأ في مزامنة الأوامر: {e}")

    print(f"تم تسجيل الدخول كبوت: {bot.user}")


# =========================
# أوامر السلاش
# =========================
@bot.tree.command(name="start", description="تفعيل البوت")
@app_commands.describe(code="اكتب رمز التفعيل")
async def start_command(interaction: discord.Interaction, code: str):
    if code == START_CODE:
        authorized_users.add(interaction.user.id)
        await interaction.response.send_message(
            embed=build_start_ok_embed(),
            ephemeral=True
        )
    else:
        await interaction.response.send_message(
            embed=build_start_fail_embed(),
            ephemeral=True
        )


@bot.tree.command(name="game", description="ابحث عن لعبة في الموقع")
@app_commands.describe(name="اكتب اسم اللعبة كامل")
async def game_command(interaction: discord.Interaction, name: str):
    if interaction.user.id not in authorized_users:
        await interaction.response.send_message(
            embed=build_not_authorized_embed(),
            ephemeral=True
        )
        return

    await interaction.response.defer(thinking=True)

    try:
        search_url = f"{BASE_URL}?search={quote_plus(name)}"
        html = await asyncio.to_thread(fetch_page, search_url)
        result_url = await asyncio.to_thread(find_game_result, html, name)

        if result_url:
            await interaction.followup.send(
                embed=build_found_embed(name, result_url),
                view=GameView(result_url)
            )
        else:
            await interaction.followup.send(
                embed=build_not_found_embed()
            )

    except requests.RequestException:
        await interaction.followup.send(
            embed=build_error_embed("تعذر الاتصال بالموقع حالياً، حاول مرة أخرى بعد قليل.")
        )
    except Exception as e:
        await interaction.followup.send(
            embed=build_error_embed(f"حدث خطأ غير متوقع:\n`{e}`")
        )


bot.run(DISCORD_TOKEN)