import os
import random
import logging
from collections import defaultdict
from telegram import Update
from telegram.ext import Application, CommandHandler, MessageHandler, CallbackQueryHandler, filters, ContextTypes

# ==================== CẤU HÌNH BẢO MẬT ĐÃ ĐƯỢC CẬP NHẬT ====================
TOKEN = "8931506777:AAFzNjP4yi56bA7yVMTwPilXULPkjtt2BKE"
OWNER_ID = 1087968824  
DB_FILE = "allowed_groups.txt"
SUDO_FILE = "sudo_users.txt"
# ==================================================================================

logging.basicConfig(format='%(asctime)s - %(name)s - %(levelname)s - %(message)s', level=logging.INFO)

# Trạng thái cấu hình chạy của hệ thống
bot_chat_enabled = True
autodelete_enabled = False  # Chế độ tự động xóa tin nhắn khóa mõm đối thủ

# Bộ nhớ tạm để lưu lịch sử câu chửi (tránh lặp quá 2 lần trong 1 box)
insult_history = defaultdict(list)

# --- Quản lý dữ liệu file ---
def load_ids(filename):
    if not os.path.exists(filename):
        return set()
    with open(filename, "r") as f:
        return set(int(line.strip()) for line in f if line.strip())

def save_ids(filename, id_set):
    with open(filename, "w") as f:
        for _id in id_set:
            f.write(f"{_id}\n")

allowed_groups = load_ids(DB_FILE)
sudo_users = load_ids(SUDO_FILE)

def has_permission(user_id):
    return user_id == OWNER_ID or user_id in sudo_users

def is_group_allowed(update: Update) -> bool:
    if not update.effective_chat:
        return False
    chat_id = update.effective_chat.id
    if update.effective_chat.type in ["group", "supergroup"]:
        return chat_id in allowed_groups
    return True

# --- Hàm thông minh lấy câu chửi không trùng quá 2 lần ---
def get_unique_response(chat_id, response_pool):
    history = insult_history[chat_id]
    
    # Lọc ra các câu trong kho mà chưa xuất hiện quá 2 lần gần đây
    available_choices = [res for res in response_pool if history.count(res) < 2]
    
    # Nếu xui xẻo dùng hết kho thì reset bộ nhớ của nhóm đó để dùng lại từ đầu
    if not available_choices:
        insult_history[chat_id] = []
        available_choices = response_pool
        
    chosen_res = random.choice(available_choices)
    
    # Lưu vào lịch sử và giới hạn ghi nhớ 10 câu gần nhất để tiết kiệm RAM
    insult_history[chat_id].append(chosen_res)
    if len(insult_history[chat_id]) > 10:
        insult_history[chat_id].pop(0)
        
    return chosen_res

# --- 1. Lệnh /start công khai ---
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(text="👋 Chào mừng đến với Gs_bot! Gõ lệnh /menu để xem danh sách tính năng.")

