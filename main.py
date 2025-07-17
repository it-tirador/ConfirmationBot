import json
import os
import logging
import requests

from dotenv import load_dotenv

load_dotenv(override=True)
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S",
    filename="app.log",
    filemode="w",
    encoding="utf-8"
)

def send_telegram_message(text: str):
    """
    Отправляет сообщение в Telegram-группу с помощью бота.
    """
    token = os.getenv("BOT_TOKEN")
    chat_id = os.getenv("BOT_CHAT_ID")
    thread_id = os.getenv("BOT_THREAD_ID")
    url = f"https://api.telegram.org/bot{token}/sendMessage"
    data = {
        "chat_id": chat_id,
        "text": text,
        "parse_mode": "HTML"
    }
    if thread_id:
        data["message_thread_id"] = thread_id
    try:
        resp = requests.post(url, data=data)
        resp.raise_for_status()
        logging.info("Сообщение отправлено в Telegram.")
    except Exception as e:
        logging.error(f"Ошибка отправки сообщения в Telegram: {e}")

def get_config(json_file: str="config.json") -> dict | None:
    """
    Загружает конфигурацию из JSON-файла.
    """
    try:
        with open(json_file, "r") as f:
            config = json.load(f)
        logging.info("Конфиг успешно загружен.")
        return config
    except Exception as e:
        logging.error(f"Ошибка загрузки конфига: {e}")
        send_telegram_message(f"❌ Ошибка подтверждения\n📎<b>Ошибка:</b><i>{e}</i>")
        return None


def init_session(config: dict) -> requests.Session | None:
    """
    Инициализирует сессию для работы с сайтом.
    """
    try:
        session = requests.Session()
        session.get(config["base_url"])
        logging.info("Сессия инициализирована.")
        return session
    except Exception as e:
        logging.error(f"Ошибка инициализации сессии: {e}")
        send_telegram_message(f"❌ Ошибка подтверждения\n📎<b>Ошибка:</b><i>{e}</i>")
        return None


def authorize(session: requests.Session) -> bool:
    """
    Авторизуется на сайте.
    """
    try:
        payload = {
            "login": os.getenv("LOGIN"),
            "password": os.getenv("PASSWORD"),
            "save_password": "on",
        }
        response = session.post("https://abstd.ru/auth-ajax_login", data=payload)
        response.raise_for_status()
        logging.info("Авторизация прошла успешно.")
        if response.json().get("errors"):
            logging.error(f"Ошибка авторизации: {response.json()['errors']}")
            send_telegram_message(f"❌ Ошибка подтверждения\n📎<b>Ошибка:</b><i>{response.json()['errors']}</i>")
            return False
        return True
    except Exception as e:
        logging.error(f"Ошибка авторизации: {e}")
        send_telegram_message(f"❌ Ошибка подтверждения\n📎<b>Ошибка:</b><i>{e}</i>")
        return False


def upload_file(session: requests.Session, config: dict) -> str | None:
    """
    Загружает файл подтверждения заказа на сайт.
    """
    url = "https://abstd.ru/supplier_answer-load_answer_file"
    file_path = config["confirmation_file_path"]
    try:
        with open(file_path, "rb") as f:
            files = {
                "order_answer_file": (file_path, f, "application/vnd.ms-excel")
            }
            upload_response = session.post(url, files=files)
            upload_response.raise_for_status()
        logging.info("Файл подтверждения успешно загружен.")
        upload_data = upload_response.json()
        return upload_data["data"]["file_name"]
    except Exception as e:
        logging.error(f"Ошибка загрузки файла: {e}")
        send_telegram_message(f"❌ Ошибка подтверждения\n📎<b>Ошибка:</b><i>{e}</i>")
        return None


def process_file(session: requests.Session, file_name: str, file_path: str) -> None:
    """
    Обрабатывает файл подтверждения заказа на сайте.
    """
    proc_url = "https://abstd.ru/supplier_answer-proc_answer_file"
    proc_data = {
        "order_id_col": 1,  # номер колонки для "№ заказа клиента"
        "quantity_col": 5,  # номер колонки для "Количество"
        "order_product_id_col": 8,  # номер колонки для "Код позиции"
        "file_name": file_name,
        "cancel_reason": "",
        "dataType": "json"
    }
    try:
        proc_response = session.post(proc_url, data=proc_data)
        proc_response.raise_for_status()
        try:
            resp_obj = proc_response.json()
            pretty = json.dumps(resp_obj, ensure_ascii=False, indent=2)
            logging.info(f"Ответ сервера:\n{pretty}")
            # Проверяем успешность по статусу
            if str(resp_obj.get("status_code")) == "0":
                fname = os.path.basename(file_path)
                send_telegram_message(f"✅ Подтверждение отправлено\n📎<b>Файл:</b><i>{fname}</i>")
            else:
                send_telegram_message(f"❌ Ошибка подтверждения\n📎<b>Ошибка:</b><i>{resp_obj.get('err_msg', resp_obj)}</i>")
        except Exception:
            logging.info(proc_response.text)
            send_telegram_message(f"❌ Ошибка подтверждения\n📎<b>Ошибка:</b><i>{proc_response.text}</i>")
        print(proc_response.text)
    except Exception as e:
        logging.error(f"Ошибка при обработке файла: {e}")
        send_telegram_message(f"❌ Ошибка подтверждения\n📎<b>Ошибка:</b><i>{e}</i>")

def main():
    config = get_config()
    if not config:
        return
    session = init_session(config)
    if not session:
        return
    if not authorize(session):
        return
    file_name = upload_file(session, config)
    if not file_name:
        return
    process_file(session, file_name, config["confirmation_file_path"])

if __name__ == "__main__":
    main()