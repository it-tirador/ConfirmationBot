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
        return None



def init_session(config: dict) -> requests.Session | None:
    """
    Инициализирует сессию для работы с API.
    """
    try:
        session = requests.Session()
        session.get(config["base_url"])
        logging.info("Сессия инициализирована.")
        return session
    except Exception as e:
        logging.error(f"Ошибка инициализации сессии: {e}")
        return None



def authorize(session: requests.Session) -> bool:
    """
    Авторизуется в API.
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
            return False
        return True
    except Exception as e:
        logging.error(f"Ошибка авторизации: {e}")
        return False



def upload_file(session: requests.Session, config: dict) -> str | None:
    """
    Загружает файл подтверждения заказа в API.
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
        return None



def process_file(session: requests.Session, file_name: str) -> None:
    """
    Обрабатывает файл подтверждения заказа в API.
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
        except Exception:
            logging.info(proc_response.text)
        print(proc_response.text)
    except Exception as e:
        logging.error(f"Ошибка при обработке файла: {e}")



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
    process_file(session, file_name)



if __name__ == "__main__":
    main()