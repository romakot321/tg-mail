import redis
from dataclasses import dataclass
import datetime as dt
import threading
import json
import telebot
from telebot import types
import time
import os
from db import DBService


@dataclass
class Mail:
    sender: str
    subject: str
    date: dt.datetime
    attachment: list[str]
    text: str | None = None
    html: str | None = None


_sender_to_app = {
    "klinknerramaya929569@gmail.com": "028 SeaArt AI",
    "hadolmanis436@gmail.com": "039 music ai",
    "auroritaquint@gmail.com": "032 Pika + txt2video",
    "carlitacipriani253@gmail.com": "046 Video ai",
    "nhflatjscuba25687@gmail.com": "035 Ai video generator",
    "bpuzjb442bpuzjbl@gmail.com": "029 pika + pixverse",
    "sofia8234307@gmail.com": "034 PixVerse",
    "brianlppopichak1842@gmail.com": "026 PixVerse",
    "waddupsnordmark@gmail.com": "1176 Sora&Hug: AI Video Generator",
    "erbolatttsaliev12@yandex.kz": "031 PixVerse",
    "ismalekberr443@outlook.com": "019 Pika app",
    "mcbayroxane@gmail.com": "017 Pika art"
}


class BotWorker:
    BOT_TOKEN = os.getenv("BOT_TOKEN")
    ACCESS_TOKEN = os.getenv("ACCESS_TOKEN", "123")
    BOT_WEBAPP_URL = os.getenv("BOT_WEBAPP_URL")
    REDIS_CHANNEL_NAME = "channel_mails"

    def __init__(
            self,
            db_service: DBService,
            redis_connection: redis.Redis | None = None,
            is_poller = False,
            is_sender = True
    ):
        self.bot = telebot.TeleBot(self.BOT_TOKEN)
        self.db_service = db_service
        self.running = True
        if is_poller:
            self.thread = threading.Thread(target=self.bot.infinity_polling)
        elif is_sender:
            self.thread = threading.Thread(target=self._listen)

        if redis_connection:
            self.conn = redis_connection.pubsub()
            self.conn.subscribe(self.REDIS_CHANNEL_NAME)
        self.bot.register_message_handler(self._handle_add_chat, commands=['start'])

    def send_to_chats(self, text: str, mail_id: int):
        keyboard = self._build_mail_button(mail_id)
        for chat_id in self.db_service.list_chats_ids():
            self.bot.send_message(chat_id, text, reply_markup=keyboard)

    def _build_mail_button(self, mail_id: int):
        keyboard = types.InlineKeyboardMarkup(row_width=1)
        webapp = types.WebAppInfo(self.BOT_WEBAPP_URL + "/mail/" + str(mail_id))
        keyboard.add(types.InlineKeyboardButton(text="Просмотреть письмо", web_app=webapp))
        return keyboard

    def _process_mail(self, mail: Mail):
        app = _sender_to_app.get(mail.sender, "Неизвестно")
        text = f"""
            Пришло новое письмо:
            Отправитель: {mail.sender}
            Приложение: {app}
            Тема: {mail.subject}
            Время: {mail.date}
            Текст: {mail.text}
        """[:3500]
        mail_id = self.db_service.add_mail(mail.sender, mail.date, mail.text, mail.html)
        self.send_to_chats(text, mail_id)

    def _parse_mail(self, raw: str) -> Mail | None:
        data = raw.get('data')
        if data is None or not isinstance(data, str):
            return
        return Mail(**json.loads(data))

    def _listen(self):
        while self.running:
            time.sleep(0.01)
            message = self.conn.get_message()
            if not message:
                continue
            mail = self._parse_mail(message);
            if mail:
                self._process_mail(mail)

    def start(self):
        self.thread.start()

    def stop(self):
        self.running = False

    def _handle_add_chat(self, message):
        print("Message from", message.from_user.id, message.chat.id, ":", message.text)
        token = message.text.split()
        if self.ACCESS_TOKEN not in token:
            self.bot.send_message(message.chat.id, "Неверный ключ доступа")
            return
        self.db_service.add_chat_id(message.chat.id)
        self.bot.send_message(message.chat.id, "Вы подписались на уведомления о письмах")

