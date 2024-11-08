import time
import pickle
import os
import re
import logging
from selenium import webdriver
from selenium.common.exceptions import NoSuchElementException
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


def check_and_handle_alert(driver):
    try:
        WebDriverWait(driver, 2).until(EC.alert_is_present())
        alert = driver.switch_to.alert
        print(f"Обнаружено всплывающее окно: {alert.text}")
        alert.accept()  # Закрывает alert
        print("Всплывающее окно было закрыто.")
    except:
        print("упс")


# Function to get car info using Selenium
def get_car_info(url):
    proxy_server = "109.184.168.106:7788"

    chrome_options = Options()
    chrome_options.add_argument("--disable-gpu")
    chrome_options.add_argument("--no-sandbox")
    chrome_options.add_argument("--headless")
    chrome_options.add_argument("--disable-dev-shm-usage")
    chrome_options.add_argument("--disable-infobars")
    chrome_options.add_argument("--disable-extensions")
    chrome_options.add_argument("--disable-blink-features=AutomationControlled")
    chrome_options.add_argument("--enable-logging")
    chrome_options.add_argument("--v=1")
    chrome_options.add_argument(f"--proxy-server={proxy_server}")
    chrome_options.add_argument(
        "user-agent=Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/88.0.4324.150 Safari/537.36"
    )

    service = Service(CHROMEDRIVER_PATH)
    driver = webdriver.Chrome(service=service, options=chrome_options)

    try:
        driver.get(url)
        check_and_handle_alert(driver)  # Проверка и закрытие alert
        driver.refresh()
        load_cookies(driver)

        # Проверка на reCAPTCHA
        if "reCAPTCHA" in driver.page_source:
            logging.info("Обнаружена reCAPTCHA. Пытаемся решить...")
            driver.refresh()
            check_and_handle_alert(driver)  # Перепроверка после обновления страницы

        save_cookies(driver)
        logging.info("Cookies сохранены.")

        parsed_url = urlparse(url)
        query_params = parse_qs(parsed_url.query)
        car_id = query_params.get("carid", [None])[0]

        # Ждем появления элемента с информацией о машине
        try:
            product_left = WebDriverWait(driver, 10).until(
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

            # Форматирование значений
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

            new_url = f"https://plugin-back-versusm.amvera.io/car-ab-korea/{car_id}?price={formatted_price}&date={formatted_date}&volume={formatted_engine_capacity}"
            logging.info(f"Данные о машине получены: {new_url}, {car_title}")
            return [new_url, car_title]
        except NoSuchElementException as e:
            logging.error(f"Ошибка при обработке product_left: {e}")
            return None
        except Exception as e:
            logging.error(f"Неизвестная ошибка при обработке: {e}")
            return None

    except Exception as e:
        logging.error(f"Произошла ошибка: {e}")
        return None
    finally:
        try:
            check_and_handle_alert(driver)
        except Exception as alert_exception:
            logging.error(f"Ошибка при обработке alert: {alert_exception}")
        driver.quit()


print(
    get_car_info(
        "http://www.encar.com/dc/dc_cardetailview.do?pageid=fc_carsearch&listAdvType=normal&carid=38213585&view_type=checked&adv_attribute=&wtClick_forList=019&advClickPosition=imp_normal_p1_g2&tempht_arg=OG1nM3l8zq48_1"
    )
)