# --- 2. Lệnh /menu hiển thị văn bản ---
async def show_menu(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not is_group_allowed(update):
        return
        
    menu_text = (
        "📜 **DANH SÁCH TOÀN BỘ LỆNH CỦA GS_BOT**\n\n"
        "👑 **Quyền hạn của Chủ sở hữu (Owner):**\n"
        "• `/chophep` (Reply): Cấp quyền điều khiển bot cho thành viên.\n"
        "• `/kochophep` (Reply): Tước quyền điều khiển bot của thành viên.\n\n"
        "🛠️ **Quyền hạn của Owner & Người được cho phép (Sudo):**\n"
        "• `/add`: Kích hoạt cho phép bot hoạt động tại nhóm hiện tại.\n"
        "• `/cc`: Hủy kích hoạt, bắt bot im lặng hoàn toàn.\n"
        "• `/onchat`: Bật chế độ trò chuyện/chửi bới tự động.\n"
        "• `/offchat`: Tắt chế độ trò chuyện (bot đi ngủ, chỉ nhận lệnh).\n"
        "• `/autod`: Bật chế độ đồ sát (xóa ngay lập tức mọi tin nhắn của đứa bị rep).\n"
        "• `/autof`: Tắt chế độ đồ sát khóa mõm, quay về võ mồm.\n"
        "• `/upadm` (Reply): Nâng thành viên được phản hồi lên làm Admin nhóm.\n"
        "• `/sos` (Reply): Hạ quyền Admin của thành viên xuống người thường.\n\n"
        "💬 **Lệnh công khai:**\n"
        "• `/start`: Khởi động lời chào của bot.\n"
        "• `/menu`: Hiển thị bảng danh sách lệnh này."
    )
    await update.message.reply_text(text=menu_text, parse_mode="Markdown")
# --- 3. Cấp/Hủy quyền bằng /chophep và /kochophep ---
async def grant_permission(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.effective_user.id != OWNER_ID: return
    if not update.message.reply_to_message:
        await update.message.reply_text("❌ Bạn phải reply tin nhắn của người muốn cho phép!")
        return
    target_id = update.message.reply_to_message.from_user.id
    target_name = update.message.reply_to_message.from_user.first_name
    sudo_users.add(target_id)
    save_ids(SUDO_FILE, sudo_users)
    await update.message.reply_text(f"✅ Đã cấp quyền điều khiển bot cho {target_name}.")

async def revoke_permission(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.effective_user.id != OWNER_ID: return
    if not update.message.reply_to_message:
        await update.message.reply_text("❌ Bạn phải reply tin nhắn của người muốn hủy cho phép!")
        return
    target_id = update.message.reply_to_message.from_user.id
    target_name = update.message.reply_to_message.from_user.first_name
    if target_id in sudo_users:
        sudo_users.remove(target_id)
        save_ids(SUDO_FILE, sudo_users)
        await update.message.reply_text(f"❌ Đã tước quyền điều khiển bot của {target_name}.")

# --- 4. Quản lý trạng thái Chat và Tự động xóa (Autodelete) ---
async def on_chat(update: Update, context: ContextTypes.DEFAULT_TYPE):
    global bot_chat_enabled
    if not has_permission(update.effective_user.id) or not is_group_allowed(update): return
    bot_chat_enabled = True
    await update.message.reply_text("🗣️ Chế độ bố láo đã BẬT. Sủa đi các em!")

async def off_chat(update: Update, context: ContextTypes.DEFAULT_TYPE):
    global bot_chat_enabled
    if not has_permission(update.effective_user.id) or not is_group_allowed(update): return
    bot_chat_enabled = False
    await update.message.reply_text("🤫 Chế độ bố láo đã TẮT. Bot tạm thời đi ngủ.")

async def autod_on(update: Update, context: ContextTypes.DEFAULT_TYPE):
    global autodelete_enabled
    if not has_permission(update.effective_user.id) or not is_group_allowed(update): return
    autodelete_enabled = True
    await update.message.reply_text("💀 Chế độ ĐỒ SÁT đã BẬT. Đứa nào bị rep mà mở mồm ra là tao xóa bài lập tức!")

async def autod_off(update: Update, context: ContextTypes.DEFAULT_TYPE):
    global autodelete_enabled
    if not has_permission(update.effective_user.id) or not is_group_allowed(update): return
    autodelete_enabled = False
    await update.message.reply_text("🕊️ Chế độ đồ sát đã TẮT. Tha bổng cho chúng mày quay về đấu võ mồm.")

# --- 5. Quản lý nhóm (/add, /cc) ---
async def add_group(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not has_permission(update.effective_user.id): return
    chat_id = update.effective_chat.id
    if chat_id not in allowed_groups:
        allowed_groups.add(chat_id)
        save_ids(DB_FILE, allowed_groups)
        await update.message.reply_text("✅ Box này dùng được bot rồi đấy.")

async def remove_group(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not has_permission(update.effective_user.id): return
    chat_id = update.effective_chat.id
    if chat_id in allowed_groups:
        allowed_groups.remove(chat_id)
        save_ids(DB_FILE, allowed_groups)
        await update.message.reply_text("⚠️ Đã cấm box này sử dụng bot.")

# --- 6. Lệnh nâng/hạ Admin (/upadm, /sos) ---
async def up_admin(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not has_permission(update.effective_user.id) or not is_group_allowed(update): return
    if not update.message.reply_to_message: return
    target_user = update.message.reply_to_message.from_user
    try:
        await context.bot.promote_chat_member(
            chat_id=update.effective_chat.id, user_id=target_user.id,
            can_manage_chat=True, can_delete_messages=True, can_manage_video_chats=True,
            can_restrict_members=True, can_promote_members=False, can_change_info=True, can_invite_users=True
        )
        await update.message.reply_text(f"✅ Đã nâng Admin cho {target_user.mention_html()}.", parse_mode="HTML")
    except Exception as e:
        await update.message.reply_text(f"❌ Lỗi: {e}")

async def down_admin(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not has_permission(update.effective_user.id) or not is_group_allowed(update): return
    if not update.message.reply_to_message: return
    target_user = update.message.reply_to_message.from_user
    try:
        await context.bot.promote_chat_member(
            chat_id=update.effective_chat.id, user_id=target_user.id,
            can_manage_chat=False, can_delete_messages=False, can_manage_video_chats=False,
            can_restrict_members=False, can_promote_members=False, can_change_info=False, can_invite_users=False
        )
        await update.message.reply_text(f"⚠️ Đã hạ Admin của {target_user.mention_html()} xuống thành viên thường.", parse_mode="HTML")
    except Exception as e:
        await update.message.reply_text(f"❌ Lỗi: {e}")

# --- 7. Bộ xử lý tin nhắn tinh vi ---
async def reply_chat(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not is_group_allowed(update): return

    chat_id = update.effective_chat.id
    user_id = update.effective_user.id
    name = update.effective_user.first_name

    # [XỬ LÝ ĐỒ SÁT]
    if autodelete_enabled and update.message.reply_to_message:
        if update.message.reply_to_message.from_user.id in [OWNER_ID, context.bot.id]:
            try:
                await update.message.delete()
                return  
            except Exception:
                pass

    if not bot_chat_enabled: return

    text = update.message.text.lower()

    chao_responses = [
        f"Chào cái cc gì mà chào, rảnh háng lắm à thằng vô tri {name}? Biến giùm cho rảnh mắt!",
        f"Lại gặp cái bản mặt đần độn của m rồi {name} ạ, nhìn thôi đã thấy vcl mệt mỏi.",
        "Sủa ít thôi, chào hỏi clg? Định làm thân với tao để xin tha à, mơ đi con trai!",
        f"Hi cc, tag tao làm cái đb gì thế hả {name}? Thừa calo thì đi chạy bộ đi bớt xàm lờ lại.",
        "Chào cc gì, thích ăn đấm hay thích ăn sút? Nói một câu để tao còn chuẩn bị combo vả rụng răng."
    ]

    bot_responses = [
        "Ré ré tên tao làm cái đb gì? Thèm ăn chửi đầu năm đến cuối năm đúng không?",
        "Tao đang bận ngủ, cút ngay trước khi tao sút bay cái hàm răng vẩu của mày ra!",
        "Gõ ít chữ thôi không bố mày cho bay màu khỏi box bây giờ, loại nít ranh tinh tướng.",
        "Lại chuẩn bị phát biểu mấy câu ngu học hỏi chấm đúng không? Đầu chỉ để mọc tóc à?",
        "Sủa nhanh đi con ranh để tao còn đi ngủ, nhìn cái dòng tin nhắn của mày đần vcl không chịu được."
    ]

    chui_responses = [
        "Mày chửi ai đấy thằng ranh con rụng răng? Thích war không tao chấp cả lò nhà mày vào đây cân một thể!",
        "Dcm mày thích thể hiện trình độ cào bàn phím à? Trông gầy gò ốm yếu mà sủa câu nào nghe thối câu đấy.",
        "Nít ranh mới nứt mắt ra tinh tướng, clg cũng lôi ra chửi được, đúng là loại thiếu giáo dục từ bé.",
        "Sủa tiếp đi thằng hề, tấu hài cho cả box xem chứ trình độ combat của mày phế vcl ra.",
        "Chửi thề cl, tao vả lệch quai hàm giờ chứ lại bảo xui, bớt cái thói múa rìu qua mắt thợ đi con.",
        "Gớm, mở mồm ra là dcm với vcl, vô học nó ngấm vào máu rồi nên phát ngôn nghe bẩn hết cả lỗ tai."
    ]

    random_responses = [
        "Nói cái clg thế không biết? Phát ngôn một câu nghe đần độn không ngửi nổi.",
        "Nín giùm cái, đọc tin nhắn của mày nhức hết cả mắt, tốn tài nguyên mạng vcl.",
        "Tao thấy mày càng nói càng xàm lờ rồi đấy, tắt văn nghệ đi ngủ đi con trai.",
        "Gớm, tinh tướng thế là cùng, ra đường gặp người thật chắc không dám ho một tiếng.",
        "Bớt sủa xàm đi con trai, nói câu nào là bộc lộ cái sự thiếu hiểu biết câu đấy.",
        "Phát biểu một câu nghe đần vcl, đúng là bộ não chưa qua trường lớp tiến hóa nào."
    ]

    if any(keyword in text for keyword in ["chào", "hi", "hello"]):
        await update.message.reply_text(get_unique_response(chat_id, chao_responses))
    elif "bot" in text:
        await update.message.reply_text(get_unique_response(chat_id, bot_responses))
    elif any(keyword in text for keyword in ["cl", "cc", "vcl", "dcm", "đb", "ngu", "chửi", "đm"]):
        await update.message.reply_text(get_unique_response(chat_id, chui_responses))
    else:
        if random.random() < 0.3:  
            await update.message.reply_text(get_unique_response(chat_id, random_responses))

def main():
    app = Application.builder().token(TOKEN).build()

    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("menu", show_menu))

    app.add_handler(CommandHandler("add", add_group))
    app.add_handler(CommandHandler("cc", remove_group))
    app.add_handler(CommandHandler("upadm", up_admin))
    app.add_handler(CommandHandler("sos", down_admin))
    app.add_handler(CommandHandler("onchat", on_chat))
    app.add_handler(CommandHandler("offchat", off_chat))
    app.add_handler(CommandHandler("autod", autod_on))
    app.add_handler(CommandHandler("autof", autod_off))
    app.add_handler(CommandHandler("chophep", grant_permission))
    app.add_handler(CommandHandler("kochophep", revoke_permission))
    
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, reply_chat))

    print("Gs_bot siêu cấp combat đã cập nhật TOKEN mới và đang khởi chạy...")
    app.run_polling()

if __name__ == '__main__':
    main()
