import requests
import time
import re
from selenium import webdriver
from twocaptcha import TwoCaptcha
from selenium.webdriver.chrome.options import Options

# Настройка для работы с 2Captcha
solver = TwoCaptcha("YOUR_2CAPTCHA_API_KEY")


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


def get_recaptcha_token(driver, url):
    # Получаем токен reCAPTCHA с помощью 2Captcha
    try:
        site_key = extract_sitekey(driver, url)

        # Генерация токена для reCAPTCHA с использованием 2Captcha
        result = solver.recaptcha(sitekey=site_key, url=url)
        return result["code"]
    except Exception as e:
        print(f"Ошибка при получении токена: {e}")
        return None


def solve_recaptcha_with_selenium(url):
    # Инициализируем драйвер
    driver = webdriver.Chrome()

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
    # chrome_options.add_argument(f"--proxy-server={http_proxy}")
    chrome_options.add_argument(
        "user-agent=Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/88.0.4324.150 Safari/537.36"
    )

    try:
        driver.get(url)

        # Даем время для загрузки страницы
        time.sleep(100)

        # Получаем токен reCAPTCHA через 2Captcha
        recaptcha_token = get_recaptcha_token(driver, url)

        if recaptcha_token:
            print(f"Получен токен reCAPTCHA: {recaptcha_token}")

            # Вставляем токен на страницу через JavaScript
            driver.execute_script(
                """
                grecaptcha.execute('6Ld9gXsmAAAAAE_tgSNL-WBZ35ORXclvMLwwGtXZ', {action: '/dc/dc_cardetailview_do'}).then(function(token) {
                    console.log(token);  // Проверяем токен
                });
            """
            )

            # Делаем POST-запрос с полученным токеном
            post_recaptcha_token(recaptcha_token)
        else:
            print("Не удалось получить токен reCAPTCHA")

    finally:
        driver.quit()


def post_recaptcha_token(token):
    # Отправляем токен через POST запрос
    post_url = "https://encar.com/validation_recaptcha.do?method=v3"
    payload = {"token": token}
    headers = {"Content-Type": "application/x-www-form-urlencoded"}

    try:
        response = requests.post(post_url, data=payload, headers=headers, timeout=5)
        if response.status_code == 200:
            print("Токен успешно отправлен и подтвержден.")
            print(f"Ответ от сервера: {response.text}")
        else:
            print(f"Ошибка при отправке запроса: {response.status_code}")
            print(f"Тело ответа: {response.text}")
    except Exception as e:
        print(f"Ошибка при отправке POST-запроса: {e}")


# Запуск решения
solve_recaptcha_with_selenium(
    "http://www.encar.com/dc/dc_cardetailview.do?pageid=dc_carsearch&listAdvType=pic&carid=38272909&view_type=hs_ad&wtClick_korList=015&advClickPosition=kor_pic_p1_g1"
)
