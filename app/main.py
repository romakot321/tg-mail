from bot import BotWorker
from mail import MailService
from db import DBService
from server import ServerWorker
import redis
import os
import time
import json
import dataclasses

REDIS_HOST = os.getenv("REDIS_HOST", "127.0.0.1")


def main():
    db_service = DBService()
    redis_connection = redis.Redis(host=REDIS_HOST, db=0, decode_responses=True)
    sender_bot_worker = BotWorker(db_service, redis_connection, is_poller=False, is_sender=True)
    poller_bot_worker = BotWorker(db_service, is_poller=True, is_sender=False)
    mail_service = MailService(redis_connection)
    server_worker = ServerWorker(redis_connection, mail_service, db_service)

    sender_bot_worker.start()
    poller_bot_worker.start()
    server_worker.start()


if __name__ == "__main__":
    main()

