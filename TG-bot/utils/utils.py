import httpx
from dotenv import load_dotenv
import os

load_dotenv()


async def send_audio_to_server(file_path: str):

    FASTAPI_URL = os.getenv("FASTAPI_URL")

    """Отправка голосового сообщения на сервер"""
    url = FASTAPI_URL + "/process_audio"
    
    # Открытие файла в бинарном режиме
    with open(file_path, "rb") as file:
        files = {"file": (file_path.split(".")[1].split("/")[-1] + ".wav", file, "audio/wav")}
        
        # Отправка POST-запроса с файлом
        async with httpx.AsyncClient() as client:
            response = await client.post(url, files=files)
            
            if response.status_code == 200:
                    try:
                        result = response.json()
                        print("Обработка завершена:", result)
                        return result
                    except Exception as e:
                        print("Ошибка обработки JSON:", str(e))
                        return {"error": "Ошибка обработки JSON"}
            else:
                print("Ошибка при отправке на сервер:", response.status_code)
                return {"error": f"Ошибка {response.status_code}"}


async def send_text_to_server(endpoint, text: str):
    FASTAPI_URL = os.getenv("FASTAPI_URL", "http://localhost:8000")  # Подставь реальный URL
    url = f"{FASTAPI_URL}/{endpoint}"

    async with httpx.AsyncClient() as client:
        try:
            response = await client.post(url, json={"text": text})
            response.raise_for_status()
            return response.json()
        except httpx.HTTPStatusError as e:
            print("Ошибка запроса:", e)
            return {"error": f"Ошибка {e.response.status_code}"}
        except Exception as e:
            print("Ошибка при обработке запроса:", str(e))
            return {"error": "Ошибка сервера"}

async def get_info(endpoint):
    FASTAPI_URL = os.getenv("FASTAPI_URL", "http://localhost:8000")  # Подставь реальный URL
    url = f"{FASTAPI_URL}/{endpoint}"

    async with httpx.AsyncClient() as client:
        try:
            response = await client.get(url)
            response.raise_for_status()
            return response.json()
        except httpx.HTTPStatusError as e:
            print("Ошибка запроса:", e)
            return {"error": f"Ошибка {e.response.status_code}"}
        except Exception as e:
            print("Ошибка при обработке запроса:", str(e))
            return {"error": "Ошибка сервера"}


def format_schedule(data: dict) -> str:
    """Форматирует данные в красивый текст"""
    text = "📍 *Информация о поликлинике:*\n\n"

    if data.get("phone"):
        text += f"📞 *Телефон:* `{data['phone']}`\n\n"

    for addr in data.get("addresses", []):
        text += f"🏥 *Адрес:* {addr['address']}\n"
        text += "🕒 *Диагностическая поликлиника:*\n"
        for sched in addr.get("diagnostic_schedule", []):
            text += f"   📅 {sched['days']}: {sched['hours']}\n"

        if addr.get("lab_schedule"):
            text += "🧪 *Бактериологическая лаборатория:*\n"
            for sched in addr["lab_schedule"]:
                text += f"   📅 {sched['days']}: {sched['hours']}\n"

        text += "\n"

    return text


import os
import httpx


async def get_categories(endpoint):
    FASTAPI_URL = os.getenv("FASTAPI_URL", "http://localhost:8000")  # Подставь реальный URL
    url = f"{FASTAPI_URL}/{endpoint}"
    secret = os.getenv("SECRET_KEY")
    headers = {
        "Authorization": f"Bearer {secret}"  # Добавляем заголовок авторизации
    }
    async with httpx.AsyncClient() as client:
        try:
            response = await client.get(url, headers=headers)
            response.raise_for_status()
            return response.json()
        except httpx.HTTPStatusError as e:
            print("Ошибка запроса:", e)
            return {"error": f"Ошибка {e.response.status_code}"}
        except Exception as e:
            print("Ошибка при обработке запроса:", str(e))
            return {"error": "Ошибка сервера"}

