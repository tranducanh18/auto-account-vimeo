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

# Tắt popup hỏi lưu mật khẩu
prefs = {
    "credentials_enable_service": False,
    "profile.password_manager_enabled": False,
    "profile.default_content_setting_values.notifications": 2
}
options.add_experimental_option("prefs", prefs)

driver = uc.Chrome(version_main=146, options=options)
wait = WebDriverWait(driver, 60)
wait_short = WebDriverWait(driver, 3)
wait_120 = WebDriverWait(driver, 120)  # chờ tối đa 120s

AVATAR_XPATH = '//*[@data-id="account_menu_button"]'
READY_XPATH    = '//*[@id="global-nav-2025-top-desktop"]/div/ul[2]/li[2]/a'
CAPTCHA_XPATH  = '//*[@id="mIyT8"]/div/label/input'
EMAIL_XPATH    = '//*[@id="email_login"]'

driver.get("https://vimeo.com/join")
email_index = 168
email_end = 188

while email_index <= email_end:
    print("\n🔄 Bắt đầu vòng lặp mới...")

    # Bước 1: Kiểm tra captcha trước khi làm gì
    print("🔍 Kiểm tra captcha...")
    try:
        captcha_checkbox = wait_short.until(EC.element_to_be_clickable((By.XPATH, CAPTCHA_XPATH)))
        captcha_checkbox.click()
        print("✅ Đã tích captcha!")
        time.sleep(2)
    except TimeoutException:
        print("⏭️ Không có captcha, bỏ qua!")

    # Bước 2: Chờ ô email tối đa 120s, nếu không có thì đóng tab
    print("⏳ Chờ ô email xuất hiện (tối đa 120s)...")
    try:
        email_input = wait_120.until(EC.element_to_be_clickable((By.XPATH, EMAIL_XPATH)))
        print("✅ Ô email đã xuất hiện!")
    except TimeoutException:
        print("❌ Không tìm thấy ô email sau 120s, đổi proxy và thử lại...")
        driver.close()
        break

    # Bước 3: Điền email
    email = f"ducanh{email_index}@lvcmail24h.com"
    email_input.send_keys(email)
    print(f"📧 Email đang dùng: {email}")

    # Bước 4: Click Submit lần 1
    submit_btn = wait.until(EC.element_to_be_clickable((By.XPATH, '//*[@id="__next"]/div[2]/div/div[1]/div[2]/section/form[2]/button')))
    submit_btn.click()

    # Kiểm tra có sang bước nhập tên không (tối đa 5s)
    try:
        name_input = WebDriverWait(driver, 5).until(
            EC.presence_of_element_located((By.XPATH, '//*[@id="name"]'))
        )
        print("✅ Email hợp lệ, tiếp tục...")

    except TimeoutException:
        # Kiểm tra xem có quay về trang chủ Vimeo không
        current_url = driver.current_url
        if "vimeo.com" in current_url and "join" not in current_url:
            print(f"⚠️ Email {email} đã tồn tại hoặc bị lỗi, quay về trang chủ Vimeo")
        else:
            print(f"❌ Email lỗi hoặc đã tồn tại: {email}")
        
        print("🔄 Đóng tab, yêu cầu đổi proxy/VPN...")
        
        # Lưu email bị lỗi
        with open("email_failed.txt", "a") as f:
            f.write(f"{email} - {time.strftime('%Y-%m-%d %H:%M:%S')}\n")
        
        driver.close()
        driver.quit()
        break

    # Bước 5: Điền tên random 6 ký tự
    random_name = ''.join(random.choices(string.ascii_letters, k=6))
    name_input = wait.until(EC.element_to_be_clickable((By.XPATH, '//*[@id="name"]')))
    name_input.click()
    name_input.send_keys(random_name)
    print(f"✅ Đã điền tên: {random_name}")

    # Bước 6: Điền password
    password_input = wait.until(EC.element_to_be_clickable((By.XPATH, '//*[@id="password_login"]')))
    password_input.click()
    password_input.send_keys("123456!@#")
    print("✅ Đã điền password")

    # Bước 7: Điền confirm password
    confirm_input = wait.until(EC.element_to_be_clickable((By.XPATH, '//*[@id="confirm_password_login"]')))
    confirm_input.click()
    confirm_input.send_keys("123456!@#")
    print("✅ Đã điền confirm password")

    # Bước 8: Tích checkbox
    checkbox = wait.until(EC.element_to_be_clickable((By.XPATH, '//*[@id="__next"]/div[2]/div/div[1]/div[2]/section/form/section[1]/label/span[1]')))
    checkbox.click()
    print("✅ Đã tích checkbox")

    # Bước 9: Click Submit lần 2
    submit_final = wait.until(EC.element_to_be_clickable((By.XPATH, '//*[@id="__next"]/div[2]/div/div[1]/div[2]/section/form/section[3]/button')))
    submit_final.click()
    print("✅ Đã click Submit!")

    # Bước 10: Điều hướng về trang chủ Vimeo thay vì click các button
    print("🌐 Điều hướng về trang chủ Vimeo...")
    driver.get("https://vimeo.com/")
    time.sleep(3)  # Chờ trang load
    
    # Kiểm tra đã về trang chủ thành công
    if "vimeo.com" in driver.current_url and "join" not in driver.current_url:
        print("✅ Đã điều hướng thành công về trang chủ Vimeo")
    else:
        print("⚠️ Có thể chưa về đúng trang chủ")

    
    # Lưu account thành công
    password = "123456!@#"
    with open("accounts.txt", "a") as f:
        f.write(f"{email}|{password}\n")
    print(f"💾 Đã lưu account thành công: {email}")

    # Quay lại trang join cho email tiếp theo
    driver.get("https://vimeo.com/join")
    time.sleep(random.uniform(2, 5))

    # Tăng index
    email_index += 1

print("\n✅ Hoàn thành tất cả các email!")