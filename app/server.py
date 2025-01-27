from flask import Flask, send_file
from mail import MailService
from db import DBService
import io
import dataclasses
import threading
import time
import json


class ServerWorker:
    REDIS_CHANNEL_NAME = "channel_mails"

    def __init__(self, redis_connection, mail_service: MailService, db_service: DBService):
        self.redis_connection = redis_connection
        self.mail_service = mail_service
        self.db_service = db_service

        self.application = Flask(__name__)
        self.register()
        self.mails_reader_thread = threading.Thread(target=self.check_for_mails)

    def register(self):
        @self.application.route('/mail/<mail_id>')
        def handle_mail_show(mail_id: int):
            mail = self.db_service.get_mail(mail_id)
            html = mail.get("html", "").encode()
            if not html:
                html = f'<p style="font-size: 1rem;">{html.get("text", "Письмо не содержит текст")}</p>'
            return send_file(io.BytesIO(html), mimetype='text/html')

    def send_mails(self, mails):
        for mail in mails:
            raw = json.dumps(dataclasses.asdict(mail))
            self.redis_connection.publish(self.REDIS_CHANNEL_NAME, raw)


    def check_for_mails(self):
        while True:
            time.sleep(5)
            mails = self.mail_service.get_new_mails()
            if not mails:
                continue
            self.send_mails(mails)

    def start(self):
        self.mails_reader_thread.start()
        self.application.run(host="0.0.0.0")

