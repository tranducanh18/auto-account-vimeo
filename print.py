import random
import string
import time
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.common.exceptions import TimeoutException

import undetected_chromedriver as uc
options = uc.ChromeOptions()
options.add_argument("--disable-blink-features=AutomationControlled")
options.add_argument("--start-maximized")
options.add_argument("--no-sandbox")
options.add_argument("--disable-dev-shm-usage")

# Tat popup hoi luu mat khau
prefs = {
    "credentials_enable_service": False,
    "profile.password_manager_enabled": False,
    "profile.default_content_setting_values.notifications": 2
}
options.add_experimental_option("prefs", prefs)

driver = uc.Chrome(version_main=146, options=options)
wait = WebDriverWait(driver, 60)
wait_short = WebDriverWait(driver, 3)
wait_120 = WebDriverWait(driver, 120)

CAPTCHA_XPATH  = '//*[@id="mIyT8"]/div/label/input'
EMAIL_XPATH    = '//*[@id="email_login"]'

driver.get("https://vimeo.com/join")
email_index = 215
email_end = 300

while email_index <= email_end:
    print("\n=== START LOOP ===")
    
    current_email = f"ducanh{email_index}@lvcmail24h.com"
    email_valid = False
    
    # Thu email hien tai cho den khi xac dinh no hop le hoac da ton tai
    while True:
        print(f"\nDang thu email: {current_email}")
        
        # Kiem tra captcha
        print("[1] Dang kiem tra captcha...")
        try:
            captcha_checkbox = wait_short.until(EC.element_to_be_clickable((By.XPATH, CAPTCHA_XPATH)))
            captcha_checkbox.click()
            print("[OK] Da tick captcha!")
            time.sleep(2)
        except TimeoutException:
            print("[BO QUA] Khong co captcha")

        # Cho o email xuat hien
        print("[2] Dang cho o email (toi da 120s)...")
        try:
            email_input = wait_120.until(EC.element_to_be_clickable((By.XPATH, EMAIL_XPATH)))
            print("[OK] Da tim thay o email!")
        except TimeoutException:
            print("[LOI] Khong tim thay o email sau 120s, dang refresh...")
            driver.refresh()
            time.sleep(3)
            continue

        # Dien email
        email_input.clear()
        email_input.send_keys(current_email)
        print(f"[3] Dang dung email: {current_email}")

        # Click submit lan 1
        submit_btn = wait.until(EC.element_to_be_clickable((By.XPATH, '//*[@id="__next"]/div[2]/div/div[1]/div[2]/section/form[2]/button')))
        submit_btn.click()

        # Kiem tra co sang buoc nhap ten khong (toi da 5s)
        try:
            name_input = WebDriverWait(driver, 5).until(
                EC.presence_of_element_located((By.XPATH, '//*[@id="name"]'))
            )
            print("[OK] EMAIL HOP LE! Sang duoc trang nhap ten")
            email_valid = True
            break  # Thoat vong lap thu, tien hanh dang ky

        except TimeoutException:
            # Khong sang duoc trang nhap ten => email da ton tai
            print(f"[TON TAI] Email {current_email} da duoc su dung, khong the dang ky")
            
            # Chuyen sang email tiep theo
            email_index += 1
            driver.get("https://vimeo.com/join")
            time.sleep(2)
            break  # Thoat vong lap thu de bat dau email moi
    
    # Neu email khong hop le (da ton tai), quay lai vong lap chinh
    if not email_valid:
        continue

    # ===== DEN DUOC DAY LA EMAIL HOP LE, TIEN HANH DANG KY =====
    print("\n=== BAT DAU DANG KY TAI KHOAN ===")
    
    # Dien ten random
    random_name = ''.join(random.choices(string.ascii_letters, k=6))
    name_input = wait.until(EC.element_to_be_clickable((By.XPATH, '//*[@id="name"]')))
    name_input.click()
    name_input.send_keys(random_name)
    print(f"[4] Ten: {random_name}")

    # Dien password
    password_input = wait.until(EC.element_to_be_clickable((By.XPATH, '//*[@id="password_login"]')))
    password_input.click()
    password_input.send_keys("123456!@#")
    print("[5] Da dien password")

    # Dien confirm password
    confirm_input = wait.until(EC.element_to_be_clickable((By.XPATH, '//*[@id="confirm_password_login"]')))
    confirm_input.click()
    confirm_input.send_keys("123456!@#")
    print("[6] Da dien xac nhan password")

    # Tich checkbox
    checkbox = wait.until(EC.element_to_be_clickable((By.XPATH, '//*[@id="__next"]/div[2]/div/div[1]/div[2]/section/form/section[1]/label/span[1]')))
    checkbox.click()
    print("[7] Da tick checkbox")

    # Click submit lan 2
    submit_final = wait.until(EC.element_to_be_clickable((By.XPATH, '//*[@id="__next"]/div[2]/div/div[1]/div[2]/section/form/section[3]/button')))
    submit_final.click()
    print("[8] Da submit lan cuoi")
    # Ve trang chu Vimeo
    print("[9] Dang chuyen ve trang chu Vimeo...")
    driver.get("https://vimeo.com/")
    
    if "vimeo.com" in driver.current_url and "join" not in driver.current_url:
        print("[OK] Da ve trang chu thanh cong")
    else:
        print("[CANH BAO] Co the chua ve dung trang chu")

    # Luu account thanh cong
    password = "123456!@#"
    with open("accounts.txt", "a", encoding='utf-8') as f:
        f.write(f"{current_email}|{password}\n")
    print(f"[DA LUU] Tao tai khoan thanh cong: {current_email}")

    # ===== TEST LAI EMAIL VUA TAO =====
    print("\n=== TEST LAI EMAIL VUA TAO ===")
    driver.get("https://vimeo.com/join")
    
    test_success = False
    test_attempt = 0
    retry_create_count = 0  # Dem so lan tao lai that bai
    
    while not test_success:
        test_attempt += 1
        print(f"\n[TEST LAN {test_attempt}] Kiem tra email: {current_email}")
        
        # Kiem tra captcha
        try:
            captcha_checkbox = wait_short.until(EC.element_to_be_clickable((By.XPATH, CAPTCHA_XPATH)))
            captcha_checkbox.click()
            print("[OK] Da tick captcha!")
        except TimeoutException:
            print("[BO QUA] Khong co captcha")
        
        # Tim o email
        try:
            email_input = wait_120.until(EC.element_to_be_clickable((By.XPATH, EMAIL_XPATH)))
            print("[OK] Da tim thay o email")
        except TimeoutException:
            print("[LOI] Khong tim thay o email, refresh...")
            driver.refresh()
            time.sleep(3)
            continue
        
        # Dien email
        email_input.clear()
        email_input.send_keys(current_email)
        print(f"[TEST] Dang dung email: {current_email}")
        
        # Click submit
        submit_btn = wait.until(EC.element_to_be_clickable((By.XPATH, '//*[@id="__next"]/div[2]/div/div[1]/div[2]/section/form[2]/button')))
        submit_btn.click()
        
        # Kiem tra ket qua
        try:
            name_input_test = WebDriverWait(driver, 5).until(
                EC.presence_of_element_located((By.XPATH, '//*[@id="name"]'))
            )
            # Van sang duoc trang nhap ten => chua duoc tao, can tao lai
            retry_create_count += 1
            print(f"[CHUA TAO] Email {current_email} van co the dang ky (lan that bai thu {retry_create_count})")
            
            # Kiem tra neu da tao lai that bai 3 lan
            if retry_create_count >= 3:
                print("\n" + "="*50)
                print("[ERROR] DA TAO LAI 3 LAN VAN THAT BAI!")
                print("[ERROR] EMAIL VAN SANG DUOC TRANG NHAP TEN")
                print("[ERROR] KHA NANG CAO IP/PROXY DA BI CHAN")
                print("[ERROR] VUI LONG DOI PROXY VA CHAY LAI CHUONG TRINH")
                print("="*50)
                
                # Ghi log loi
                with open("error_proxy.txt", "a", encoding='utf-8') as f:
                    f.write(f"{time.strftime('%Y-%m-%d %H:%M:%S')} - Can doi proxy - Email that bai: {current_email}\n")
                
                driver.quit()
                exit()
            
            # Tao lai tai khoan
            print(f"[TAO LAI LAN {retry_create_count}] Dang tao lai tai khoan...")
            random_name_new = ''.join(random.choices(string.ascii_letters, k=6))
            name_input_test.click()
            name_input_test.send_keys(random_name_new)
            print(f"[TAO LAI] Ten moi: {random_name_new}")
            
            password_input_test = wait.until(EC.element_to_be_clickable((By.XPATH, '//*[@id="password_login"]')))
            password_input_test.click()
            password_input_test.send_keys("123456!@#")
            
            confirm_input_test = wait.until(EC.element_to_be_clickable((By.XPATH, '//*[@id="confirm_password_login"]')))
            confirm_input_test.click()
            confirm_input_test.send_keys("123456!@#")
            
            checkbox_test = wait.until(EC.element_to_be_clickable((By.XPATH, '//*[@id="__next"]/div[2]/div/div[1]/div[2]/section/form/section[1]/label/span[1]')))
            checkbox_test.click()
            
            submit_final_test = wait.until(EC.element_to_be_clickable((By.XPATH, '//*[@id="__next"]/div[2]/div/div[1]/div[2]/section/form/section[3]/button')))
            submit_final_test.click()
            
            print("[TAO LAI THANH CONG]")
            driver.get("https://vimeo.com/")
            
            # Reset bien dem sau khi tao lai thanh cong? Khong, van con trong vong lap test
            # Nhung da tao lai thanh cong, tiep tuc test lai lan nua
            print("\n[TEST LAI SAU KHI TAO LAI] Quay lai trang join de test tiep...")
            driver.get("https://vimeo.com/join")
            # Tiep tuc vong lap while de test lai
            
        except TimeoutException:
            # Khong sang duoc trang nhap ten => email da ton tai, ok
            print(f"[OK] Email {current_email} da ton tai, khong the dang ky lai")
            print("[KET LUAN] Tai khoan da duoc tao thanh cong")
            test_success = True
            break
    
    # Chuyen sang email tiep theo
    print(f"\n[CHUYEN] Sang email tiep theo: ducanh{email_index + 1}@lvcmail24h.com")
    email_index += 1
    driver.get("https://vimeo.com/join")

print("\n=== HOAN THANH TAT CA EMAIL ===")
driver.quit()