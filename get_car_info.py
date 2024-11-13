import time
import pickle
import os
import re
import logging
from selenium import webdriver
from selenium.common.exceptions import NoSuchElementException, TimeoutException
from selenium.webdriver.common.by import By
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.chrome.options import Options
from urllib.parse import urlparse, parse_qs
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.common.exceptions import NoAlertPresentException

COOKIES_FILE = "cookies.pkl"
CHROMEDRIVER_PATH = "/opt/homebrew/bin/chromedriver"


def save_cookies(driver):
    with open(COOKIES_FILE, "wb") as file:
        pickle.dump(driver.get_cookies(), file)


# Load cookies from file
def load_cookies(driver):
    if os.path.exists(COOKIES_FILE):
        with open(COOKIES_FILE, "rb") as file:
            cookies = pickle.load(file)
            for cookie in cookies:
                driver.add_cookie(cookie)


def check_and_handle_alert(driver, wait_time=5):
    try:
        WebDriverWait(driver, wait_time).until(EC.alert_is_present())
        alert = driver.switch_to.alert
        print(f"Обнаружено всплывающее окно: {alert.text}")
        alert.accept()  # Закрывает alert
        print("Всплывающее окно было закрыто.")
    except TimeoutException:
        print("Всплывающее окно не обнаружено.")
    except Exception as e:
        print(f"Произошла ошибка при обработке всплывающего окна: {e}")


# Function to get car info using Selenium
def get_car_info(url):
    global car_id_external

    chrome_options = Options()
    chrome_options.add_argument("--headless")
    chrome_options.add_argument("--no-sandbox")
    chrome_options.add_argument("--disable-dev-shm-usage")
    chrome_options.add_argument("--remote-debugging-port=9222")
    chrome_options.add_argument("--disable-gpu")
    chrome_options.add_argument("--disable-software-rasterizer")
    chrome_options.add_argument("--window-size=1920x1080")  # Устанавливаем размер окна
    chrome_options.add_argument("--disable-notifications")  # Отключаем уведомления
    chrome_options.add_argument("--incognito")
    chrome_options.add_argument(
        "--user-agent=Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/92.0.4515.159 Safari/537.36"
    )

    # Инициализация драйвера
    service = Service(CHROMEDRIVER_PATH)
    driver = webdriver.Chrome(service=service, options=chrome_options)

    try:
        # Загружаем страницу
        driver.get(url)
        check_and_handle_alert(driver)  # Обработка alert, если присутствует
        load_cookies(driver)

        # Проверка на reCAPTCHA
        if "reCAPTCHA" in driver.page_source:
            logging.info("Обнаружена reCAPTCHA. Пытаемся решить...")
            driver.refresh()
            logging.info("Страница обновлена после reCAPTCHA.")
            check_and_handle_alert(driver)  # Перепроверка после обновления страницы

        save_cookies(driver)
        logging.info("Куки сохранены.")

        # Парсим URL для получения carid
        parsed_url = urlparse(url)
        query_params = parse_qs(parsed_url.query)
        car_id = query_params.get("carid", [None])[0]

        # Проверка элемента areaLeaseRent
        try:
            lease_area = driver.find_element(By.ID, "areaLeaseRent")
            title_element = lease_area.find_element(By.CLASS_NAME, "title")

            if "리스정보" in title_element.text or "렌트정보" in title_element.text:
                logging.info("Данная машина находится в лизинге.")
                return [
                    "",
                    "Данная машина находится в лизинге. Свяжитесь с менеджером.",
                ]
        except NoSuchElementException:
            logging.warning("Элемент areaLeaseRent не найден.")

        # Инициализация переменных
        car_title, car_date, car_engine_capacity, car_price = "", "", "", ""

        # Проверка элемента product_left
        try:
            product_left = WebDriverWait(driver, 7).until(
                EC.presence_of_element_located((By.CLASS_NAME, "product_left"))
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
            logging.info(f"Данные о машине получены: {new_url}, {car_title}")
            return [new_url, car_title]
        except NoSuchElementException as e:
            logging.error(f"Ошибка при обработке product_left: {e}")
        except Exception as e:
            logging.error(f"Неизвестная ошибка при обработке product_left: {e}")

        # Проверка элемента gallery_photo
        try:
            gallery_element = driver.find_element(By.CSS_SELECTOR, "div.gallery_photo")
            car_title = gallery_element.find_element(By.CLASS_NAME, "prod_name").text
            items = gallery_element.find_elements(By.XPATH, ".//*")

            if len(items) > 10:
                car_date = items[10].text
            if len(items) > 18:
                car_engine_capacity = items[18].text

            # Извлечение информации о ключах
            try:
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
                logging.warning("Элемент wrap_keyinfo не найден.")

        except NoSuchElementException:
            logging.warning("Элемент gallery_photo также не найден.")

        # Форматирование значений для URL
        if car_price:
            formatted_price = car_price.replace(",", "")
        else:
            formatted_price = "0"  # Задаем значение по умолчанию

        formatted_engine_capacity = (
            car_engine_capacity.replace(",", "")[:-2] if car_engine_capacity else "0"
        )
        cleaned_date = "".join(filter(str.isdigit, car_date))
        formatted_date = (
            f"01{cleaned_date[2:4]}{cleaned_date[:2]}" if cleaned_date else "010101"
        )

        # Конечный URL
        new_url = f"https://plugin-back-versusm.amvera.io/car-ab-korea/{car_id}?price={formatted_price}&date={formatted_date}&volume={formatted_engine_capacity}"

        logging.info(f"Данные о машине получены: {new_url}, {car_title}")
        return [new_url, car_title]

    except Exception as e:
        logging.error(f"Произошла ошибка: {e}")
        return None, None

    finally:
        # Обработка всплывающих окон (alerts)
        try:
            alert = driver.switch_to.alert
            alert.dismiss()
            logging.info("Всплывающее окно отклонено.")
        except NoAlertPresentException:
            logging.info("Нет активного всплывающего окна.")
        except Exception as alert_exception:
            logging.error(f"Ошибка при обработке alert: {alert_exception}")

        driver.quit()


print(
    get_car_info(
        "http://www.encar.com/dc/dc_cardetailview.do?pageid=dc_carsearch&listAdvType=word&carid=38434253&view_type=normal&wtClick_korList=007&advClickPosition=kor_word_p1_g7"
    )
)
# print(get_car_info("https://fem.encar.com/cars/detail/38358876"))
