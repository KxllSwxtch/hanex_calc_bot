import time
import requests
import os
import re
from urllib.parse import urlparse, parse_qs
from dotenv import load_dotenv
from selenium import webdriver
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.common.by import By
from selenium.webdriver.chrome.options import Options
from selenium.common.exceptions import NoSuchElementException

load_dotenv()

CAPSOLVER_API_KEY = os.getenv("CAPSOLVER_API_KEY")
SITE_KEY = os.getenv("SITE_KEY")
CHROMEDRIVER_PATH = "/opt/homebrew/bin/chromedriver"  # Укажите путь к chromedriver


def solve_recaptcha_v3(url):
    payload = {
        "clientKey": CAPSOLVER_API_KEY,
        "task": {
            "type": "ReCaptchaV3TaskProxyLess",
            "websiteKey": SITE_KEY,
            "websiteURL": url,
            "pageAction": "/dc/dc_cardetailview_do",
        },
    }
    res = requests.post("https://api.capsolver.com/createTask", json=payload)
    resp = res.json()
    task_id = resp.get("taskId")
    if not task_id:
        print("Не удалось создать задачу:", res.text)
        return None
    print(f"Получен taskId: {task_id} / Ожидание результата...")

    while True:
        time.sleep(1)
        payload = {"clientKey": CAPSOLVER_API_KEY, "taskId": task_id}
        res = requests.post("https://api.capsolver.com/getTaskResult", json=payload)
        resp = res.json()
        if resp.get("status") == "ready":
            print("reCAPTCHA успешно решена")
            return resp.get("solution", {}).get("gRecaptchaResponse")
        if resp.get("status") == "failed" or resp.get("errorId"):
            print("Решение не удалось! Ответ:", res.text)
            return None


def get_car_info(url):
    global car_id_external

    chrome_options = Options()
    chrome_options.add_argument("--headless")
    chrome_options.add_argument("--disable-infobars")
    chrome_options.add_argument("--disable-extensions")
    chrome_options.add_argument("--disable-blink-features=AutomationControlled")
    chrome_options.add_argument(
        "user-agent=Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/88.0.4324.150 Safari/537.36"
    )
    service = Service(CHROMEDRIVER_PATH)
    driver = webdriver.Chrome(service=service, options=chrome_options)

    try:
        driver.get(url)

        # Проверка на наличие reCAPTCHA
        if "reCAPTCHA" in driver.page_source:
            print("Обнаружена reCAPTCHA. Пытаемся решить...")
            recaptcha_response = solve_recaptcha_v3(url)
            if recaptcha_response:
                driver.execute_script(
                    f'document.getElementById("g-recaptcha-response").innerHTML = "{recaptcha_response}";'
                )
                driver.execute_script("document.forms[0].submit();")
                time.sleep(3)  # Подождем, пока страница загрузится после отправки формы
            else:
                print("Решение reCAPTCHA не удалось.")
                return None

        # Парсим URL для получения carid
        parsed_url = urlparse(url)
        query_params = parse_qs(parsed_url.query)
        car_id = query_params.get("carid", [None])[0]
        car_id_external = car_id

        # Инициализация переменных для информации о машине
        car_date = ""
        car_engine_capacity = ""
        car_price = ""

        # Проверка элемента product_left
        try:
            product_left = driver.find_element(By.CLASS_NAME, "product_left")
            product_left_splitted = product_left.text.split("\n")

            car_date = product_left_splitted[3]
            car_engine_capacity = product_left_splitted[6]
            car_price = re.sub(r"\D", "", product_left_splitted[1])

            formatted_price = car_price.replace(",", "")
            formatted_engine_capacity = car_engine_capacity.replace(",", "")[0:-2]
            cleaned_date = "".join(filter(str.isdigit, car_date))
            formatted_date = f"01{cleaned_date[2:4]}{cleaned_date[:2]}"

            # Создание URL для передачи данных
            new_url = f"https://plugin-back-versusm.amvera.io/car-ab-korea/{car_id}?price={formatted_price}&date={formatted_date}&volume={formatted_engine_capacity}"
            return new_url

        except NoSuchElementException:
            print("Элемент product_left не найден. Переходим к gallery_photo.")

            try:
                gallery_element = driver.find_element(
                    By.CSS_SELECTOR, "div.gallery_photo"
                )
                items = gallery_element.find_elements(By.XPATH, ".//*")

                for index, item in enumerate(items):
                    if index == 10:
                        car_date = item.text
                    if index == 18:
                        car_engine_capacity = item.text

                try:
                    keyinfo_element = driver.find_element(
                        By.CSS_SELECTOR, "div.wrap_keyinfo"
                    )
                    keyinfo_items = keyinfo_element.find_elements(By.XPATH, ".//*")
                    keyinfo_texts = [
                        item.text for item in keyinfo_items if item.text.strip() != ""
                    ]

                    for index, info in enumerate(keyinfo_texts):
                        if index == 12:
                            car_price = re.sub(r"\D", "", info)
                except NoSuchElementException:
                    print("Элемент wrap_keyinfo не найден.")
            except NoSuchElementException:
                print("Элемент gallery_photo также не найден.")

        # Форматирование значений для URL
        formatted_price = car_price.replace(",", "")
        formatted_engine_capacity = car_engine_capacity.replace(",", "")[0:-2]
        cleaned_date = "".join(filter(str.isdigit, car_date))
        formatted_date = f"01{cleaned_date[2:4]}{cleaned_date[:2]}"

        # Конечный URL
        new_url = f"https://plugin-back-versusm.amvera.io/car-ab-korea/{car_id}?price={formatted_price}&date={formatted_date}&volume={formatted_engine_capacity}"

        return new_url

    except Exception as e:
        print(f"Произошла ошибка: {e}")
        return None

    finally:
        driver.quit()


# Вызов функции

cars = [
    "http://www.encar.com/dc/dc_cardetailview.do?pageid=fc_carsearch&listAdvType=normal&carid=37864643&view_type=hs_ad&adv_attribute=hs_ad&wtClick_forList=019&advClickPosition=imp_normal_p1_g1&tempht_arg=1ZQ3jgI8g0x9_0",
    "http://www.encar.com/dc/dc_cardetailview.do?pageid=dc_carsearch&carid=37952680",
    "http://www.encar.com",
    "http://www.encar.com/dc/dc_cardetailview.do?pageid=fc_carsearch&listAdvType=pic&carid=37976575&view_type=normal&wtClick_forList=033&advClickPosition=imp_pic_p1_g2",
    "http://www.encar.com/dc/dc_cardetailview.do?pageid=fc_carsearch&listAdvType=pic&carid=37740834&view_type=normal&wtClick_forList=033&advClickPosition=imp_pic_p1_g8",
]

for i in range(len(cars) - 1):
    car = cars[i]
    print(f"Тестим ссылку {i+1}")
    result_url = get_car_info(car)
    if result_url:
        print(result_url)
