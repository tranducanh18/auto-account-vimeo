import random
import string
import time
import threading
import tkinter as tk
from tkinter import scrolledtext, messagebox
import sys
import os

from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.common.exceptions import TimeoutException
import undetected_chromedriver as uc

# ── Windows API để ẩn/hiện cửa sổ ──────────────────────────────────
import ctypes
import ctypes.wintypes

user32 = ctypes.windll.user32

def find_chrome_hwnd():
    """Tìm handle cửa sổ Chrome"""
    result = []
    def callback(hwnd, _):
        title = ctypes.create_unicode_buffer(512)
        user32.GetWindowTextW(hwnd, title, 512)
        if title.value and ("Chrome" in title.value or "Google Chrome" in title.value):
            result.append(hwnd)
        return True
    WNDENUMPROC = ctypes.WINFUNCTYPE(ctypes.c_bool, ctypes.wintypes.HWND, ctypes.wintypes.LPARAM)
    user32.EnumWindows(WNDENUMPROC(callback), 0)
    return result[0] if result else None

def hide_chrome():
    """Ẩn cửa sổ Chrome"""
    hwnd = find_chrome_hwnd()
    if hwnd:
        user32.ShowWindow(hwnd, 0)

def show_chrome():
    """Hiện cửa sổ Chrome"""
    hwnd = find_chrome_hwnd()
    if hwnd:
        user32.ShowWindow(hwnd, 9)
        user32.SetForegroundWindow(hwnd)
        time.sleep(0.5)

# ── Đường dẫn file cùng thư mục với script ───────────────────────────────────
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
ACCOUNTS_FILE = os.path.join(BASE_DIR, "accounts.txt")
EMAIL_FAILED_FILE = os.path.join(BASE_DIR, "email_failed.txt")
ERROR_PROXY_FILE = os.path.join(BASE_DIR, "error_proxy.txt")

