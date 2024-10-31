import time
import pickle
import os
import re
from selenium import webdriver
from selenium.common.exceptions import NoSuchElementException
from selenium.webdriver.common.by import By
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.chrome.options import Options
from urllib.parse import urlparse, parse_qs

# CapSolver API key
CAPSOLVER_API_KEY = os.getenv("CAPSOLVER_API_KEY")  # Замените на ваш API-ключ CapSolver
SITE_KEY = os.getenv("SITE_KEY")
CHROMEDRIVER_PATH = "/opt/homebrew/bin/chromedriver"  # Укажите путь к chromedriver


def simulate_recaptcha():
    print("Имитация решения reCAPTCHA...")
    # Симуляция решения reCAPTCHA
    return "simulated_recaptcha_response"


def test_get_car_info(url):
    chrome_options = Options()

    # TODO : UNCOMMENT
    # chrome_options.add_argument("--headless")

    chrome_options.add_argument("user-data-dir=./profile")  # Путь к папке профиля
    chrome_options.add_argument("--disable-infobars")
    chrome_options.add_argument("--disable-extensions")
    # chrome_options.add_argument("--disable-blink-features=AutomationControlled")
    chrome_options.add_argument(
        "user-agent=Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/88.0.4324.150 Safari/537.36"
    )
    service = Service(CHROMEDRIVER_PATH)
    driver = webdriver.Chrome(service=service, options=chrome_options)

    try:
        driver.delete_all_cookies()  # Очистка всех куков перед каждым запросом

        driver.get(url)

        time.sleep(5)  # Задержка для проверки страницы

        # Проверка на наличие reCAPTCHA
        if "reCAPTCHA" in driver.page_source:
            print("Обнаружена reCAPTCHA. Пытаемся решить...")
            # Используем симуляцию вместо реального вызова
            recaptcha_response = simulate_recaptcha()
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

        # Инициализация переменных для информации о машине
        car_title = ""
        car_date = ""
        car_engine_capacity = ""
        car_price = ""

        # Проверка элемента product_left
        try:
            product_left = driver.find_element(By.CLASS_NAME, "product_left")
            product_left_splitted = product_left.text.split("\n")

            prod_name = product_left.find_element(By.CLASS_NAME, "prod_name")

            car_title = prod_name.text.strip()
            car_date = product_left_splitted[3]
            car_engine_capacity = product_left_splitted[6]
            car_price = re.sub(r"\D", "", product_left_splitted[1])

            formatted_price = car_price.replace(",", "")
            formatted_engine_capacity = car_engine_capacity.replace(",", "")[0:-2]
            cleaned_date = "".join(filter(str.isdigit, car_date))
            formatted_date = f"01{cleaned_date[2:4]}{cleaned_date[:2]}"

            # Создание URL для передачи данных
            new_url = f"https://plugin-back-versusm.amvera.io/car-ab-korea/{car_id}?price={formatted_price}&date={formatted_date}&volume={formatted_engine_capacity}"
            return [new_url, car_title]

        except NoSuchElementException:
            print("Элемент product_left не найден. Переходим к gallery_photo.")

            try:
                gallery_element = driver.find_element(
                    By.CSS_SELECTOR, "div.gallery_photo"
                )
                prod_name = gallery_element.find_element(By.CLASS_NAME, "prod_name")
                car_title = prod_name.text

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

        return [new_url, car_title]

    except Exception as e:
        print(f"Произошла ошибка: {e}")
        return None

    finally:
        driver.quit()


if __name__ == "__main__":
    print(
        test_get_car_info(
            "http://www.encar.com/dc/dc_cardetailview.do?pageid=fc_carsearch&carid=37999442"
        )
    )
