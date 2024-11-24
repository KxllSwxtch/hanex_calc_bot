import time
import re
import requests
import logging

from twocaptcha import TwoCaptcha
from selenium import webdriver
from selenium.common.exceptions import NoSuchElementException
from selenium.webdriver.common.by import By
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.chrome.options import Options
from urllib.parse import urlparse, parse_qs
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC

CHROMEDRIVER_PATH = "/opt/homebrew/bin/chromedriver"
TWOCAPTCHA_API_KEY = "89a8f41a0641f085c8ca6e861e0fa571"
PROXY_HOST = "45.118.250.2"
PROXY_PORT = "8000"
PROXY_USER = "B01vby"
PROXY_PASS = "GBno0x"

http_proxy = f"http://{PROXY_USER}:{PROXY_PASS}@{PROXY_HOST}:{PROXY_PORT}"


def extract_sitekey(driver, url):
    """Извлекает sitekey из iframe на странице."""
    driver.get(url)  # Загружаем страницу
    iframe = driver.find_element(
        By.TAG_NAME, "iframe"
    )  # Находим iframe, содержащий reCAPTCHA
    iframe_src = iframe.get_attribute("src")  # Получаем src атрибут iframe

    # Ищем sitekey в src iframe
    match = re.search(r"k=([A-Za-z0-9_-]+)", iframe_src)
    if match:
        return match.group(1)
    else:
        raise Exception("Не удалось найти sitekey.")


def send_recaptcha_token(url, token, cookies=None, headers=None):
    """
    Отправляет reCAPTCHA токен через POST запрос на сервер.

    :param url: URL для отправки запроса
    :param token: Токен, полученный от reCAPTCHA
    :param cookies: Словарь с cookies (если необходимо)
    :param headers: Словарь с заголовками (если необходимо)
    :return: Ответ сервера в формате JSON
    """
    try:
        # Устанавливаем URL для reCAPTCHA обработки
        post_url = f"{url}/validation_recaptcha.do?method=v3"

        # Данные для POST-запроса
        payload = {"token": token}

        # Отправка POST-запроса
        response = requests.post(
            post_url, data=payload, cookies=cookies, headers=headers
        )

        # Проверка статуса ответа
        if response.status_code == 200:
            print("Запрос успешно отправлен.")
            return response.json()
        else:
            print(f"Ошибка запроса: {response.status_code}")
            print(f"Тело ответа: {response.text}")
            return None
    except Exception as e:
        print(f"Ошибка при отправке POST-запроса: {e}")
        return None


def solve_recaptcha(driver, url):
    """Решает reCAPTCHA, извлекая sitekey с помощью Selenium и TwoCaptcha."""
    try:
        # Извлекаем sitekey
        site_key = extract_sitekey(driver, url)
        print(f"Извлеченный sitekey: {site_key}")

        # Инициализация solver
        solver = TwoCaptcha(TWOCAPTCHA_API_KEY)

        # Решение reCAPTCHA
        result = solver.recaptcha(sitekey=site_key, url=url)
        print(f"reCAPTCHA решена: {result}")

        # Извлечение cookies из Selenium
        cookies = {cookie["name"]: cookie["value"] for cookie in driver.get_cookies()}

        # Установка заголовков (если необходимо)
        headers = {
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/115.0.0.0 Safari/537.36"
        }

        # Отправка reCAPTCHA токена через POST-запрос
        response = send_recaptcha_token(
            url, result["code"], cookies=cookies, headers=headers
        )

        # Проверка ответа
        if response and response.get("success"):
            print("reCAPTCHA успешно пройдена, перезагружаем страницу.")
            driver.refresh()  # Перезагрузка страницы для завершения процесса
        else:
            print("Не удалось пройти reCAPTCHA.")
    except Exception as e:
        logging.error(f"Ошибка при решении reCAPTCHA или отправке формы: {e}")


