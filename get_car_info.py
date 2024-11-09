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
    chrome_options.add_argument("--disable-gpu")
    chrome_options.add_argument("--headless")
    chrome_options.add_argument("--no-sandbox")
    chrome_options.add_argument("--disable-dev-shm-usage")
    chrome_options.add_argument("--disable-infobars")
    chrome_options.add_argument("--disable-extensions")
    chrome_options.add_argument("--disable-blink-features=AutomationControlled")
    chrome_options.add_argument("--enable-logging")
    chrome_options.add_argument("--v=1")
    chrome_options.add_argument(
        "user-agent=Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/88.0.4324.150 Safari/537.36"
    )

    service = Service(CHROMEDRIVER_PATH)
    driver = webdriver.Chrome(service=service, options=chrome_options)

    try:
        driver.get(url)
        load_cookies(driver)
        check_and_handle_alert(driver)

        if "reCAPTCHA" in driver.page_source:
            logging.info("Обнаружена reCAPTCHA. Пытаемся решить...")
            driver.refresh()
            logging.info("Страница обновлена после reCAPTCHA.")
            check_and_handle_alert(driver)

        save_cookies(driver)

        # Извлечение car_id
        parsed_url = urlparse(url)
        query_params = parse_qs(parsed_url.query)
        car_id = query_params.get("carid", [None])[0]
        if not car_id:
            logging.warning("car_id не найден в URL. Возвращаем None.")
            return None, None

        # Проверка лизинга
        try:
            lease_area = WebDriverWait(driver, 3).until(
                EC.presence_of_element_located((By.ID, "areaLeaseRent"))
            )
            title_element = lease_area.find_element(By.CLASS_NAME, "title")

            if "리스정보" in title_element.text or "렌트정보" in title_element.text:
                logging.info("Данная машина находится в лизинге.")
                return [
                    "",
                    "Данная машина находится в лизинге. Свяжитесь с менеджером.",
                ]
        except (NoSuchElementException, TimeoutException):
            logging.warning("Элемент areaLeaseRent не найден.")

        car_title, car_date, car_engine_capacity, car_price = "", "", "", ""

        # Обработка product_left и gallery_photo в одном try
        try:
            product_left = WebDriverWait(driver, 3).until(
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
            car_price = (
                re.sub(r"\D", "", product_left_splitted[1])
                if len(product_left_splitted) > 1
                else "0"
            )

        except (NoSuchElementException, TimeoutException):
            logging.warning(
                "Элемент product_left не найден, пробуем искать gallery_photo."
            )

            try:
                gallery_element = driver.find_element(
                    By.CSS_SELECTOR, "div.gallery_photo"
                )
                car_title = gallery_element.find_element(
                    By.CLASS_NAME, "prod_name"
                ).text
                items = gallery_element.find_elements(By.XPATH, ".//*")
                car_date = items[10].text if len(items) > 10 else car_date
                car_engine_capacity = (
                    items[18].text if len(items) > 18 else car_engine_capacity
                )
            except NoSuchElementException as gallery_error:
                logging.error(
                    "Не удалось найти ни product_left, ни gallery_photo: %s",
                    gallery_error,
                    exc_info=True,
                )

        # Обработка wrap_keyinfo
        try:
            keyinfo_element = driver.find_element(By.CSS_SELECTOR, "div.wrap_keyinfo")
            keyinfo_texts = [
                item.text
                for item in keyinfo_element.find_elements(By.XPATH, ".//*")
                if item.text.strip()
            ]
            car_price = (
                re.sub(r"\D", "", keyinfo_texts[12])
                if len(keyinfo_texts) > 12
                else car_price
            )

        except NoSuchElementException:
            logging.warning("Элемент wrap_keyinfo не найден.")

        # Если нет названия или ссылки на машину, выбрасываем ошибку
        if not car_title or not car_price:
            logging.error("Не удалось найти информацию о машине (название или цена).")
            raise ValueError("Ссылка или название автомобиля не найдены.")

        # Форматирование значений
        formatted_price = car_price if car_price else "0"
        formatted_engine_capacity = (
            re.sub(r"\D", "", car_engine_capacity)[:-2] if car_engine_capacity else "0"
        )
        cleaned_date = "".join(filter(str.isdigit, car_date))
        formatted_date = (
            f"01{cleaned_date[2:4]}{cleaned_date[:2]}"
            if len(cleaned_date) >= 4
            else "010101"
        )

        logging.info(f"Форматированная цена: {formatted_price}")
        logging.info(f"Форматированная емкость двигателя: {formatted_engine_capacity}")
        logging.info(f"Форматированная дата: {formatted_date}")

        new_url = f"https://plugin-back-versusm.amvera.io/car-ab-korea/{car_id}?price={formatted_price}&date={formatted_date}&volume={formatted_engine_capacity}"

        logging.info(f"Данные о машине получены: {new_url}, {car_title}")
        return [new_url, car_title]

    except Exception as e:
        logging.error("Произошла ошибка в get_car_info: %s", e, exc_info=True)
        return None, None

    finally:
        try:
            alert = driver.switch_to.alert
            alert.dismiss()
            logging.info("Всплывающее окно отклонено.")
        except NoAlertPresentException:
            logging.info("Нет активного всплывающего окна.")
        except Exception as alert_exception:
            logging.error(
                "Ошибка при обработке alert: %s", alert_exception, exc_info=True
            )

        driver.quit()


print(
    get_car_info(
        "http://www.encar.com/dc/dc_cardetailview.do?pageid=fc_carsearch&listAdvType=normal&carid=38213585&view_type=checked&adv_attribute=&wtClick_forList=019&advClickPosition=imp_normal_p1_g2&tempht_arg=OG1nM3l8zq48_1"
    )
)
