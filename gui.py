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

# ── Đường dẫn file cùng thư mục với script ───────────────────────────────────
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
ACCOUNTS_FILE = os.path.join(BASE_DIR, "accounts.txt")
EMAIL_FAILED_FILE = os.path.join(BASE_DIR, "email_failed.txt")

# ════════════════════════════════════════════════════════════════════════════
#  GUI
# ════════════════════════════════════════════════════════════════════════════
class App(tk.Tk):
    def __init__(self):
        super().__init__()
        self.title("Vimeo Auto Tool for ducanh")
        self.geometry("600x620")
        self.resizable(False, False)
        self.configure(bg="#0f0f0f")

        self.driver = None
        self.running = False
        self.thread = None

        self._build_ui()

    # ── Build UI ─────────────────────────────────────────────────────────
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

        self.var_email_prefix = row(cfg, "Email prefix:", "Tên muốn đặt", 0)
        self.var_email_domain = row(cfg, "Email domain:", "@lvcmail24h.com", 1)
        self.var_email_start  = row(cfg, "Index bắt đầu:", "0", 2)
        self.var_email_end    = row(cfg, "Index kết thúc:", "9999", 3)
        self.var_password     = row(cfg, "Password:", "123456!@#", 4)
        self.var_chrome_ver   = row(cfg, "Chrome version:", "0", 5)

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
        self.lbl_count = tk.Label(self, text="Accounts tạo: 0", font=("Courier New", 10),
                                  bg="#0f0f0f", fg="#555")
        self.lbl_count.pack(pady=(0, 10))

        self.count = 0

    # ── Helpers ──────────────────────────────────────────────────────────
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
            messagebox.showinfo("Thông báo", "Chưa có file accounts.txt!")

    # ── Start / Stop ─────────────────────────────────────────────────────
    def _start(self):
        try:
            int(self.var_email_start.get())
            int(self.var_email_end.get())
            int(self.var_chrome_ver.get())
        except ValueError:
            messagebox.showerror("Lỗi", "Index và Chrome version phải là số!")
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

    # ── Bot logic ─────────────────────────────────────────────────────────
    def _run(self):
        try:
            chrome_ver = int(self.var_chrome_ver.get())
            prefix = self.var_email_prefix.get()
            domain = self.var_email_domain.get()
            password = self.var_password.get()
            email_index = int(self.var_email_start.get())
            email_end = int(self.var_email_end.get())

            # Chrome options
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

            # XPath constants
            CAPTCHA_XPATH = '//*[@id="mIyT8"]/div/label/input'
            EMAIL_XPATH = '//*[@id="email_login"]'

            driver.get("https://vimeo.com/join")

            while self.running and email_index <= email_end:
                self.log_msg(f"\n🔄 Bắt đầu vòng lặp mới — index {email_index}")

                # Bước 1: Kiểm tra captcha
                self.log_msg("🔍 Kiểm tra captcha...")
                try:
                    captcha_checkbox = wait_short.until(EC.element_to_be_clickable((By.XPATH, CAPTCHA_XPATH)))
                    captcha_checkbox.click()
                    self.log_msg("✅ Đã tích captcha!")
                    time.sleep(2)
                except TimeoutException:
                    self.log_msg("⏭️ Không có captcha, bỏ qua!")

                # Bước 2: Chờ ô email
                self.log_msg("⏳ Chờ ô email xuất hiện (tối đa 120s)...")
                try:
                    email_input = wait_120.until(EC.element_to_be_clickable((By.XPATH, EMAIL_XPATH)))
                    self.log_msg("✅ Ô email đã xuất hiện!")
                except TimeoutException:
                    self.log_msg("❌ Không tìm thấy ô email sau 120s, dừng tool...")
                    break

                # Bước 3: Điền email
                email = f"{prefix}{email_index}{domain}"
                email_input.send_keys(email)
                self.log_msg(f"📧 Email đang dùng: {email}")

                # Bước 4: Click Submit lần 1
                submit_btn = wait.until(EC.element_to_be_clickable((By.XPATH, '//*[@id="__next"]/div[2]/div/div[1]/div[2]/section/form[2]/button')))
                submit_btn.click()

                # Kiểm tra email hợp lệ
                try:
                    name_input = WebDriverWait(driver, 5).until(
                        EC.presence_of_element_located((By.XPATH, '//*[@id="name"]'))
                    )
                    self.log_msg("✅ Email hợp lệ, tiếp tục...")

                except TimeoutException:
                    current_url = driver.current_url
                    if "vimeo.com" in current_url and "join" not in current_url:
                        self.log_msg(f"⚠️ Email {email} đã tồn tại hoặc bị lỗi, quay về trang chủ Vimeo")
                    else:
                        self.log_msg(f"❌ Email lỗi hoặc đã tồn tại: {email}")
                    
                    # Lưu email bị lỗi
                    with open(EMAIL_FAILED_FILE, "a") as f:
                        f.write(f"{email} - {time.strftime('%Y-%m-%d %H:%M:%S')}\n")
                    
                    email_index += 1
                    driver.get("https://vimeo.com/join")
                    continue

                # Bước 5: Điền tên random
                random_name = ''.join(random.choices(string.ascii_letters, k=6))
                name_input = wait.until(EC.element_to_be_clickable((By.XPATH, '//*[@id="name"]')))
                name_input.click()
                name_input.send_keys(random_name)
                self.log_msg(f"✅ Đã điền tên: {random_name}")

                # Bước 6: Điền password
                password_input = wait.until(EC.element_to_be_clickable((By.XPATH, '//*[@id="password_login"]')))
                password_input.click()
                password_input.send_keys(password)
                self.log_msg("✅ Đã điền password")

                # Bước 7: Điền confirm password
                confirm_input = wait.until(EC.element_to_be_clickable((By.XPATH, '//*[@id="confirm_password_login"]')))
                confirm_input.click()
                confirm_input.send_keys(password)
                self.log_msg("✅ Đã điền confirm password")

                # Bước 8: Tích checkbox
                checkbox = wait.until(EC.element_to_be_clickable((By.XPATH, '//*[@id="__next"]/div[2]/div/div[1]/div[2]/section/form/section[1]/label/span[1]')))
                checkbox.click()
                self.log_msg("✅ Đã tích checkbox")

                # Bước 9: Click Submit lần 2
                submit_final = wait.until(EC.element_to_be_clickable((By.XPATH, '//*[@id="__next"]/div[2]/div/div[1]/div[2]/section/form/section[3]/button')))
                submit_final.click()
                self.log_msg("✅ Đã click Submit!")

                # Bước 10: Điều hướng về trang chủ
                self.log_msg("🌐 Điều hướng về trang chủ Vimeo...")
                driver.get("https://vimeo.com/")
                time.sleep(3)
                
                if "vimeo.com" in driver.current_url and "join" not in driver.current_url:
                    self.log_msg("✅ Đã điều hướng thành công về trang chủ Vimeo")
                else:
                    self.log_msg("⚠️ Có thể chưa về đúng trang chủ")

                # Lưu account thành công
                with open(ACCOUNTS_FILE, "a") as f:
                    f.write(f"{email}|{password}\n")
                self.log_msg(f"💾 Đã lưu account thành công: {email}")

                self.count += 1
                self.after(0, lambda c=self.count: self.lbl_count.configure(text=f"Accounts tạo: {c}"))

                # Quay lại trang join
                driver.get("https://vimeo.com/join")
                time.sleep(random.uniform(2, 5))
                email_index += 1

            self.log_msg("\n✅ Hoàn thành tất cả các email!")

        except Exception as e:
            self.log_msg(f"💥 LỖI: {e}")

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
        self.log_msg("─── Kết thúc ───")


if __name__ == "__main__":
    app = App()
    app.mainloop()