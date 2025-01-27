import imaplib
import os
import email
from email.header import decode_header
from dataclasses import dataclass
import datetime as dt
import base64


@dataclass
class Mail:
    sender: str
    subject: str
    date: str
    attachment: list[str]
    text: str | None = None
    html: str | None = None


class MailService:
    MAIL_PASSWORD = os.getenv("MAIL_PASSWORD")
    MAIL_USERNAME = os.getenv("MAIL_USERNAME")
    MAIL_IMAP_SERVER = os.getenv("MAIL_IMAP_SERVER")

    def __init__(self, redis_connection):
        self.imap = imaplib.IMAP4_SSL(self.MAIL_IMAP_SERVER)
        self.redis_connection = redis_connection
        self._last_mail_uid = self._load_uid_tip()

        self.imap.login(self.MAIL_USERNAME, self.MAIL_PASSWORD)
        self.imap.select("INBOX")

    def _load_uid_tip(self) -> int:
        value = self.redis_connection.get("UID_TIP" + self.MAIL_USERNAME)
        return int(value) if value is not None else -1

    def _set_uid_tip(self, value: int):
        self.redis_connection.set("UID_TIP" + self.MAIL_USERNAME, str(value))

    def _parse_mail(self, msg) -> Mail:
        sender = msg["Return-path"]
        date = email.utils.parsedate_tz(msg["Date"])
        raw_subject = decode_header(msg["Subject"])
        subject = raw_subject[0][0]
        if isinstance(subject, bytes):
            subject = subject.decode(raw_subject[0][1])
        text = ""
        html = ""

        for part in msg.walk():
            if part.get_content_maintype() != 'text':
                continue
            if part.get_content_subtype() == 'plain':
                text += part.get_payload(decode=True).decode(part.get_content_charset())
            elif part.get_content_subtype() == 'html':
                html += part.get_payload(decode=True).decode(part.get_content_charset())

        return Mail(
            sender=sender,
            subject=subject,
            date=dt.datetime(*date[:-3]).isoformat(sep=" "),
            text=(text if text else None),
            html=(html if html else None),
            attachment=[]
        )

    def get_new_mails(self) -> list[Mail]:
        self.imap.select("INBOX", readonly=True)
        if self._last_mail_uid == -1:
            _, uids = self.imap.uid('search', 'UNSEEN', 'ALL')
            uids = uids[0].split(b' ')
            self._last_mail_uid = int(uids[-1].decode())
            self._set_uid_tip(self._last_mail_uid)
        else:
            _, uids = self.imap.uid('search', 'UNSEEN', 'UID ' + str(self._last_mail_uid) + ':*')

        if not uids or not uids[0]:
            print("No new messages")
            return []
        uids = list(map(lambda i: int(i.decode()), uids))

        left_index = len(uids) - 1
        for i in range(len(uids) - 1, 1, -1):
            if uids[i - 1] < self._last_mail_uid:
                left_index = i
                break

        for uid in uids[left_index:]:
            if uid < self._last_mail_uid:
                continue
            res, msg = self.imap.uid('fetch', str(uid), '(RFC822)')
            msg = email.message_from_bytes(msg[0][1])
            mail = self._parse_mail(msg)
        self._set_uid_tip(uids[-1])

        return [mail]


if __name__ == '__main__':
    service = MailService()
    mails = service.get_new_mails()
    for mail in mails:
        print("\n\n\n\n----NEW MAIL----")
        print("\tFrom:", mail.sender)
        print("\tSubject:", mail.subject)
        print("\tDate:", mail.date)
        print("\tText:", mail.text)
        print("\tHTML:", mail.html)

