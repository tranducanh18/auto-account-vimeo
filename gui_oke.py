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

if getattr(sys, 'frozen', False):
    BASE_DIR = os.path.dirname(sys.executable)
else:
    BASE_DIR = os.path.dirname(os.path.abspath(__file__))

ACCOUNTS_FILE     = os.path.join(BASE_DIR, "accounts.txt")
EMAIL_FAILED_FILE = os.path.join(BASE_DIR, "email_failed.txt")
ERROR_PROXY_FILE  = os.path.join(BASE_DIR, "error_proxy.txt")


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

    # ── Chrome size helpers ──────────────────────────────────────────
    def _minimize_chrome(self, driver):
        """Thu nhỏ Chrome xuống 1x1 pixel góc màn hình"""
        try:
            driver.execute_script("window.moveTo(0, 0); window.resizeTo(1, 1);")
        except:
            pass

    def _maximize_chrome(self, driver):
        """Phóng to Chrome để user thao tác captcha"""
        try:
            driver.execute_script("window.moveTo(100, 50); window.resizeTo(1280, 800);")
        except:
            pass

    # ── JS helpers ──────────────────────────────────────────────────
    def js_input(self, driver, element, value):
        driver.execute_script("""
            var el = arguments[0], val = arguments[1];
            var setter = Object.getOwnPropertyDescriptor(
                window.HTMLInputElement.prototype, 'value').set;
            setter.call(el, val);
            el.dispatchEvent(new Event('input',  { bubbles: true }));
            el.dispatchEvent(new Event('change', { bubbles: true }));
        """, element, value)

    def js_click(self, driver, element):
        driver.execute_script("arguments[0].click();", element)

    def wait_el(self, driver, xpath, timeout=60):
        return WebDriverWait(driver, timeout).until(
            EC.presence_of_element_located((By.XPATH, xpath))
        )

    # ── UI ───────────────────────────────────────────────────────────
    def log_error(self, msg):
        self.log.configure(state="normal")
        self.log.insert("end", msg + "\n", "error")
        self.log.tag_config("error", foreground="#ff4455")
        self.log.see("end")
        self.log.configure(state="disabled")

    def _build_ui(self):
        tk.Label(self, text="VIMEO AUTO TOOL", font=("Courier New", 18, "bold"),
                 bg="#0f0f0f", fg="#00ff88").pack(pady=(18, 2))
        tk.Label(self, text="─" * 60, bg="#0f0f0f", fg="#333").pack()

        cfg = tk.Frame(self, bg="#0f0f0f")
        cfg.pack(padx=24, pady=10, fill="x")

        def row(parent, label, default, r):
            tk.Label(parent, text=label, bg="#0f0f0f", fg="#aaa",
                     font=("Courier New", 10), width=18, anchor="w").grid(row=r, column=0, pady=4)
            var = tk.StringVar(value=default)
            tk.Entry(parent, textvariable=var, bg="#1a1a1a", fg="#00ff88",
                     insertbackground="#00ff88", font=("Courier New", 10),
                     relief="flat", bd=4, width=28).grid(row=r, column=1, pady=4, padx=6)
            return var

        self.var_email_prefix = row(cfg, "Email prefix:",   "name",            0)
        self.var_email_domain = row(cfg, "Email domain:",   "@lvcmail24h.com", 1)
        self.var_email_start  = row(cfg, "Index bat dau:",  "0",               2)
        self.var_email_end    = row(cfg, "Index ket thuc:", "999",             3)
        self.var_password     = row(cfg, "Password:",       "123456!@#",       4)
        self.var_chrome_ver   = row(cfg, "Chrome version:", "146",             5)

        hide_frame = tk.Frame(self, bg="#0f0f0f")
        hide_frame.pack(pady=5)
        tk.Checkbutton(hide_frame,
                       text="🔒 An cua so Chrome (chay ngam) - Tich vao de an",
                       variable=self.hide_window,
                       bg="#0f0f0f", fg="#00ff88", selectcolor="#0f0f0f",
                       font=("Courier New", 9),
                       activebackground="#0f0f0f", activeforeground="#00ff88").pack()

        tk.Label(self, text="─" * 60, bg="#0f0f0f", fg="#333").pack()

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

        self.lbl_status = tk.Label(self, text="● IDLE", font=("Courier New", 10, "bold"),
                                   bg="#0f0f0f", fg="#555")
        self.lbl_status.pack()

        tk.Label(self, text="─" * 60, bg="#0f0f0f", fg="#333").pack()
        self.log = scrolledtext.ScrolledText(self, height=14, bg="#0d0d0d", fg="#ccc",
                                             font=("Courier New", 9), relief="flat",
                                             insertbackground="white", state="disabled")
        self.log.pack(padx=16, pady=8, fill="both")

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

    def _show_captcha_window(self, driver):
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
                    self._minimize_chrome(driver)

            tk.Button(win, text="Done - Da tich xong", command=on_done,
                      bg="#00ff88", fg="#0f0f0f", font=("Courier New", 10, "bold"),
                      relief="flat", padx=16, pady=8, cursor="hand2").pack(pady=14)

        self._maximize_chrome(driver)
        self.after(0, popup)
        done.wait()

    def check_cloudflare_page(self, driver):
        url = driver.current_url
        if "challenges.cloudflare.com" in url or "cdn-cgi" in url:
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
            chrome_ver  = int(self.var_chrome_ver.get())
            prefix      = self.var_email_prefix.get()
            domain      = self.var_email_domain.get()
            password    = self.var_password.get()
            email_index = int(self.var_email_start.get())
            email_end   = int(self.var_email_end.get())

            options = uc.ChromeOptions()
            options.add_argument("--disable-blink-features=AutomationControlled")
            options.add_argument("--no-sandbox")
            options.add_argument("--disable-dev-shm-usage")
            # Khởi động Chrome nhỏ 1x1 pixel ngay từ đầu
            options.add_argument("--window-size=1,1")
            options.add_argument("--window-position=0,0")

            prefs = {
                "credentials_enable_service": False,
                "profile.password_manager_enabled": False,
                "profile.default_content_setting_values.notifications": 2
            }
            options.add_experimental_option("prefs", prefs)

            self.driver = uc.Chrome(version_main=chrome_ver, options=options)
            driver = self.driver

            CAPTCHA_XPATH      = '//*[@id="mIyT8"]/div/label/input'
            EMAIL_XPATH        = '//*[@id="email_login"]'
            NAME_XPATH         = '//*[@id="name"]'
            PASSWORD_XPATH     = '//*[@id="password_login"]'
            CONFIRM_XPATH      = '//*[@id="confirm_password_login"]'
            CHECKBOX_XPATH     = '//*[@id="__next"]/div[2]/div/div[1]/div[2]/section/form/section[1]/label/span[1]'
            SUBMIT1_XPATH      = '//*[@id="__next"]/div[2]/div/div[1]/div[2]/section/form[2]/button'
            SUBMIT_FINAL_XPATH = '//*[@id="__next"]/div[2]/div/div[1]/div[2]/section/form/section[3]/button'

            driver.get("https://vimeo.com/join")

            if self.hide_window.get():
                self._minimize_chrome(driver)
                self.log_msg("Chrome dang chay nho 1x1 pixel (khong chiem man hinh)")
            else:
                self._maximize_chrome(driver)
                self.log_msg("Chrome hien thi binh thuong")

            while self.running and email_index <= email_end:
                self.log_msg(f"\n=== START LOOP index {email_index} ===")
                current_email = f"{prefix}{email_index}{domain}"
                email_valid = False

                while True:
                    self.log_msg(f"\nDang thu email: {current_email}")
                    self.log_msg("[1] Kiem tra captcha...")

                    if self.check_cloudflare_page(driver):
                        self.log_msg("Cloudflare - can tich tay!")
                        self._show_captcha_window(driver)

                    try:
                        cap_el = WebDriverWait(driver, 3).until(
                            EC.presence_of_element_located((By.XPATH, CAPTCHA_XPATH)))
                        self.js_click(driver, cap_el)
                        self.log_msg("[OK] Da tick captcha!")
                        time.sleep(2)
                    except TimeoutException:
                        self.log_msg("[BO QUA] Khong co captcha")

                    self.log_msg("[2] Cho o email (120s)...")
                    try:
                        email_el = self.wait_el(driver, EMAIL_XPATH, 120)
                        self.log_msg("[OK] Tim thay o email!")
                    except TimeoutException:
                        self.log_msg("[LOI] Khong tim thay o email, refresh...")
                        driver.refresh()
                        continue

                    self.js_input(driver, email_el, current_email)
                    self.log_msg(f"[3] Da dien email: {current_email}")

                    try:
                        sub1 = self.wait_el(driver, SUBMIT1_XPATH, 60)
                        self.js_click(driver, sub1)
                    except TimeoutException:
                        driver.refresh()
                        continue

                    try:
                        self.wait_el(driver, NAME_XPATH, 5)
                        self.log_msg("[OK] EMAIL HOP LE!")
                        email_valid = True
                        break
                    except TimeoutException:
                        self.log_msg(f"[TON TAI] {current_email} da ton tai")
                        email_index += 1
                        current_email = f"{prefix}{email_index}{domain}"
                        driver.get("https://vimeo.com/join")
                        break

                if not email_valid:
                    continue

                self.log_msg("\n=== BAT DAU DANG KY ===")
                random_name = ''.join(random.choices(string.ascii_letters, k=6))

                self.log_msg("[4] Dien ten...")
                name_el = self.wait_el(driver, NAME_XPATH, 60)
                self.js_input(driver, name_el, random_name)
                self.log_msg(f"[4] Ten: {random_name}")

                self.log_msg("[5] Dien password...")
                pw_el = self.wait_el(driver, PASSWORD_XPATH, 60)
                self.js_input(driver, pw_el, password)
                self.log_msg("[5] OK!")

                self.log_msg("[6] Dien confirm password...")
                cf_el = self.wait_el(driver, CONFIRM_XPATH, 60)
                self.js_input(driver, cf_el, password)
                self.log_msg("[6] OK!")

                self.log_msg("[7] Tick checkbox...")
                cb_el = self.wait_el(driver, CHECKBOX_XPATH, 60)
                self.js_click(driver, cb_el)
                self.log_msg("[7] OK!")

                self.log_msg("[8] Submit...")
                sf_el = self.wait_el(driver, SUBMIT_FINAL_XPATH, 60)
                self.js_click(driver, sf_el)
                self.log_msg("[8] OK!")

                driver.get("https://vimeo.com/")

                if "vimeo.com" in driver.current_url and "join" not in driver.current_url:
                    self.log_msg("[OK] Da ve trang chu!")
                else:
                    self.log_msg("[CANH BAO] Co the chua ve dung trang chu")

                with open(ACCOUNTS_FILE, "a", encoding="utf-8") as f:
                    f.write(f"{current_email}|{password}\n")
                self.log_msg(f"[DA LUU] {current_email}")

                self.count += 1
                self.after(0, lambda c=self.count: self.lbl_count.configure(text=f"Accounts tao: {c}"))

                self.log_msg("\n=== TEST LAI EMAIL ===")
                driver.get("https://vimeo.com/join")

                test_success = False
                test_attempt = 0
                retry_create_count = 0

                while not test_success and self.running:
                    test_attempt += 1
                    self.log_msg(f"\n[TEST LAN {test_attempt}] {current_email}")

                    try:
                        cap_el = WebDriverWait(driver, 3).until(
                            EC.presence_of_element_located((By.XPATH, CAPTCHA_XPATH)))
                        self.js_click(driver, cap_el)
                        self.log_msg("[OK] Da tick captcha!")
                    except TimeoutException:
                        self.log_msg("[BO QUA] Khong co captcha")

                    try:
                        email_el = self.wait_el(driver, EMAIL_XPATH, 120)
                    except TimeoutException:
                        driver.refresh()
                        continue

                    self.js_input(driver, email_el, current_email)

                    try:
                        sub1 = self.wait_el(driver, SUBMIT1_XPATH, 60)
                        self.js_click(driver, sub1)
                    except TimeoutException:
                        driver.refresh()
                        continue

                    try:
                        name_test = self.wait_el(driver, NAME_XPATH, 5)
                        retry_create_count += 1
                        self.log_msg(f"[CHUA TAO] Van co the dang ky (lan {retry_create_count})")

                        if retry_create_count >= 3:
                            self.log_error("=" * 50)
                            self.log_error("[ERROR] DA TAO LAI 3 LAN VAN THAT BAI!")
                            self.log_error("[ERROR] KHA NANG CAO IP/PROXY DA BI CHAN")
                            self.log_error("[ERROR] VUI LONG DOI PROXY VA CHAY LAI")
                            self.log_error("=" * 50)
                            with open(ERROR_PROXY_FILE, "a", encoding="utf-8") as f:
                                f.write(f"{time.strftime('%Y-%m-%d %H:%M:%S')} - {current_email}\n")
                            self.running = False
                            break

                        self.log_msg(f"[TAO LAI LAN {retry_create_count}]...")
                        rn = ''.join(random.choices(string.ascii_letters, k=6))
                        self.js_input(driver, name_test, rn)

                        pw2 = self.wait_el(driver, PASSWORD_XPATH, 60)
                        self.js_input(driver, pw2, password)

                        cf2 = self.wait_el(driver, CONFIRM_XPATH, 60)
                        self.js_input(driver, cf2, password)

                        cb2 = self.wait_el(driver, CHECKBOX_XPATH, 60)
                        self.js_click(driver, cb2)

                        sf2 = self.wait_el(driver, SUBMIT_FINAL_XPATH, 60)
                        self.js_click(driver, sf2)

                        self.log_msg("[TAO LAI THANH CONG]")
                        driver.get("https://vimeo.com/")
                        driver.get("https://vimeo.com/join")

                    except TimeoutException:
                        self.log_msg("[OK] Email da ton tai - Tai khoan tao thanh cong!")
                        test_success = True
                        break

                if not self.running:
                    break

                self.log_msg(f"\n[CHUYEN] Sang index {email_index + 1}")
                email_index += 1
                driver.get("https://vimeo.com/join")

                if self.hide_window.get():
                    self._minimize_chrome(driver)

            self.log_msg("\n=== HOAN THANH ===")

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