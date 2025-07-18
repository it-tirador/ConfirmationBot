import json
import os
import logging
import requests
import sys
import argparse

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
    Args:
        json_file: str
    Returns:
        dict | None: Конфигурация или None в случае ошибки
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
    Args:
        config: dict
    Returns:
        requests.Session | None: Сессия или None в случае ошибки
    """
    try:
        session = requests.Session()
        session.get(os.getenv("BASE_URL"))
        logging.info("Сессия инициализирована.")
        return session
    except Exception as e:
        logging.error(f"Ошибка инициализации сессии: {e}")
        send_telegram_message(f"❌ Ошибка подтверждения\n📎<b>Ошибка:</b><i>{e}</i>")
        return None



def authorize(session: requests.Session) -> bool:
    """
    Авторизуется на сайте.
    Args:
        session: requests.Session
    Returns:
        bool: True если авторизация прошла успешно, False в противном случае
    """
    try:
        payload = {
            "login": os.getenv("LOGIN"),
            "password": os.getenv("PASSWORD"),
            "save_password": "on",
        }
        response = session.post(os.path.join(os.getenv("BASE_URL"), "auth-ajax_login"), data=payload)
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



def upload_file(session: requests.Session, config: dict, file_path: str) -> str | None:
    """
    Загружает файл подтверждения заказа на сайт.
    Args:
        session: requests.Session
        config: dict
        file_path: str
    Returns:
        str | None: Имя загруженного файла или None в случае ошибки
    """
    url = os.path.join(os.getenv("BASE_URL"), "supplier_answer-load_answer_file")
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



def process_file(session: requests.Session, file_name: str, file_path: str, config: dict) -> None:
    """
    Обрабатывает файл подтверждения заказа на сайте.
    Args:
        session: requests.Session
        file_name: str
        file_path: str
        config: dict
    """
    proc_url = os.path.join(os.getenv("BASE_URL"), "supplier_answer-proc_answer_file")
    proc_data = {
        "order_id_col": config["order_id_col"],  # номер колонки для "№ заказа клиента"
        "quantity_col": config["quantity_col"],  # номер колонки для "Количество"
        "order_product_id_col": config["order_product_id_col"],  # номер колонки для "Код позиции"
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
    # Настройка парсера аргументов
    parser = argparse.ArgumentParser(
        description='Загрузка подтверждения заказа',
        epilog='Пример: python main.py "C:\\path\\to\\file.xls"'
    )
    parser.add_argument(
        'file_path', 
        nargs='?',
        help='Путь к файлу подтверждения заказа (.xls)'
    )
    
    args = parser.parse_args()
    
    config = get_config()
    if not config:
        return
    
    # Гибридный подход: аргумент командной строки или config
    if args.file_path:
        file_path = args.file_path
        logging.info(f"Используется файл из аргумента командной строки: {file_path}")
    else:
        if "confirmation_file_path" not in config:
            error_msg = "Не указан путь к файлу подтверждения ни в аргументах командной строки, ни в config.json"
            logging.error(error_msg)
            send_telegram_message(f"❌ Ошибка подтверждения\n📎<b>Ошибка:</b><i>{error_msg}</i>")
            return
        file_path = config["confirmation_file_path"]
        logging.info(f"Используется файл из конфига: {file_path}")
    
    session = init_session(config)
    if not session:
        return
    if not authorize(session):
        return
    file_name = upload_file(session, config, file_path)
    if not file_name:
        return
    process_file(session, file_name, file_path, config)



if __name__ == "__main__":
    main()