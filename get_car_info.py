import requests
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.chrome.options import Options
from urllib.parse import urlparse, parse_qs
import json

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

service = Service("/opt/homebrew/bin/chromedriver")  # Specify your chromedriver path

# Define the URL
url = "http://www.encar.com/dc/dc_cardetailview.do?pageid=dc_carsearch&listAdvType=normal&carid=38313470&view_type=checked&adv_attribute=&wtClick_korList=019&advClickPosition=kor_normal_p1_g10&tempht_arg=1fI3zz7nle73_9"

try:
    # Start the WebDriver
    driver = webdriver.Chrome(service=service, options=chrome_options)

    # Navigate to the URL
    driver.get(url)

    # Check if reCAPTCHA is present
    if "reCAPTCHA" in driver.page_source:
        print("reCAPTCHA detected, please solve it manually.")
        input("Press Enter after solving reCAPTCHA...")  # Wait for user input

    # Parse the URL to get carid
    parsed_url = urlparse(url)
    query_params = parse_qs(parsed_url.query)
    car_id = query_params.get("carid", [None])[0]  # Get the carid value

    # Find the gallery container
    gallery_element = driver.find_element(
        By.CSS_SELECTOR, "div.gallery_photo"  # or use "#carPic" for the ID
    )

    # Find all child elements in the gallery
    items = gallery_element.find_elements(
        By.XPATH, ".//*"
    )  # Get all descendant elements

    # Output items for car date and engine capacity
    car_date = ""
    car_engine_capacity = ""
    car_price = ""

    for index, item in enumerate(items):
        if index == 10:
            car_date = item.text
        if index == 18:
            car_engine_capacity = item.text

    # Find and print the wrap_keyinfo div
    keyinfo_element = driver.find_element(By.CSS_SELECTOR, "div.wrap_keyinfo")

    # Save each item in wrap_keyinfo to a list
    keyinfo_items = keyinfo_element.find_elements(
        By.XPATH, ".//*"
    )  # Get all descendant elements
    keyinfo_texts = [
        item.text for item in keyinfo_items if item.text.strip() != ""
    ]  # Create a list with non-empty texts

    # Iterate and print each key info item
    for index, info in enumerate(keyinfo_texts):
        if index == 12:
            car_price = info

    # Format values for the URL
    formatted_price = car_price.replace(",", "")  # Remove commas from price
    formatted_engine_capacity = car_engine_capacity.replace(",", "")[0:-2]

    # Process car_date to keep only digits and rearrange
    cleaned_date = "".join(filter(str.isdigit, car_date))  # Keep only digits
    formatted_date = f"01{cleaned_date[2:4]}{cleaned_date[:2]}"

    # Construct the new URL with the extracted values
    new_url = f"https://plugin-back-versusm.amvera.io/car-ab-korea/{car_id}?price={formatted_price}&date={formatted_date}&volume={formatted_engine_capacity}"


except Exception as e:
    print(f"Произошла ошибка: {e}")

finally:
    driver.quit()  # Close the WebDriver


# Выполнение GET-запроса
response = requests.get(new_url)

# Проверка успешности запроса
if response.status_code == 200:
    print("Ответ от сервера:")
    try:
        json_response = response.json()  # Получаем JSON-ответ
        print(
            json.dumps(json_response, indent=4, ensure_ascii=False)
        )  # Форматированный вывод JSON
    except json.JSONDecodeError:
        print("Ответ не в формате JSON:", response.text)
else:
    print(f"Ошибка при выполнении запроса: {response.status_code}")
