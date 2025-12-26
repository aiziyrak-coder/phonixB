"""
Telegram Bot for Phoenix Scientific Platform
"""
import logging
import os
import sys
import django
from dotenv import load_dotenv
from telegram import Update, ReplyKeyboardMarkup, KeyboardButton
from telegram.ext import Application, CommandHandler, MessageHandler, filters, ContextTypes, ConversationHandler
from django.contrib.auth import authenticate
from apps.users.models import User
from django.core.exceptions import ObjectDoesNotExist
from asgiref.sync import sync_to_async

# Add the parent directory to the path so we can import Django settings
sys.path.append(os.path.join(os.path.dirname(__file__), '..'))

# Load environment variables from .env file
load_dotenv(os.path.join(os.path.dirname(__file__), '..', '.env'))

# Set up Django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.settings_local')

# Setup Django
django.setup()

# Enable logging
logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO
)
logger = logging.getLogger(__name__)

# Conversation states
LOGIN_PHONE, LOGIN_PASSWORD, REGISTER_NAME, REGISTER_LAST_NAME, REGISTER_PHONE, REGISTER_EMAIL, REGISTER_PASSWORD = range(7)

# Service conversation states
BOOK_PUBLISH_START, BOOK_PUBLISH_TITLE, BOOK_PUBLISH_AUTHOR_INFO, BOOK_PUBLISH_ABSTRACT, BOOK_PUBLISH_KEYWORDS = range(5)
PLAGIARISM_CHECK_START, PLAGIARISM_CHECK_FILE, PLAGIARISM_CHECK_TYPE = range(3)
TRANSLATION_START, TRANSLATION_FILE, TRANSLATION_TARGET_LANGUAGE = range(3)
ARTICLE_SUBMIT_START, ARTICLE_SUBMIT_TITLE, ARTICLE_SUBMIT_ABSTRACT, ARTICLE_SUBMIT_KEYWORDS, ARTICLE_SUBMIT_FILE = range(5)

# Keyboard buttons based on user role
def get_keyboard_for_user(user_role=None, is_authenticated=False):
    """Generate keyboard based on user role and authentication status"""
    if not is_authenticated:
        return [
            ["👤 Mening profilim"],
            ["🔒 Kirish", "📝 Ro'yxatdan o'tish"],
            ["ℹ️ Yordam"]
        ]
    
    # Base keyboard for all authenticated users
    keyboard = [
        ["👤 Mening profilim"],
        ["📚 Mening xizmatlarim"],
        ["🔓 Chiqish"],
        ["ℹ️ Yordam"]
    ]
    
    # Add role-specific buttons
    if user_role == 'author':
        keyboard.insert(1, ["📝 Maqola yuborish", "📖 Kitob nashr etish", "🛡️ Antiplagiat tekshiruvi", "🌐 Ilmiy tarjima"])
    elif user_role == 'reviewer':
        keyboard.insert(1, ["🔍 Ko'rib chiqish", "📊 Statistika"])
    elif user_role == 'journal_admin':
        keyboard.insert(1, ["📋 Jurnal boshqaruvi", "👥 Foydalanuvchilar"])
    elif user_role == 'super_admin':
        keyboard.insert(1, ["⚙️ Administrator", "📊 Barcha statistika"])
    elif user_role == 'accountant':
        keyboard.insert(1, ["💰 Moliya", "🧾 Hisobotlar"])
    
    return keyboard

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Send a message when the command /start is issued."""
    user = update.effective_user
    if user is None:
        return
        
    # Check if user is already logged in
    is_authenticated = context.user_data.get('authenticated', False) if context.user_data else False
    user_role = context.user_data.get('role', 'author') if context.user_data else 'author'
    keyboard = get_keyboard_for_user(user_role, is_authenticated)
    
    welcome_message = f"""
Salom {user.first_name}! Phoenix Scientific Platform botiga xush kelibsiz! 🎉

Men sizga quyidagi xizmatlarni taklif qila olaman:
• {'🔓 Chiqish' if is_authenticated else '🔒 Kirish'} - {'tizimdan chiqish' if is_authenticated else 'tizimga kirish'}
• 📝 Ro'yxatdan o'tish - yangi foydalanuvchi sifatida ro'yxatdan o'tish
• 👤 Mening profilim - profilingiz haqida ma'lumot olish
{f"• 📚 Mening xizmatlarim - {user_role.replace('_', ' ').title()} sifatida mavjud xizmatlar" if is_authenticated else ""}