def get_car_info(url):
    global car_id_external

    chrome_options = Options()
    chrome_options.add_argument("--disable-gpu")
    chrome_options.add_argument("--no-sandbox")  # Необходим для работы в Heroku
    chrome_options.add_argument("--headless")  # Необходим для работы в Heroku
    chrome_options.add_argument("--disable-dev-shm-usage")  # Решает проблемы с памятью
    chrome_options.add_argument("--disable-software-rasterizer")
    chrome_options.add_argument("--disable-blink-features=AutomationControlled")
    chrome_options.add_argument("--disable-extensions")
    chrome_options.add_argument("--log-level=3")  # Отключение логов
    chrome_options.add_argument("--disable-application-cache")
    chrome_options.add_argument("--disable-web-security")
    chrome_options.add_argument("--allow-running-insecure-content")
    chrome_options.add_argument("--disable-autofill")
    chrome_options.add_argument(f"--proxy-server={http_proxy}")
    chrome_options.add_argument(
        "user-agent=Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/88.0.4324.150 Safari/537.36"
    )

    # Инициализация драйвера
    service = Service(CHROMEDRIVER_PATH)
    driver = webdriver.Chrome(
        service=service,
        options=chrome_options,
    )

    try:
        # Загружаем страницу
        driver.get(url)

        solve_recaptcha(driver, url)

        parsed_url = urlparse(url)
        query_params = parse_qs(parsed_url.query)
        car_id = query_params.get("carid", [None])[0]
        car_id_external = car_id

        ########
        # Проверка элемента areaLeaseRent
        ########
        try:
            print("Проверка на areaLeaseRent")
            lease_area = driver.find_element(By.ID, "areaLeaseRent")
            title_element = lease_area.find_element(By.CLASS_NAME, "title")

            if "리스정보" in title_element.text or "렌트정보" in title_element.text:
                print("Данная машина находится в лизинге.")
                return [
                    "",
                    "Данная машина находится в лизинге. Свяжитесь с менеджером.",
                ]
        except NoSuchElementException:
            print("Элемент areaLeaseRent не найден.")

        ########
        # Проверка элемента product_left
        ########
        try:
            print("Проверка на product_left")

            product_left = WebDriverWait(driver, 5).until(
                EC.visibility_of_element_located((By.CLASS_NAME, "product_left"))
            )
            product_left_splitted = product_left.text.split("\n")

            car_title = product_left.find_element(
                By.CLASS_NAME, "prod_name"
            ).text.strip()

            car_date = (
                product_left_splitted[3] if len(product_left_splitted) > 3 else ""
            )
            car_engine_capacity = (
                product_left_splitted[6] if len(product_left_splitted) > 6 else ""
            )
            car_price = re.sub(r"\D", "", product_left_splitted[1])

            # Форматирование
            formatted_price = car_price.replace(",", "")
            formatted_engine_capacity = (
                car_engine_capacity.replace(",", "")[:-2]
                if car_engine_capacity
                else "0"
            )
            cleaned_date = "".join(filter(str.isdigit, car_date))
            formatted_date = (
                f"01{cleaned_date[2:4]}{cleaned_date[:2]}" if cleaned_date else "010101"
            )

            # Создание URL
            new_url = f"https://plugin-back-versusm.amvera.io/car-ab-korea/{car_id}?price={formatted_price}&date={formatted_date}&volume={formatted_engine_capacity}"

            print(f"Данные о машине получены: {new_url}, {car_title}")

            return [new_url, car_title]
        except NoSuchElementException:
            print("Элемент product_left не найден, переходим к поиску gallery_photo")
        except Exception as e:
            print(f"Ошибка при обработке product_left: {e}")

        ########
        # Проверка элемента gallery_photo
        ########
        try:
            print("Проверка на gallery_photo")

            gallery_element = driver.find_element(By.CSS_SELECTOR, "div.gallery_photo")
            car_title = gallery_element.find_element(By.CLASS_NAME, "prod_name").text
            items = gallery_element.find_elements(By.XPATH, ".//*")

            if len(items) > 10:
                car_date = items[10].text
            if len(items) > 18:
                car_engine_capacity = items[18].text

            # Извлечение информации о ключах
            try:
                print("Проверка на элемент wrap_keyinfo")

                time.sleep(5)
                keyinfo_element = driver.find_element(
                    By.CSS_SELECTOR, "div.wrap_keyinfo"
                )
                keyinfo_items = keyinfo_element.find_elements(By.XPATH, ".//*")
                keyinfo_texts = [
                    item.text for item in keyinfo_items if item.text.strip()
                ]

                # Извлекаем цену, если элемент существует
                car_price = (
                    re.sub(r"\D", "", keyinfo_texts[12])
                    if len(keyinfo_texts) > 12
                    else None
                )
            except NoSuchElementException:
                print("Элемент wrap_keyinfo не найден.")

        except NoSuchElementException:
            print("Элемент gallery_photo также не найден.")

        # Форматирование значений для URL
        formatted_price = car_price.replace(",", "") if car_price else "0"
        formatted_engine_capacity = (
            car_engine_capacity.replace(",", "")[:-2] if car_engine_capacity else "0"
        )
        cleaned_date = "".join(filter(str.isdigit, car_date))
        formatted_date = (
            f"01{cleaned_date[2:4]}{cleaned_date[:2]}" if cleaned_date else "010101"
        )

        # Конечный URL
        new_url = f"https://plugin-back-versusm.amvera.io/car-ab-korea/{car_id}?price={formatted_price}&date={formatted_date}&volume={formatted_engine_capacity}"

        driver.quit()

        print(f"Данные о машине получены: {new_url}, {car_title}")
        return [new_url, car_title]

    except Exception as e:
        logging.error(f"Произошла ошибка: {e}")
        return None, None

    finally:
        driver.quit()


print(get_car_info("http://www.encar.com/dc/dc_cardetailview.do?carid=37837457"))
