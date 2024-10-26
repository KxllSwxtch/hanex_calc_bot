import requests
import re
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.chrome.options import Options


def get_insurance_total(car_id):
    # Configure WebDriver
    chrome_options = Options()
    chrome_options.add_argument("--disable-infobars")  # Disable the info bar
    chrome_options.add_argument("--disable-extensions")  # Disable extensions
    chrome_options.add_argument("--headless")  # Don't open the browser
    chrome_options.add_argument(
        "--disable-blink-features=AutomationControlled"
    )  # Disable detection of automation
    chrome_options.add_argument(
        "user-agent=Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/88.0.4324.150 Safari/537.36"
    )  # Add a User-Agent

    service = Service(
        "/opt/homebrew/bin/chromedriver"
    )  # Specify your chromedriver path

    # Define the URL
    url = f"http://www.encar.com/dc/dc_cardetailview.do?method=kidiFirstPop&carid={car_id}&wtClick_carview=044"

    try:
        # Start the WebDriver
        driver = webdriver.Chrome(service=service, options=chrome_options)

        # Navigate to the URL
        driver.get(url)

        # Check if reCAPTCHA is present
        if "reCAPTCHA" in driver.page_source:
            print("reCAPTCHA detected, please solve it manually.")
            input("Press Enter after solving reCAPTCHA...")  # Wait for user input

        # Найти элемент с классом smlist
        try:
            smlist_element = driver.find_element(By.CLASS_NAME, "smlist")
            print("Элемент с классом 'smlist' найден!")
            # Выводим содержимое элемента
            smlist_list = smlist_element.text.split("\n")
            damage_to_my_car = (
                "0" if smlist_list[-2] == "없음" else smlist_list[-2].split(", ")[1]
            )
            damage_to_other_car = (
                "0" if smlist_list[-1] == "없음" else smlist_list[-1].split(", ")[1]
            )

            damage_to_my_car_formatted = ",".join(re.findall(r"\d+", damage_to_my_car))
            damage_to_other_car_formatted = ",".join(
                re.findall(r"\d+", damage_to_other_car)
            )
        except Exception as e:
            print(f"Не удалось найти элемент с классом 'smlist': {e}")

    except Exception as e:
        print(f"Произошла ошибка: {e}")
    finally:
        driver.quit()  # Close the WebDriver


# Example call with car_id
car_id = "38173474"  # Replace with an actual car ID
get_insurance_total(car_id)