Quyidagi tugmalardan birini tanlang:
"""
    
    if update.message is not None:
        await update.message.reply_text(
            welcome_message,
            reply_markup=ReplyKeyboardMarkup(keyboard, resize_keyboard=True)
        )

async def help_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Send a message when the command /help is issued."""
    # Check if user is already logged in
    is_authenticated = context.user_data.get('authenticated', False) if context.user_data else False
    user_role = context.user_data.get('role', 'author') if context.user_data else 'author'
    keyboard = get_keyboard_for_user(user_role, is_authenticated)
    
    help_text = f"""
Phoenix Scientific Platform bot yordami:

{'/logout' if is_authenticated else '/login'} - {'tizimdan chiqish' if is_authenticated else 'tizimga kirish'}
/register - Ro'yxatdan o'tish
/profile - Profilingiz haqida ma'lumot
/help - Yordam

{"Mavjud xizmatlar:" if is_authenticated else ""}
{"/services" if is_authenticated else ""} - Mening xizmatlarim
/article_submit - Maqola yuborish
/book_publish - Kitob nashr etish
/plagiarism_check - Antiplagiat tekshiruvi
/translation - Ilmiy tarjima

Agar sizda savollar bo'lsa, iltimos biz bilan bog'laning!
"""
    
    if update.message is not None:
        await update.message.reply_text(help_text, reply_markup=ReplyKeyboardMarkup(keyboard, resize_keyboard=True))

