import os
import re
import json
import random
import telebot
import pypdf
from groq import Groq
from telebot.types import InlineKeyboardMarkup, InlineKeyboardButton

# 1. Инициализация
TOKEN = os.environ.get("TELEGRAM_TOKEN")
GROQ_API_KEY = os.environ.get("GROQ_API_KEY")
PDF_FILE = "Қазақстан тарихы (база).pdf"

bot = telebot.TeleBot(TOKEN)
client = Groq(api_key=GROQ_API_KEY)

# 2. Парсинг PDF
def load_db():
    reader = pypdf.PdfReader(PDF_FILE)
    text = "\n".join([page.extract_text() for page in reader.pages if page.extract_text()])
    blocks = re.findall(r'(\d+)\.\s*(.*?)(?=\n\s*\d+\.|$)', text, re.DOTALL)
    return [{"id": i, "q": b[1].split('.')[0].strip(), "a": b[1].split('.')[-1].strip()} for i, b in enumerate(blocks)]

db = load_db()

# 3. ИИ генерирует "вредные" варианты
def get_options(correct_answer, question):
    prompt = f"Сұрақ: {question}. Дұрыс жауап: {correct_answer}. 3 қате, бірақ логикалық жауап ойлап тап. Формат: қате1|қате2|қате3"
    try:
        chat_completion = client.chat.completions.create(
            messages=[{"role": "user", "content": prompt}],
            model="llama3-8b-8192",
        )
        wrongs = chat_completion.choices[0].message.content.split('|')
        options = [correct_answer] + [w.strip() for w in wrongs[:3]]
    except:
        options = [correct_answer, "Білмеймін", "Тарихқа қатысы жоқ", "Қате нұсқа"]
    random.shuffle(options)
    return options

# 4. Обработчик команд
@bot.message_handler(commands=['start', 'quiz'])
def send_quiz(message):
    q = random.choice(db)
    options = get_options(q['a'], q['q'])
    markup = InlineKeyboardMarkup()
    for opt in options:
        markup.add(InlineKeyboardButton(opt, callback_data=f"ans_{opt}_{q['a']}"))
    bot.send_message(message.chat.id, f"❓ {q['q']}", reply_markup=markup)

@bot.callback_query_handler(func=lambda call: True)
def check_answer(call):
    user_ans, correct = call.data.split("_")[1], call.data.split("_")[2]
    result = "🎉 Дұрыс!" if user_ans == correct else f"😔 Қате. Дұрыс жауап: {correct}"
    bot.edit_message_text(f"{call.message.text}\n\n{result}", call.message.chat.id, call.message.message_id)

print("Бот запущен!")
bot.infinity_polling()
