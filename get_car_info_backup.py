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
        check_and_handle_alert(driver)

        # Проверка на reCAPTCHA
        if "reCAPTCHA" in driver.page_source:
            print("Обнаружена reCAPTCHA. Пытаемся решить...")
            driver.refresh()
            print("Страница обновлена после reCAPTCHA.")
            check_and_handle_alert(driver)

        wait_for_page_to_load(driver)

        # Парсим URL для получения carid
        parsed_url = urlparse(url)
        query_params = parse_qs(parsed_url.query)
        car_id = query_params.get("carid", [None])[0]
        car_id_external = car_id

        ########
        # Проверка элемента areaLeaseRent
        ########
        try:
            print("Проверка на areaLeaseRent")

            time.sleep(6)
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

            time.sleep(6)
            product_left = driver.find_element(By.CLASS_NAME, "product_left")
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

            driver.quit()

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

            time.sleep(6)
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