# Login conversation handlers
async def login_start(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Start the login conversation."""
    if update.message is not None:
        await update.message.reply_text("Iltimos, telefon raqamingizni kiriting:")
    return LOGIN_PHONE

async def login_phone(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Get phone number for login."""
    if update.message is not None and context.user_data is not None:
        context.user_data['phone'] = update.message.text
        await update.message.reply_text("Parolni kiriting:")
    return LOGIN_PASSWORD

@sync_to_async
def authenticate_user(phone, password):
    """Authenticate user with phone and password."""
    return authenticate(username=phone, password=password)

@sync_to_async
def get_user_by_id(user_id):
    """Get user by ID."""
    return User.objects.get(id=user_id)

@sync_to_async
def check_user_exists(phone):
    """Check if user exists."""
    return User.objects.filter(phone=phone).exists()

@sync_to_async
def create_new_user(phone, first_name, last_name, email, password):
    """Create new user."""
    return User.objects.create_user(
        phone=phone,
        email=email,
        first_name=first_name,
        last_name=last_name,
        password=password,
        affiliation="Telegram User"  # Default affiliation for Telegram users
    )

async def login_password(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Authenticate user with phone and password."""
    if context.user_data is None or update.message is None:
        return ConversationHandler.END
        
    phone = context.user_data.get('phone') if context.user_data else None
    password = update.message.text if update.message else None
    
    if phone is None or password is None:
        return ConversationHandler.END
    
    try:
        # Authenticate user using sync_to_async
        user = await authenticate_user(phone, password)
        if user is not None:
            # Store user data in context
            if context.user_data is not None:
                context.user_data['user_id'] = user.id
                context.user_data['authenticated'] = True
                context.user_data['role'] = user.role
            
            # Get keyboard based on user role
            keyboard = get_keyboard_for_user(user.role, True)
            
            profile_message = f"""
✅ Muvaffaqiyatli kirish!

Foydalanuvchi ma'lumotlari:
👤 Ism: {user.first_name}
👥 Familiya: {user.last_name}
📱 Telefon: {user.phone}
📧 Email: {user.email}
💼 Rol: {user.get_role_display()}
📅 Ro'yxatdan o'tgan sana: {user.date_joined.strftime('%Y-%m-%d')}
"""
            await update.message.reply_text(profile_message, reply_markup=ReplyKeyboardMarkup(keyboard, resize_keyboard=True))
        else:
            await update.message.reply_text("❌ Noto'g'ri telefon raqam yoki parol. Iltimos, qaytadan urinib ko'ring.", 
                                          reply_markup=ReplyKeyboardMarkup(get_keyboard_for_user(), resize_keyboard=True))
            return ConversationHandler.END
    except Exception as e:
        logger.error(f"Login error: {e}")
        if update.message is not None:
            await update.message.reply_text("❌ Kirishda xatolik yuz berdi. Iltimos, qaytadan urinib ko'ring.", 
                                          reply_markup=ReplyKeyboardMarkup(get_keyboard_for_user(), resize_keyboard=True))
    
    return ConversationHandler.END

# Logout handler
async def logout(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Logout user."""
    if context.user_data is not None:
        context.user_data.clear()
    
    if update.message is not None:
        await update.message.reply_text("✅ Siz tizimdan chiqdingiz.", 
                                      reply_markup=ReplyKeyboardMarkup(get_keyboard_for_user(), resize_keyboard=True))

# Services handler
async def services_list(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Show available services based on user role."""
    if context.user_data is None or not context.user_data.get('authenticated', False):
        if update.message is not None:
            await update.message.reply_text("❌ Avval tizimga kirishingiz kerak.", 
                                          reply_markup=ReplyKeyboardMarkup(get_keyboard_for_user(), resize_keyboard=True))
        return
    
    user_role = context.user_data.get('role', 'author')
    
    services_message = f"""
📚 Mening xizmatlarim ({user_role.replace('_', ' ').title()} uchun):

"""
    
    # Role-specific services
    if user_role == 'author':
        services_message += """
📝 Maqola yuborish - Ilmiy maqolangizni platformaga yuboring
📖 Kitob nashr etish - Tayyor qo'lyozmangizni professional kitob shaklida nashr eting
🛡️ Antiplagiat tekshiruvi - Maqolangizning o'ziga xosligini tekshiring
🌐 Ilmiy tarjima - Maqolalaringizni professional tarjimonlar yordamida ingliz va boshqa tillarga o'giring
"""
    elif user_role == 'reviewer':
        services_message += """
🔍 Ko'rib chiqish - Maqolalarni ko'rib chiqish
📊 Statistika - Shaxsiy statistikangiz
"""
    elif user_role == 'journal_admin':
        services_message += """
📋 Jurnal boshqaruvi - Jurnal maqolalarini boshqarish
👥 Foydalanuvchilar - Foydalanuvchilarni boshqarish
"""
    elif user_role == 'super_admin':
        services_message += """
⚙️ Administrator - Barcha tizim sozlamalari
📊 Barcha statistika - Tizim bo'yicha to'liq statistika
"""
    elif user_role == 'accountant':
        services_message += """
💰 Moliya - Moliyaviy operatsiyalar
🧾 Hisobotlar - Moliyaviy hisobotlar
"""
    else:
        services_message += "Hozircha mavjud xizmatlar yo'q."
    
    if update.message is not None:
        await update.message.reply_text(services_message, 
                                      reply_markup=ReplyKeyboardMarkup(get_keyboard_for_user(user_role, True), resize_keyboard=True))

# Registration conversation handlers
async def register_start(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Start the registration conversation."""
    if update.message is not None:
        await update.message.reply_text("Iltimos, ismingizni kiriting:")
    return REGISTER_NAME

async def register_name(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Get user's name for registration."""
    if update.message is not None and context.user_data is not None:
        context.user_data['first_name'] = update.message.text
        await update.message.reply_text("Familiyangizni kiriting:")
    return REGISTER_LAST_NAME

async def register_last_name(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Get user's last name for registration."""
    if update.message is not None and context.user_data is not None:
        context.user_data['last_name'] = update.message.text
        await update.message.reply_text("Telefon raqamingizni kiriting:")
    return REGISTER_PHONE

async def register_phone(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Get phone number for registration."""
    if update.message is not None and context.user_data is not None:
        context.user_data['phone'] = update.message.text
        await update.message.reply_text("Email manzilingizni kiriting:")
    return REGISTER_EMAIL

async def register_email(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Get email for registration."""
    if update.message is not None and context.user_data is not None:
        context.user_data['email'] = update.message.text
        await update.message.reply_text("Parolni kiriting:")
    return REGISTER_PASSWORD

async def register_password(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Final step of registration - create user."""
    if context.user_data is None or update.message is None:
        return ConversationHandler.END
        
    first_name = context.user_data.get('first_name') if context.user_data else None
    last_name = context.user_data.get('last_name') if context.user_data else None
    phone = context.user_data.get('phone') if context.user_data else None
    email = context.user_data.get('email') if context.user_data else None
    password = update.message.text if update.message else None
    
    if first_name is None or last_name is None or phone is None or email is None or password is None:
        return ConversationHandler.END
    
    try:
        # Check if user already exists using sync_to_async
        user_exists = await check_user_exists(phone)
        if user_exists:
            await update.message.reply_text("❌ Ushbu telefon raqam allaqachon ro'yxatdan o'tgan.", 
                                          reply_markup=ReplyKeyboardMarkup(get_keyboard_for_user(), resize_keyboard=True))
            return ConversationHandler.END
        
        # Create new user using sync_to_async (default role is 'author')
        user = await create_new_user(phone, first_name, last_name, email, password)
        
        # Store user data in context and auto-login
        if context.user_data is not None:
            context.user_data['user_id'] = user.id
            context.user_data['authenticated'] = True
            context.user_data['role'] = user.role
        
        # Get keyboard based on user role
        keyboard = get_keyboard_for_user(user.role, True)
        
        success_message = f"""
✅ Muvaffaqiyatli ro'yxatdan o'tdingiz!

Foydalanuvchi ma'lumotlari:
👤 Ism: {user.first_name}
👥 Familiya: {user.last_name}
📱 Telefon: {user.phone}
📧 Email: {user.email}
💼 Rol: {user.get_role_display()}
📅 Ro'yxatdan o'tgan sana: {user.date_joined.strftime('%Y-%m-%d')}

Tizimga avtomatik kirish amalga oshirildi. Quyidagi tugmalardan birini tanlang.
"""
        await update.message.reply_text(success_message, reply_markup=ReplyKeyboardMarkup(keyboard, resize_keyboard=True))
        
    except Exception as e:
        logger.error(f"Registration error: {e}")
        if update.message is not None:
            await update.message.reply_text("❌ Ro'yxatdan o'tishda xatolik yuz berdi. Iltimos, qaytadan urinib ko'ring.", 
                                          reply_markup=ReplyKeyboardMarkup(get_keyboard_for_user(), resize_keyboard=True))
    
    return ConversationHandler.END

# Profile handler
async def show_profile(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Show user profile information."""
    if context.user_data is None or not context.user_data.get('authenticated', False):
        if update.message is not None:
            await update.message.reply_text("❌ Avval tizimga kirishingiz kerak. '🔒 Kirish' tugmasini bosing.", 
                                          reply_markup=ReplyKeyboardMarkup(get_keyboard_for_user(), resize_keyboard=True))
        return
    
    try:
        user_id = context.user_data.get('user_id') if context.user_data else None
        if user_id is None:
            return
            
        # Get user by ID using sync_to_async
        user = await get_user_by_id(user_id)
        
        profile_message = f"""
👤 Sizning profilingiz:

👤 Ism: {user.first_name}
👥 Familiya: {user.last_name}
📱 Telefon: {user.phone}
📧 Email: {user.email}
💼 Rol: {user.get_role_display()}
📊 Daraja: {user.gamification_level}
⭐ Ballar: {user.gamification_points}
📅 Ro'yxatdan o'tgan sana: {user.date_joined.strftime('%Y-%m-%d')}
"""
        if update.message is not None:
            await update.message.reply_text(profile_message, reply_markup=ReplyKeyboardMarkup(get_keyboard_for_user(user.role, True), resize_keyboard=True))
        
    except ObjectDoesNotExist:
        if update.message is not None:
            await update.message.reply_text("❌ Foydalanuvchi topilmadi.", 
                                          reply_markup=ReplyKeyboardMarkup(get_keyboard_for_user(), resize_keyboard=True))
    except Exception as e:
        logger.error(f"Profile error: {e}")
        if update.message is not None:
            await update.message.reply_text("❌ Profil ma'lumotlarini olishda xatolik yuz berdi.", 
                                          reply_markup=ReplyKeyboardMarkup(get_keyboard_for_user(), resize_keyboard=True))

# Service handlers with conversation flow
# Article submission service
async def article_submit_start(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Start article submission service"""
    if context.user_data is None or not context.user_data.get('authenticated', False):
        if update.message is not None:
            await update.message.reply_text("❌ Avval tizimga kirishingiz kerak.", 
                                          reply_markup=ReplyKeyboardMarkup(get_keyboard_for_user(), resize_keyboard=True))
        return ConversationHandler.END
    
    user_role = context.user_data.get('role', 'author')
    if user_role != 'author':
        if update.message is not None:
            await update.message.reply_text("❌ Bu xizmat faqat mualliflar uchun mavjud.", 
                                          reply_markup=ReplyKeyboardMarkup(get_keyboard_for_user(user_role, True), resize_keyboard=True))
        return ConversationHandler.END
    
    service_message = """
📝 Maqola yuborish xizmati

Ilmiy maqolangizni platformaga yuborish uchun quyidagi amallarni bajaring:

1. Maqola nomini kiriting:
"""
    
    if update.message is not None:
        await update.message.reply_text(service_message, 
                                      reply_markup=ReplyKeyboardMarkup([["❌ Bekor qilish"]], resize_keyboard=True))
    return ARTICLE_SUBMIT_TITLE

async def article_submit_title(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Get article title"""
    if update.message is None or context.user_data is None:
        return ConversationHandler.END
    
    if update.message.text == "❌ Bekor qilish":
        user_role = context.user_data.get('role', 'author')
        await update.message.reply_text("❌ Maqola yuborish bekor qilindi.", 
                                      reply_markup=ReplyKeyboardMarkup(get_keyboard_for_user(user_role, True), resize_keyboard=True))
        return ConversationHandler.END
    
    context.user_data['article_title'] = update.message.text
    await update.message.reply_text("2. Maqola annotatsiyasini kiriting:")
    return ARTICLE_SUBMIT_ABSTRACT

async def article_submit_abstract(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Get article abstract"""
    if update.message is None or context.user_data is None:
        return ConversationHandler.END
    
    context.user_data['article_abstract'] = update.message.text
    await update.message.reply_text("3. Kalit so'zlarni kiriting (vergul bilan ajrating):")
    return ARTICLE_SUBMIT_KEYWORDS

async def article_submit_keywords(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Get article keywords"""
    if update.message is None or context.user_data is None:
        return ConversationHandler.END
    
    context.user_data['article_keywords'] = update.message.text
    await update.message.reply_text("4. Maqola matnini yuboring (PDF, DOC, DOCX formatida):")
    return ARTICLE_SUBMIT_FILE

async def article_submit_file(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Get article file and finish submission"""
    if update.message is None or context.user_data is None:
        return ConversationHandler.END
    
    if update.message.text == "❌ Bekor qilish":
        user_role = context.user_data.get('role', 'author')
        await update.message.reply_text("❌ Maqola yuborish bekor qilindi.", 
                                      reply_markup=ReplyKeyboardMarkup(get_keyboard_for_user(user_role, True), resize_keyboard=True))
        return ConversationHandler.END
        
    # Check if document is sent
    if update.message.document is None:
        await update.message.reply_text("❌ Iltimos, faqat hujjat faylini yuboring (PDF, DOC, DOCX).")
        return ARTICLE_SUBMIT_FILE
    
    context.user_data['article_file'] = update.message.document.file_id
    
    # Get user info
    user_id = context.user_data.get('user_id')
    user = await get_user_by_id(user_id)
    
    confirmation_message = f"""
✅ Maqola yuborish buyurtmangiz qabul qilindi!

Buyurtma ma'lumotlari:
📝 Maqola nomi: {context.user_data['article_title']}
📋 Annotatsiya: {context.user_data['article_abstract']}
🔑 Kalit so'zlar: {context.user_data['article_keywords']}
📄 Fayl: {context.user_data['article_file']}

Foydalanuvchi:
👤 {user.first_name} {user.last_name}
📱 {user.phone}
📧 {user.email}

Maqolangiz ko'rib chiqish uchun yuborildi. Ko'rib chiqish natijasi haqida sizga xabar beriladi.
"""
    
    user_role = context.user_data.get('role', 'author')
    await update.message.reply_text(confirmation_message, 
                                  reply_markup=ReplyKeyboardMarkup(get_keyboard_for_user(user_role, True), resize_keyboard=True))
    return ConversationHandler.END

# Book publishing service
async def book_publish_start(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Start book publishing service"""
    if context.user_data is None or not context.user_data.get('authenticated', False):
        if update.message is not None:
            await update.message.reply_text("❌ Avval tizimga kirishingiz kerak.", 
                                          reply_markup=ReplyKeyboardMarkup(get_keyboard_for_user(), resize_keyboard=True))
        return ConversationHandler.END
    
    user_role = context.user_data.get('role', 'author')
    if user_role != 'author':
        if update.message is not None:
            await update.message.reply_text("❌ Bu xizmat faqat mualliflar uchun mavjud.", 
                                          reply_markup=ReplyKeyboardMarkup(get_keyboard_for_user(user_role, True), resize_keyboard=True))
        return ConversationHandler.END
    
    service_message = """
📖 Kitob nashr etish xizmati

Tayyor qo'lyozmangizni professional kitob shaklida nashr etish uchun quyidagi amallarni bajaring:

1. Kitob nomini kiriting:
"""
    
    if update.message is not None:
        await update.message.reply_text(service_message, 
                                      reply_markup=ReplyKeyboardMarkup([["❌ Bekor qilish"]], resize_keyboard=True))
    return BOOK_PUBLISH_TITLE

async def book_publish_title(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Get book title"""
    if update.message is None or context.user_data is None:
        return ConversationHandler.END
    
    if update.message.text == "❌ Bekor qilish":
        user_role = context.user_data.get('role', 'author')
        await update.message.reply_text("❌ Kitob nashr etish bekor qilindi.", 
                                      reply_markup=ReplyKeyboardMarkup(get_keyboard_for_user(user_role, True), resize_keyboard=True))
        return ConversationHandler.END
    
    context.user_data['book_title'] = update.message.text
    await update.message.reply_text("2. Muallif(lar) haqida ma'lumot kiriting:")
    return BOOK_PUBLISH_AUTHOR_INFO

async def book_publish_author_info(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Get author information"""
    if update.message is None or context.user_data is None:
        return ConversationHandler.END
    
    context.user_data['book_author_info'] = update.message.text
    await update.message.reply_text("3. Kitob annotatsiyasini kiriting:")
    return BOOK_PUBLISH_ABSTRACT

async def book_publish_abstract(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Get book abstract"""
    if update.message is None or context.user_data is None:
        return ConversationHandler.END
    
    context.user_data['book_abstract'] = update.message.text
    await update.message.reply_text("4. Kalit so'zlarni kiriting (vergul bilan ajrating):")
    return BOOK_PUBLISH_KEYWORDS

async def book_publish_keywords(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Get book keywords and finish"""
    if update.message is None or context.user_data is None:
        return ConversationHandler.END
    
    context.user_data['book_keywords'] = update.message.text
    
    # Get user info
    user_id = context.user_data.get('user_id')
    user = await get_user_by_id(user_id)
    
    confirmation_message = f"""
✅ Kitob nashr etish buyurtmangiz qabul qilindi!

Buyurtma ma'lumotlari:
📖 Kitob nomi: {context.user_data['book_title']}
👤 Muallif(lar): {context.user_data['book_author_info']}
📝 Annotatsiya: {context.user_data['book_abstract']}
🔑 Kalit so'zlar: {context.user_data['book_keywords']}

Foydalanuvchi:
👤 {user.first_name} {user.last_name}
📱 {user.phone}
📧 {user.email}

Xizmat narxi: 100,000 so'm
Yetkazish muddati: 3 ish kuni

To'lovni amalga oshirish uchun saytimizga tashrif buyuring yoki to'lov qilish tugmasini bosing.
"""
    
    user_role = context.user_data.get('role', 'author')
    await update.message.reply_text(confirmation_message, 
                                  reply_markup=ReplyKeyboardMarkup(get_keyboard_for_user(user_role, True), resize_keyboard=True))
    return ConversationHandler.END

# Plagiarism check service
async def plagiarism_check_start(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Start plagiarism check service"""
    if context.user_data is None or not context.user_data.get('authenticated', False):
        if update.message is not None:
            await update.message.reply_text("❌ Avval tizimga kirishingiz kerak.", 
                                          reply_markup=ReplyKeyboardMarkup(get_keyboard_for_user(), resize_keyboard=True))
        return ConversationHandler.END
    
    user_role = context.user_data.get('role', 'author')
    if user_role != 'author':
        if update.message is not None:
            await update.message.reply_text("❌ Bu xizmat faqat mualliflar uchun mavjud.", 
                                          reply_markup=ReplyKeyboardMarkup(get_keyboard_for_user(user_role, True), resize_keyboard=True))
        return ConversationHandler.END
    
    service_message = """
🛡️ Antiplagiat tekshiruvi xizmati

Maqolangizning o'ziga xosligini tekshirish uchun quyidagi amallarni bajaring:

1. Maqola matnini yuboring (PDF, DOC, DOCX formatida)
"""
    
    if update.message is not None:
        await update.message.reply_text(service_message, 
                                      reply_markup=ReplyKeyboardMarkup([["❌ Bekor qilish"]], resize_keyboard=True))
    return PLAGIARISM_CHECK_FILE

async def plagiarism_check_file(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Get plagiarism check file"""
    if update.message is None or context.user_data is None:
        return ConversationHandler.END
    
    if update.message.text == "❌ Bekor qilish":
        user_role = context.user_data.get('role', 'author')
        await update.message.reply_text("❌ Antiplagiat tekshiruvi bekor qilindi.", 
                                      reply_markup=ReplyKeyboardMarkup(get_keyboard_for_user(user_role, True), resize_keyboard=True))
        return ConversationHandler.END
    
    # Check if document is sent
    if update.message.document is None:
        await update.message.reply_text("❌ Iltimos, faqat hujjat faylini yuboring (PDF, DOC, DOCX).")
        return PLAGIARISM_CHECK_FILE
    
    context.user_data['plagiarism_file'] = update.message.document.file_id
    await update.message.reply_text("2. Tekshiruv turini tanlang:", 
                                  reply_markup=ReplyKeyboardMarkup([
                                      ["⏱️ Tez tekshiruv (30 daqiqa - 50,000 so'm)"],
                                      ["📋 Batafsil tekshiruv (2 ish kuni - 100,000 so'm)"],
                                      ["⚡ Premium tekshiruv (1 ish kuni - 150,000 so'm)"],
                                      ["❌ Bekor qilish"]
                                  ], resize_keyboard=True))
    return PLAGIARISM_CHECK_TYPE

async def plagiarism_check_type(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Get plagiarism check type and finish"""
    if update.message is None or context.user_data is None:
        return ConversationHandler.END
    
    if update.message.text == "❌ Bekor qilish":
        user_role = context.user_data.get('role', 'author')
        await update.message.reply_text("❌ Antiplagiat tekshiruvi bekor qilindi.", 
                                      reply_markup=ReplyKeyboardMarkup(get_keyboard_for_user(user_role, True), resize_keyboard=True))
        return ConversationHandler.END
    
    context.user_data['plagiarism_type'] = update.message.text
    
    # Get user info
    user_id = context.user_data.get('user_id')
    user = await get_user_by_id(user_id)
    
    confirmation_message = f"""
✅ Antiplagiat tekshiruvi buyurtmangiz qabul qilindi!

Buyurtma ma'lumotlari:
📄 Fayl: {context.user_data['plagiarism_file']}
🔍 Tekshiruv turi: {context.user_data['plagiarism_type']}

Foydalanuvchi:
👤 {user.first_name} {user.last_name}
📱 {user.phone}
📧 {user.email}

To'lovni amalga oshirish uchun saytimizga tashrif buyuring yoki to'lov qilish tugmasini bosing.
"""
    
    user_role = context.user_data.get('role', 'author')
    await update.message.reply_text(confirmation_message, 
                                  reply_markup=ReplyKeyboardMarkup(get_keyboard_for_user(user_role, True), resize_keyboard=True))
    return ConversationHandler.END

# Translation service
async def translation_start(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Start translation service"""
    if context.user_data is None or not context.user_data.get('authenticated', False):
        if update.message is not None:
            await update.message.reply_text("❌ Avval tizimga kirishingiz kerak.", 
                                          reply_markup=ReplyKeyboardMarkup(get_keyboard_for_user(), resize_keyboard=True))
        return ConversationHandler.END
    
    user_role = context.user_data.get('role', 'author')
    if user_role != 'author':
        if update.message is not None:
            await update.message.reply_text("❌ Bu xizmat faqat mualliflar uchun mavjud.", 
                                          reply_markup=ReplyKeyboardMarkup(get_keyboard_for_user(user_role, True), resize_keyboard=True))
        return ConversationHandler.END
    
    service_message = """
🌐 Ilmiy tarjima xizmati

Maqolalaringizni professional tarjimonlar yordamida ingliz va boshqa tillarga o'girish uchun quyidagi amallarni bajaring:

1. Tarjima qilinadigan matnni yuboring (PDF, DOC, DOCX formatida)
"""
    
    if update.message is not None:
        await update.message.reply_text(service_message, 
                                      reply_markup=ReplyKeyboardMarkup([["❌ Bekor qilish"]], resize_keyboard=True))
    return TRANSLATION_FILE

async def translation_file(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Get translation file"""
    if update.message is None or context.user_data is None:
        return ConversationHandler.END
    
    if update.message.text == "❌ Bekor qilish":
        user_role = context.user_data.get('role', 'author')
        await update.message.reply_text("❌ Ilmiy tarjima bekor qilindi.", 
                                      reply_markup=ReplyKeyboardMarkup(get_keyboard_for_user(user_role, True), resize_keyboard=True))
        return ConversationHandler.END
    
    # Check if document is sent
    if update.message.document is None:
        await update.message.reply_text("❌ Iltimos, faqat hujjat faylini yuboring (PDF, DOC, DOCX).")
        return TRANSLATION_FILE
    
    context.user_data['translation_file'] = update.message.document.file_id
    await update.message.reply_text("2. Maqsad tilini tanlang:", 
                                  reply_markup=ReplyKeyboardMarkup([
                                      ["🇬🇧 Ingliz tili"],
                                      ["🇷🇺 Rus tili"],
                                      ["🇩🇪 Nemis tili"],
                                      ["🇫🇷 Fransuz tili"],
                                      ["❌ Bekor qilish"]
                                  ], resize_keyboard=True))
    return TRANSLATION_TARGET_LANGUAGE

async def translation_target_language(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Get target language and finish"""
    if update.message is None or context.user_data is None:
        return ConversationHandler.END
    
    if update.message.text == "❌ Bekor qilish":
        user_role = context.user_data.get('role', 'author')
        await update.message.reply_text("❌ Ilmiy tarjima bekor qilindi.", 
                                      reply_markup=ReplyKeyboardMarkup(get_keyboard_for_user(user_role, True), resize_keyboard=True))
        return ConversationHandler.END
    
    context.user_data['translation_language'] = update.message.text
    
    # Get user info
    user_id = context.user_data.get('user_id')
    user = await get_user_by_id(user_id)
    
    confirmation_message = f"""
✅ Ilmiy tarjima buyurtmangiz qabul qilindi!

Buyurtma ma'lumotlari:
📄 Fayl: {context.user_data['translation_file']}
🌍 Maqsad tili: {context.user_data['translation_language']}

Foydalanuvchi:
👤 {user.first_name} {user.last_name}
📱 {user.phone}
📧 {user.email}

Xizmat narxi: 70,000 so'm / sahifa
Yetkazish muddati: 2-5 ish kuni

To'lovni amalga oshirish uchun saytimizga tashrif buyuring yoki to'lov qilish tugmasini bosing.
"""
    
    user_role = context.user_data.get('role', 'author')
    await update.message.reply_text(confirmation_message, 
                                  reply_markup=ReplyKeyboardMarkup(get_keyboard_for_user(user_role, True), resize_keyboard=True))
    return ConversationHandler.END

# Message handler for button presses
async def button_handler(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Handle button presses."""
    if update.message is None:
        return
        
    text = update.message.text
    
    # Check if user is already logged in
    is_authenticated = context.user_data.get('authenticated', False) if context.user_data else False
    user_role = context.user_data.get('role', 'author') if context.user_data else 'author'
    keyboard = get_keyboard_for_user(user_role, is_authenticated)
    
    if text == "🔒 Kirish":
        await login_start(update, context)
    elif text == "📝 Ro'yxatdan o'tish":
        await register_start(update, context)
    elif text == "👤 Mening profilim":
        await show_profile(update, context)
    elif text == "📚 Mening xizmatlarim":
        await services_list(update, context)
    elif text == "🔓 Chiqish":
        await logout(update, context)
    elif text == "ℹ️ Yordam":
        await help_command(update, context)
    elif text == "📝 Maqola yuborish":
        await article_submit_start(update, context)
    elif text == "📖 Kitob nashr etish":
        await book_publish_start(update, context)
    elif text == "🛡️ Antiplagiat tekshiruvi":
        await plagiarism_check_start(update, context)
    elif text == "🌐 Ilmiy tarjima":
        await translation_start(update, context)
    elif text == "⚙️ Administrator":
        if user_role == 'super_admin':
            await update.message.reply_text("⚙️ Administrator paneli. Bu yerda tizim sozlamalari bo'ladi.", 
                                          reply_markup=ReplyKeyboardMarkup(get_keyboard_for_user(user_role, True), resize_keyboard=True))
        else:
            await update.message.reply_text("❌ Bu funksiya faqat super administratorlar uchun mavjud.", 
                                          reply_markup=ReplyKeyboardMarkup(get_keyboard_for_user(user_role, True), resize_keyboard=True))
    elif text == "📊 Barcha statistika":
        if user_role == 'super_admin':
            await update.message.reply_text("📊 Barcha statistika. Bu yerda tizim bo'yicha to'liq statistika bo'ladi.", 
                                          reply_markup=ReplyKeyboardMarkup(get_keyboard_for_user(user_role, True), resize_keyboard=True))
        else:
            await update.message.reply_text("❌ Bu funksiya faqat super administratorlar uchun mavjud.", 
                                          reply_markup=ReplyKeyboardMarkup(get_keyboard_for_user(user_role, True), resize_keyboard=True))
    else:
        await update.message.reply_text("❌ Noma'lum buyruq. Iltimos, quyidagi tugmalardan birini tanlang:", 
                                       reply_markup=ReplyKeyboardMarkup(keyboard, resize_keyboard=True))

def main() -> None:
    """Start the bot."""
    # Get token from environment variables
    token = os.getenv("TELEGRAM_BOT_TOKEN")
    if not token:
        logger.error("TELEGRAM_BOT_TOKEN environment variable not set")
        return
    
    # Create the Application and pass it your bot's token
    application = Application.builder().token(token).build()
    
    # Add conversation handlers
    login_conv_handler = ConversationHandler(
        entry_points=[MessageHandler(filters.Regex("^🔒 Kirish$"), login_start)],
        states={
            LOGIN_PHONE: [MessageHandler(filters.TEXT & ~filters.COMMAND, login_phone)],
            LOGIN_PASSWORD: [MessageHandler(filters.TEXT & ~filters.COMMAND, login_password)],
        },
        fallbacks=[]
    )
    
    register_conv_handler = ConversationHandler(
        entry_points=[MessageHandler(filters.Regex("^📝 Ro'yxatdan o'tish$"), register_start)],
        states={
            REGISTER_NAME: [MessageHandler(filters.TEXT & ~filters.COMMAND, register_name)],
            REGISTER_LAST_NAME: [MessageHandler(filters.TEXT & ~filters.COMMAND, register_last_name)],
            REGISTER_PHONE: [MessageHandler(filters.TEXT & ~filters.COMMAND, register_phone)],
            REGISTER_EMAIL: [MessageHandler(filters.TEXT & ~filters.COMMAND, register_email)],
            REGISTER_PASSWORD: [MessageHandler(filters.TEXT & ~filters.COMMAND, register_password)],
        },
        fallbacks=[]
    )
    
    # Article submission conversation handler
    article_submit_conv_handler = ConversationHandler(
        entry_points=[MessageHandler(filters.Regex("^📝 Maqola yuborish$"), article_submit_start)],
        states={
            ARTICLE_SUBMIT_TITLE: [MessageHandler(filters.TEXT & ~filters.COMMAND, article_submit_title)],
            ARTICLE_SUBMIT_ABSTRACT: [MessageHandler(filters.TEXT & ~filters.COMMAND, article_submit_abstract)],
            ARTICLE_SUBMIT_KEYWORDS: [MessageHandler(filters.TEXT & ~filters.COMMAND, article_submit_keywords)],
            ARTICLE_SUBMIT_FILE: [MessageHandler(filters.Document.ALL, article_submit_file)],
        },
        fallbacks=[]
    )
    
    # Book publishing conversation handler
    book_publish_conv_handler = ConversationHandler(
        entry_points=[MessageHandler(filters.Regex("^📖 Kitob nashr etish$"), book_publish_start)],
        states={
            BOOK_PUBLISH_TITLE: [MessageHandler(filters.TEXT & ~filters.COMMAND, book_publish_title)],
            BOOK_PUBLISH_AUTHOR_INFO: [MessageHandler(filters.TEXT & ~filters.COMMAND, book_publish_author_info)],
            BOOK_PUBLISH_ABSTRACT: [MessageHandler(filters.TEXT & ~filters.COMMAND, book_publish_abstract)],
            BOOK_PUBLISH_KEYWORDS: [MessageHandler(filters.TEXT & ~filters.COMMAND, book_publish_keywords)],
        },
        fallbacks=[]
    )
    
    # Plagiarism check conversation handler
    plagiarism_check_conv_handler = ConversationHandler(
        entry_points=[MessageHandler(filters.Regex("^🛡️ Antiplagiat tekshiruvi$"), plagiarism_check_start)],
        states={
            PLAGIARISM_CHECK_FILE: [MessageHandler(filters.Document.ALL, plagiarism_check_file)],
            PLAGIARISM_CHECK_TYPE: [MessageHandler(filters.TEXT & ~filters.COMMAND, plagiarism_check_type)],
        },
        fallbacks=[]
    )
    
    # Translation conversation handler
    translation_conv_handler = ConversationHandler(
        entry_points=[MessageHandler(filters.Regex("^🌐 Ilmiy tarjima$"), translation_start)],
        states={
            TRANSLATION_FILE: [MessageHandler(filters.Document.ALL, translation_file)],
            TRANSLATION_TARGET_LANGUAGE: [MessageHandler(filters.TEXT & ~filters.COMMAND, translation_target_language)],
        },
        fallbacks=[]
    )
    
    # Add command handlers
    application.add_handler(CommandHandler("start", start))
    application.add_handler(CommandHandler("help", help_command))
    application.add_handler(CommandHandler("logout", logout))
    application.add_handler(CommandHandler("services", services_list))
    application.add_handler(CommandHandler("article_submit", article_submit_start))
    
    # Add conversation handlers
    application.add_handler(login_conv_handler)
    application.add_handler(register_conv_handler)
    application.add_handler(article_submit_conv_handler)
    application.add_handler(book_publish_conv_handler)
    application.add_handler(plagiarism_check_conv_handler)
    application.add_handler(translation_conv_handler)
    
    # Add message handler for button presses
    application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, button_handler))
    
    # Run the bot until the user presses Ctrl-C
    application.run_polling(allowed_updates=Update.ALL_TYPES)

if __name__ == "__main__":
    main()