# ════════════════════════════════════════════════════════════════════════════
#  GUI
# ════════════════════════════════════════════════════════════════════════════
class App(tk.Tk):
    def __init__(self):
        super().__init__()
        self.title("Vimeo Auto Tool for ducanh")
        self.geometry("600x720")
        self.resizable(False, False)
        self.configure(bg="#0f0f0f")

        self.driver = None
        self.running = False
        self.thread = None
        
        self.hide_window = tk.BooleanVar(value=True)
        self._build_ui()

    def log_error(self, msg):
        """Log message màu đỏ"""
        self.log.configure(state="normal")
        self.log.insert("end", msg + "\n", "error")
        self.log.tag_config("error", foreground="#ff4455")  # màu đỏ
        self.log.see("end")
        self.log.configure(state="disabled")
        
    def _build_ui(self):
        # Header
        tk.Label(self, text="VIMEO AUTO TOOL", font=("Courier New", 18, "bold"),
                 bg="#0f0f0f", fg="#00ff88").pack(pady=(18, 2))
        tk.Label(self, text="─" * 60, bg="#0f0f0f", fg="#333").pack()

        # Frame cấu hình
        cfg = tk.Frame(self, bg="#0f0f0f")
        cfg.pack(padx=24, pady=10, fill="x")

        def row(parent, label, default, row):
            tk.Label(parent, text=label, bg="#0f0f0f", fg="#aaa",
                     font=("Courier New", 10), width=18, anchor="w").grid(row=row, column=0, pady=4)
            var = tk.StringVar(value=default)
            e = tk.Entry(parent, textvariable=var, bg="#1a1a1a", fg="#00ff88",
                         insertbackground="#00ff88", font=("Courier New", 10),
                         relief="flat", bd=4, width=28)
            e.grid(row=row, column=1, pady=4, padx=6)
            return var

        self.var_email_prefix = row(cfg, "Email prefix:", "name", 0)
        self.var_email_domain = row(cfg, "Email domain:", "@lvcmail24h.com", 1)
        self.var_email_start  = row(cfg, "Index bắt đầu:", "0", 2)
        self.var_email_end    = row(cfg, "Index kết thúc:", "999", 3)
        self.var_password     = row(cfg, "Password:", "123456!@#", 4)
        self.var_chrome_ver   = row(cfg, "Chrome version:", "146", 5)

        # # Checkbox Ẩn/Hiện Chrome
        # hide_frame = tk.Frame(self, bg="#0f0f0f")
        # hide_frame.pack(pady=5)
        
        # self.hide_check = tk.Checkbutton(hide_frame, 
        #                                  text="🔒 An cua so Chrome (chay ngam) - Tich vao de an", 
        #                                  variable=self.hide_window,
        #                                  bg="#0f0f0f", 
        #                                  fg="#00ff88", 
        #                                  selectcolor="#0f0f0f",
        #                                  font=("Courier New", 9),
        #                                  activebackground="#0f0f0f",
        #                                  activeforeground="#00ff88")
        # self.hide_check.pack()

        tk.Label(self, text="─" * 60, bg="#0f0f0f", fg="#333").pack()

        # Buttons
        btn_frame = tk.Frame(self, bg="#0f0f0f")
        btn_frame.pack(pady=10)

        self.btn_start = tk.Button(btn_frame, text="▶  START", command=self._start,
                                   bg="#00ff88", fg="#0f0f0f", font=("Courier New", 11, "bold"),
                                   relief="flat", padx=20, pady=8, cursor="hand2")
        self.btn_start.grid(row=0, column=0, padx=8)

        self.btn_stop = tk.Button(btn_frame, text="■  STOP", command=self._stop,
                                  bg="#ff4455", fg="white", font=("Courier New", 11, "bold"),
                                  relief="flat", padx=20, pady=8, cursor="hand2", state="disabled")
        self.btn_stop.grid(row=0, column=1, padx=8)

        self.btn_accounts = tk.Button(btn_frame, text="📄 accounts.txt", command=self._open_accounts,
                                      bg="#1a1a1a", fg="#00ff88", font=("Courier New", 10),
                                      relief="flat", padx=14, pady=8, cursor="hand2")
        self.btn_accounts.grid(row=0, column=2, padx=8)

        # Status
        self.lbl_status = tk.Label(self, text="● IDLE", font=("Courier New", 10, "bold"),
                                   bg="#0f0f0f", fg="#555")
        self.lbl_status.pack()

        # Log box
        tk.Label(self, text="─" * 60, bg="#0f0f0f", fg="#333").pack()
        self.log = scrolledtext.ScrolledText(self, height=14, bg="#0d0d0d", fg="#ccc",
                                             font=("Courier New", 9), relief="flat",
                                             insertbackground="white", state="disabled")
        self.log.pack(padx=16, pady=8, fill="both")

        # Counter
        self.lbl_count = tk.Label(self, text="Accounts tao: 0", font=("Courier New", 10),
                                  bg="#0f0f0f", fg="#555")
        self.lbl_count.pack(pady=(0, 10))

        self.count = 0

    def log_msg(self, msg):
        self.log.configure(state="normal")
        self.log.insert("end", msg + "\n")
        self.log.see("end")
        self.log.configure(state="disabled")

    def set_status(self, text, color="#00ff88"):
        self.lbl_status.configure(text=f"● {text}", fg=color)

    def _open_accounts(self):
        if os.path.exists(ACCOUNTS_FILE):
            os.startfile(ACCOUNTS_FILE)
        else:
            messagebox.showinfo("Thong bao", "Chua co file accounts.txt!")

    def _show_captcha_window(self):
        done = threading.Event()

        def popup():
            win = tk.Toplevel(self)
            win.title("Xac thuc Captcha")
            win.geometry("340x160")
            win.configure(bg="#1a1a1a")
            win.attributes("-topmost", True)

            tk.Label(win, text="Cloudflare Captcha phat hien!",
                     bg="#1a1a1a", fg="#ffaa00", font=("Courier New", 11, "bold")).pack(pady=(20, 6))
            tk.Label(win, text="Hay tich captcha tren Chrome roi bam Done.",
                     bg="#1a1a1a", fg="#ccc", font=("Courier New", 9)).pack(pady=4)

            def on_done():
                done.set()
                win.destroy()
                if self.hide_window.get():
                    hide_chrome()

            tk.Button(win, text="Done - Da tich xong", command=on_done,
                      bg="#00ff88", fg="#0f0f0f", font=("Courier New", 10, "bold"),
                      relief="flat", padx=16, pady=8, cursor="hand2").pack(pady=14)

        self.after(0, popup)
        
        if self.hide_window.get():
            show_chrome()
        
        done.wait()

    def check_cloudflare_page(self, driver):
        time.sleep(1)
        current_url = driver.current_url

        if "challenges.cloudflare.com" in current_url or "cdn-cgi" in current_url:
            return True

        try:
            driver.find_element(By.XPATH, '//*[contains(text(), "Verify to continue")]')
            return True
        except:
            return False

    def _start(self):
        try:
            int(self.var_email_start.get())
            int(self.var_email_end.get())
            int(self.var_chrome_ver.get())
        except ValueError:
            messagebox.showerror("Loi", "Index va Chrome version phai la so!")
            return

        self.running = True
        self.btn_start.configure(state="disabled")
        self.btn_stop.configure(state="normal")
        self.set_status("RUNNING")
        self.thread = threading.Thread(target=self._run, daemon=True)
        self.thread.start()

    def _stop(self):
        self.running = False
        self.set_status("STOPPING...", "#ffaa00")
        self.btn_stop.configure(state="disabled")

    def _run(self):
        try:
            chrome_ver = int(self.var_chrome_ver.get())
            prefix = self.var_email_prefix.get()
            domain = self.var_email_domain.get()
            password = self.var_password.get()
            email_index = int(self.var_email_start.get())
            email_end = int(self.var_email_end.get())

            options = uc.ChromeOptions()
            options.add_argument("--disable-blink-features=AutomationControlled")
            options.add_argument("--start-maximized")
            options.add_argument("--no-sandbox")
            options.add_argument("--disable-dev-shm-usage")

            prefs = {
                "credentials_enable_service": False,
                "profile.password_manager_enabled": False,
                "profile.default_content_setting_values.notifications": 2
            }
            options.add_experimental_option("prefs", prefs)

            self.driver = uc.Chrome(version_main=chrome_ver, options=options)
            driver = self.driver
            wait = WebDriverWait(driver, 60)
            wait_short = WebDriverWait(driver, 3)
            wait_120 = WebDriverWait(driver, 120)

            CAPTCHA_XPATH = '//*[@id="mIyT8"]/div/label/input'
            EMAIL_XPATH = '//*[@id="email_login"]'

            driver.get("https://vimeo.com/join")
            
            time.sleep(2)
            if self.hide_window.get():
                hide_chrome()
                self.log_msg("Da an cua so Chrome (chay ngam)")
            else:
                self.log_msg("Che do hien thi Chrome (khong an)")

            while self.running and email_index <= email_end:
                self.log_msg(f"\n=== START LOOP index {email_index} ===")
                
                current_email = f"{prefix}{email_index}{domain}"
                email_valid = False
                
                # Thu email hien tai
                while True:
                    self.log_msg(f"\nDang thu email: {current_email}")
                    
                    # Kiem tra captcha
                    self.log_msg("[1] Dang kiem tra captcha...")
                    if self.check_cloudflare_page(driver):
                        self.log_msg("Cloudflare - can tich tay!")
                        self._show_captcha_window()
                    
                    try:
                        captcha_checkbox = wait_short.until(EC.element_to_be_clickable((By.XPATH, CAPTCHA_XPATH)))
                        captcha_checkbox.click()
                        self.log_msg("[OK] Da tick captcha!")
                        time.sleep(2)
                    except TimeoutException:
                        self.log_msg("[BO QUA] Khong co captcha")

                    # Cho o email xuat hien
                    self.log_msg("[2] Dang cho o email (toi da 120s)...")
                    try:
                        email_input = wait_120.until(EC.element_to_be_clickable((By.XPATH, EMAIL_XPATH)))
                        self.log_msg("[OK] Da tim thay o email!")
                    except TimeoutException:
                        self.log_msg("[LOI] Khong tim thay o email sau 120s, dang refresh...")
                        driver.refresh()
                        time.sleep(3)
                        continue

                    # Dien email
                    email_input.clear()
                    email_input.send_keys(current_email)
                    self.log_msg(f"[3] Dang dung email: {current_email}")

                    # Click submit lan 1
                    submit_btn = wait.until(EC.element_to_be_clickable((By.XPATH, '//*[@id="__next"]/div[2]/div/div[1]/div[2]/section/form[2]/button')))
                    submit_btn.click()

                    # Kiem tra co sang buoc nhap ten khong
                    try:
                        name_input = WebDriverWait(driver, 5).until(
                            EC.presence_of_element_located((By.XPATH, '//*[@id="name"]'))
                        )
                        self.log_msg("[OK] EMAIL HOP LE! Sang duoc trang nhap ten")
                        email_valid = True
                        break

                    except TimeoutException:
                        self.log_msg(f"[TON TAI] Email {current_email} da duoc su dung, khong the dang ky")
                        email_index += 1
                        driver.get("https://vimeo.com/join")
                        break
                
                if not email_valid:
                    continue

                # ===== DANG KY TAI KHOAN =====
                self.log_msg("\n=== BAT DAU DANG KY TAI KHOAN ===")
                
                random_name = ''.join(random.choices(string.ascii_letters, k=6))
                name_input = wait.until(EC.element_to_be_clickable((By.XPATH, '//*[@id="name"]')))
                name_input.click()
                name_input.send_keys(random_name)
                self.log_msg(f"[4] Ten: {random_name}")

                password_input = wait.until(EC.element_to_be_clickable((By.XPATH, '//*[@id="password_login"]')))
                password_input.click()
                password_input.send_keys(password)
                self.log_msg("[5] Da dien password")

                confirm_input = wait.until(EC.element_to_be_clickable((By.XPATH, '//*[@id="confirm_password_login"]')))
                confirm_input.click()
                confirm_input.send_keys(password)
                self.log_msg("[6] Da dien xac nhan password")

                checkbox = wait.until(EC.element_to_be_clickable((By.XPATH, '//*[@id="__next"]/div[2]/div/div[1]/div[2]/section/form/section[1]/label/span[1]')))
                checkbox.click()
                self.log_msg("[7] Da tick checkbox")

                submit_final = wait.until(EC.element_to_be_clickable((By.XPATH, '//*[@id="__next"]/div[2]/div/div[1]/div[2]/section/form/section[3]/button')))
                submit_final.click()
                self.log_msg("[8] Da submit lan cuoi")
                
                self.log_msg("[9] Dang chuyen ve trang chu Vimeo...")
                driver.get("https://vimeo.com/")
                
                if "vimeo.com" in driver.current_url and "join" not in driver.current_url:
                    self.log_msg("[OK] Da ve trang chu thanh cong")
                else:
                    self.log_msg("[CANH BAO] Co the chua ve dung trang chu")

                with open(ACCOUNTS_FILE, "a", encoding='utf-8') as f:
                    f.write(f"{current_email}|{password}\n")
                self.log_msg(f"[DA LUU] Tao tai khoan thanh cong: {current_email}")

                self.count += 1
                self.after(0, lambda c=self.count: self.lbl_count.configure(text=f"Accounts tao: {c}"))

                # ===== TEST LAI EMAIL VUA TAO =====
                self.log_msg("\n=== TEST LAI EMAIL VUA TAO ===")
                driver.get("https://vimeo.com/join")
                
                test_success = False
                test_attempt = 0
                retry_create_count = 0
                
                while not test_success and self.running:
                    test_attempt += 1
                    self.log_msg(f"\n[TEST LAN {test_attempt}] Kiem tra email: {current_email}")
                    
                    try:
                        captcha_checkbox = wait_short.until(EC.element_to_be_clickable((By.XPATH, CAPTCHA_XPATH)))
                        captcha_checkbox.click()
                        self.log_msg("[OK] Da tick captcha!")
                    except TimeoutException:
                        self.log_msg("[BO QUA] Khong co captcha")
                    
                    try:
                        email_input = wait_120.until(EC.element_to_be_clickable((By.XPATH, EMAIL_XPATH)))
                        self.log_msg("[OK] Da tim thay o email")
                    except TimeoutException:
                        self.log_msg("[LOI] Khong tim thay o email, refresh...")
                        driver.refresh()
                        time.sleep(3)
                        continue
                    
                    email_input.clear()
                    email_input.send_keys(current_email)
                    self.log_msg(f"[TEST] Dang dung email: {current_email}")
                    
                    submit_btn = wait.until(EC.element_to_be_clickable((By.XPATH, '//*[@id="__next"]/div[2]/div/div[1]/div[2]/section/form[2]/button')))
                    submit_btn.click()
                    
                    try:
                        name_input_test = WebDriverWait(driver, 5).until(
                            EC.presence_of_element_located((By.XPATH, '//*[@id="name"]'))
                        )
                        retry_create_count += 1
                        self.log_msg(f"[CHUA TAO] Email {current_email} van co the dang ky (lan that bai thu {retry_create_count})")
                        
                        if retry_create_count >= 3:
                            self.log_error("\n" + "="*50)
                            self.log_error("[ERROR] DA TAO LAI 3 LAN VAN THAT BAI!")
                            self.log_error("[ERROR] EMAIL VAN SANG DUOC TRANG NHAP TEN")
                            self.log_error("[ERROR] KHA NANG CAO IP/PROXY DA BI CHAN")
                            self.log_error("[ERROR] VUI LONG DOI PROXY VA CHAY LAI CHUONG TRINH")
                            self.log_error("="*50)
                            
                            with open(ERROR_PROXY_FILE, "a", encoding='utf-8') as f:
                                f.write(f"{time.strftime('%Y-%m-%d %H:%M:%S')} - Can doi proxy - Email that bai: {current_email}\n")
                            
                            self.running = False
                            break
                        
                        self.log_msg(f"[TAO LAI LAN {retry_create_count}] Dang tao lai tai khoan...")
                        random_name_new = ''.join(random.choices(string.ascii_letters, k=6))
                        name_input_test.click()
                        name_input_test.send_keys(random_name_new)
                        self.log_msg(f"[TAO LAI] Ten moi: {random_name_new}")
                        
                        password_input_test = wait.until(EC.element_to_be_clickable((By.XPATH, '//*[@id="password_login"]')))
                        password_input_test.click()
                        password_input_test.send_keys(password)
                        
                        confirm_input_test = wait.until(EC.element_to_be_clickable((By.XPATH, '//*[@id="confirm_password_login"]')))
                        confirm_input_test.click()
                        confirm_input_test.send_keys(password)
                        
                        checkbox_test = wait.until(EC.element_to_be_clickable((By.XPATH, '//*[@id="__next"]/div[2]/div/div[1]/div[2]/section/form/section[1]/label/span[1]')))
                        checkbox_test.click()
                        
                        submit_final_test = wait.until(EC.element_to_be_clickable((By.XPATH, '//*[@id="__next"]/div[2]/div/div[1]/div[2]/section/form/section[3]/button')))
                        submit_final_test.click()
                        
                        self.log_msg("[TAO LAI THANH CONG]")
                        driver.get("https://vimeo.com/")
                        
                        self.log_msg("\n[TEST LAI SAU KHI TAO LAI] Quay lai trang join de test tiep...")
                        driver.get("https://vimeo.com/join")
                        
                    except TimeoutException:
                        self.log_msg(f"[OK] Email {current_email} da ton tai, khong the dang ky lai")
                        self.log_msg("[KET LUAN] Tai khoan da duoc tao thanh cong")
                        test_success = True
                        break
                
                if not self.running:
                    break
                
                self.log_msg(f"\n[CHUYEN] Sang email tiep theo: {prefix}{email_index + 1}{domain}")
                email_index += 1
                driver.get("https://vimeo.com/join")
                
                if self.hide_window.get():
                    hide_chrome()

            self.log_msg("\n=== HOAN THANH TAT CA EMAIL ===")

        except Exception as e:
            self.log_msg(f"LOI: {e}")

        finally:
            try:
                if self.driver:
                    self.driver.quit()
            except:
                pass

            self.running = False
            self.after(0, self._on_done)

    def _on_done(self):
        self.btn_start.configure(state="normal")
        self.btn_stop.configure(state="disabled")
        self.set_status("DONE", "#ffaa00")
        self.log_msg("─── Ket thuc ───")


if __name__ == "__main__":
    app = App()
    app.mainloop()