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
        logging.info("Открываем URL")
        driver.get(url)
        check_and_handle_alert(driver)

        if "reCAPTCHA" in driver.page_source:
            logging.info("Обнаружена reCAPTCHA. Пытаемся решить...")
            driver.refresh()
            check_and_handle_alert(driver)

        save_cookies(driver)

        parsed_url = urlparse(url)
        car_id = parsed_url.path.split("/")[-1]

        # Прокручиваем к кнопке и пытаемся кликнуть с помощью JavaScript
        try:
            logging.info("Ищем кнопку '자세히'")
            details_button = WebDriverWait(driver, 5).until(
                EC.presence_of_element_located(
                    (By.XPATH, "//button[contains(text(), '자세히')]")
                )
            )
            driver.execute_script("arguments[0].scrollIntoView(true);", details_button)
            time.sleep(1)  # Небольшая задержка для прокрутки

            # Пытаемся кликнуть стандартным методом, если ошибка — используем JavaScript
            try:
                details_button.click()
                logging.info("Кнопка '자세히' успешно нажата стандартным методом.")
            except Exception as e:
                logging.warning(
                    f"Ошибка при обычном нажатии, пробуем JavaScript. Ошибка: {e}"
                )
                driver.execute_script("arguments[0].click();", details_button)
                logging.info("Кнопка '자세히' нажата через JavaScript.")

            logging.info("Кнопка '자세히' нажата, раскрыты дополнительные детали.")
        except (NoSuchElementException, TimeoutException) as e:
            logging.warning(f"Кнопка '자세히' не найдена или не нажата: {e}")

        # Извлекаем данные из элементов
        try:
            logging.info("Извлекаем данные из элементов страницы")
            summary_element = WebDriverWait(driver, 6).until(
                EC.presence_of_element_located(
                    (By.CLASS_NAME, "DetailSummary_define_summary__NOYid")
                )
            )
            car_date = summary_element.find_element(By.TAG_NAME, "dd").text.strip()

            price_element = driver.find_element(
                By.CLASS_NAME, "DetailLeadBottom_point__uBgbF"
            )
            car_price = re.sub(r"\D", "", price_element.text)

            spec_list = WebDriverWait(driver, 6).until(
                EC.presence_of_element_located(
                    (By.CLASS_NAME, "DetailSpec_list_default__Gx+ZA")
                )
            )
            engine_capacity_element = spec_list.find_elements(By.TAG_NAME, "li")[3]
            engine_capacity_text = engine_capacity_element.find_element(
                By.CLASS_NAME, "DetailSpec_txt__NGapF"
            ).text
            car_engine_capacity = re.sub(r"\D", "", engine_capacity_text)

            formatted_price = car_price.replace(",", "")
            formatted_engine_capacity = (
                car_engine_capacity if car_engine_capacity else "0"
            )
            cleaned_date = "".join(filter(str.isdigit, car_date))
            formatted_date = (
                f"01{cleaned_date[2:4]}{cleaned_date[:2]}" if cleaned_date else "010101"
            )

            new_url = f"https://plugin-back-versusm.amvera.io/car-ab-korea/{car_id}?price={formatted_price}&date={formatted_date}&volume={formatted_engine_capacity}"
            logging.info(f"Данные успешно получены: {new_url}")
            return [new_url, f"Автомобиль ID {car_id}"]

        except NoSuchElementException as e:
            logging.error(f"Не удалось найти элемент: {e}")
            return None, None

    except Exception as e:
        logging.error(f"Произошла ошибка: {e}")
        return None, None

    finally:
        try:
            alert = driver.switch_to.alert
            alert.dismiss()
        except NoAlertPresentException:
            pass
        driver.quit()


print(get_car_info("https://fem.encar.com/cars/detail/38453939"))
# print(get_car_info("https://fem.encar.com/cars/detail/38358876"))
