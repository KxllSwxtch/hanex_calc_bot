import re
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.chrome.options import Options


def get_insurance_total(car_id):
    # Настройка WebDriver с нужными опциями
    chrome_options = Options()
    chrome_options.add_argument("--disable-infobars")
    chrome_options.add_argument("--disable-extensions")
    chrome_options.add_argument("--headless")
    chrome_options.add_argument("--disable-blink-features=AutomationControlled")
    chrome_options.add_argument(
        "user-agent=Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/88.0.4324.150 Safari/537.36"
    )

    service = Service("/opt/homebrew/bin/chromedriver")

    # Формируем URL с использованием car_id
    url = f"http://www.encar.com/dc/dc_cardetailview.do?method=kidiFirstPop&carid={car_id}&wtClick_carview=044"

    try:
        # Запускаем WebDriver
        driver = webdriver.Chrome(service=service, options=chrome_options)
        driver.get(url)

        # Проверяем наличие reCAPTCHA на странице
        if "reCAPTCHA" in driver.page_source:
            print("reCAPTCHA обнаружена, пожалуйста, решите её вручную.")
            input("Нажмите Enter после решения reCAPTCHA...")

        try:
            # Ищем элемент с классом 'smlist'
            smlist_element = driver.find_element(By.CLASS_NAME, "smlist")
            # Находим таблицу внутри элемента
            table = smlist_element.find_element(By.TAG_NAME, "table")

            # Получаем все строки таблицы
            rows = table.find_elements(By.TAG_NAME, "tr")

            # Извлекаем данные из пятого и шестого tr, если они существуют
            damage_to_my_car = (
                rows[4].find_elements(By.TAG_NAME, "td")[1].text
                if len(rows) > 4
                else "Нет данных"
            )
            damage_to_other_car = (
                rows[5].find_elements(By.TAG_NAME, "td")[1].text
                if len(rows) > 5
                else "Нет данных"
            )

            # Функция для извлечения и форматирования больших чисел
            def extract_large_number(damage_text):
                # Если в тексте присутствует "없음", возвращаем 0
                if "없음" in damage_text:
                    return "0"

                # Извлекаем все числа, убирая 원 и другие нежелательные символы
                numbers = re.findall(r"[\d,]+(?=\s*원)", damage_text)

                # Если есть большие числа, возвращаем первое найденное большое число
                if numbers:
                    return numbers[0]
                else:
                    return "0"

            # Извлекаем и форматируем данные
            damage_to_my_car_formatted = extract_large_number(damage_to_my_car)
            damage_to_other_car_formatted = extract_large_number(damage_to_other_car)

        except Exception as e:
            print(f"Не удалось найти элемент с классом 'smlist': {e}")
            return [
                "Ошибка: Не удалось найти нужные данные",
                "Ошибка: Не удалось найти нужные данные",
            ]

        # Возвращаем отформатированные данные
        return [damage_to_my_car_formatted, damage_to_other_car_formatted]

    except Exception as e:
        print(f"Произошла ошибка при получении данных: {e}")
        return "Ошибка при получении деталей страховки."

    finally:
        driver.quit()


# Примеры вызова функции
print(get_insurance_total("37723583"))
print(get_insurance_total("38208463"))
print(get_insurance_total("38189887"))
print(get_insurance_total("38144941"))
print(get_insurance_total("38289851"))
