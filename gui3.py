import random
import string
import time
import threading
import subprocess
import glob
import shutil
import os
import sys
import tkinter as tk
from tkinter import scrolledtext, messagebox, filedialog

from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.common.exceptions import TimeoutException
import undetected_chromedriver as uc

# ── Paths ─────────────────────────────────────────────────────────────
if getattr(sys, 'frozen', False):
    BASE_DIR = os.path.dirname(sys.executable)
else:
    BASE_DIR = os.path.dirname(os.path.abspath(__file__))

ACCOUNTS_FILE     = os.path.join(BASE_DIR, "accounts.txt")
EMAIL_FAILED_FILE = os.path.join(BASE_DIR, "email_failed.txt")
ERROR_PROXY_FILE  = os.path.join(BASE_DIR, "error_proxy.txt")

# ── XPath constants ────────────────────────────────────────────────────
CAPTCHA_XPATH      = '//*[@id="mIyT8"]/div/label/input'
EMAIL_XPATH        = '//*[@id="email_login"]'
NAME_XPATH         = '//*[@id="name"]'
PASSWORD_XPATH     = '//*[@id="password_login"]'
CONFIRM_XPATH      = '//*[@id="confirm_password_login"]'
CHECKBOX_XPATH     = '//*[@id="__next"]/div[2]/div/div[1]/div[2]/section/form/section[1]/label/span[1]'
SUBMIT1_XPATH      = '//*[@id="__next"]/div[2]/div/div[1]/div[2]/section/form[2]/button'
SUBMIT_FINAL_XPATH = '//*[@id="__next"]/div[2]/div/div[1]/div[2]/section/form/section[3]/button'
EMAIL_EXISTS_XPATH = '//*[@id="__next"]/div[2]/div/div[1]/div[2]/section/form[2]/div[2]'
LOGGED_IN_XPATH    = '//*[@id="global-nav-2025-top-desktop"]/div/ul[3]/li[1]/a[2]'

# ── WireGuard helper (GIỮ NGUYÊN) ──────────────────────────────────────
class WireGuardManager:
    def __init__(self, conf_dir: str = "", log_fn=None):
        self.conf_dir    = conf_dir
        self.conf_files  : list[str] = []
        self.current_idx : int = 0
        self.active_name : str = ""
        self.log         = log_fn or print

        if sys.platform == "win32":
            self.mode = "win"
            found = shutil.which("wireguard")
            if not found:
                candidates = [
                    os.path.expandvars(r"%ProgramFiles%\WireGuard\wireguard.exe"),
                    os.path.expandvars(r"%ProgramFiles(x86)%\WireGuard\wireguard.exe"),
                    os.path.expandvars(r"%LocalAppData%\WireGuard\wireguard.exe"),
                ]
                found = next((p for p in candidates if os.path.isfile(p)), None)
            self.wg_exe = found or "wireguard"
        else:
            self.mode   = "unix"
            self.wg_exe = shutil.which("wg-quick") or shutil.which("wg") or "wg-quick"

    def load_configs(self, path: str):
        self.conf_dir = path
        if os.path.isdir(path):
            self.conf_files = sorted(glob.glob(os.path.join(path, "*.conf")))
            self.log(f"[WG] Tim thay {len(self.conf_files)} file .conf trong: {path}")
        elif os.path.isfile(path) and path.endswith(".conf"):
            self.conf_files = [path]
            self.log(f"[WG] Dung 1 file conf: {os.path.basename(path)}")
        else:
            self.conf_files = []
            self.log(f"[WG-WARN] Khong tim thay file .conf tai: {path}")
        self.current_idx = 0

    def _run(self, *args, timeout=20) -> bool:
        try:
            result = subprocess.run(list(args), capture_output=True, text=True, timeout=timeout)
            if result.returncode != 0:
                self.log(f"[WG-ERR] {result.stderr.strip()}")
                return False
            return True
        except Exception as e:
            self.log(f"[WG-EXC] {e}")
            return False

    def _tunnel_name(self, conf_path: str) -> str:
        return os.path.splitext(os.path.basename(conf_path))[0]

    def _tunnel_running(self, name: str) -> bool:
        try:
            r = subprocess.run(
                ["sc", "query", f"WireGuardTunnel${name}"],
                capture_output=True, text=True, timeout=5
            )
            return "RUNNING" in r.stdout
        except Exception:
            return False

    def _up(self, conf_path: str) -> bool:
        name = self._tunnel_name(conf_path)
        self.log(f"[WG] UP → {name}")

        if self.mode != "win":
            return self._run(self.wg_exe, "up", conf_path)

        if self._tunnel_running(name):
            self.log(f"[WG] Tunnel dang chay, down truoc...")
            self._win_run(self.wg_exe, "/uninstalltunnelservice", name)

        ok, err = self._win_run(self.wg_exe, "/installtunnelservice", conf_path)
        if ok:
            time.sleep(3)
            self.log(f"[WG] Tunnel UP thanh cong!")
            return True

        if "already installed" in err.lower() or "already running" in err.lower():
            self.log(f"[WG] Da ton tai, uninstall roi install lai...")
            self._win_run(self.wg_exe, "/uninstalltunnelservice", name)
            time.sleep(2)
            ok, err = self._win_run(self.wg_exe, "/installtunnelservice", conf_path)
            if ok:
                time.sleep(3)
                self.log(f"[WG] Tunnel UP thanh cong (lan 2)!")
                return True

        self.log(f"[WG-ERR] UP that bai: {err}")
        return False

    def _down(self, conf_path: str) -> bool:
        name = self._tunnel_name(conf_path)
        self.log(f"[WG] DOWN → {name}")

        if self.mode != "win":
            return self._run(self.wg_exe, "down", conf_path)

        ok, err = self._win_run(self.wg_exe, "/uninstalltunnelservice", name)
        if ok:
            self.log(f"[WG] Tunnel DOWN thanh cong!")
            return True
        if "not found" in err.lower() or "does not exist" in err.lower():
            return True
        self.log(f"[WG-ERR] DOWN that bai: {err}")
        return False

    def _win_run(self, *args, timeout=20) -> tuple[bool, str]:
        try:
            r = subprocess.run(list(args), capture_output=True, text=True, timeout=timeout)
            return r.returncode == 0, r.stderr.strip()
        except Exception as e:
            return False, str(e)

    def rotate(self) -> bool:
        if not self.conf_files:
            self.log("[WG] Khong co config nao – bo qua rotate")
            return False

        if self.active_name:
            active_conf = next(
                (c for c in self.conf_files if self._tunnel_name(c) == self.active_name),
                self.conf_files[(self.current_idx - 1) % len(self.conf_files)]
            )
            self._down(active_conf)
            time.sleep(1)

        next_conf = self.conf_files[self.current_idx % len(self.conf_files)]
        self.current_idx = (self.current_idx + 1) % len(self.conf_files)
        ok = self._up(next_conf)
        if ok:
            self.active_name = self._tunnel_name(next_conf)
            self.log(f"[WG] Active tunnel: {self.active_name}")
        return ok

    def shutdown(self):
        if self.active_name:
            active_conf = next(
                (c for c in self.conf_files if self._tunnel_name(c) == self.active_name),
                None
            )
            if active_conf:
                self._down(active_conf)


# ── Main App ──────────────────────────────────────────────────────────
class App(tk.Tk):
    def __init__(self):
        super().__init__()
        self.title("Vimeo Auto Tool – WireGuard Edition")
        self.geometry("640x820")
        self.resizable(False, False)
        self.configure(bg="#0f0f0f")
        self.driver      = None
        self.running     = False
        self.thread      = None
        self.hide_window = tk.BooleanVar(value=True)
        self.use_vpn     = tk.BooleanVar(value=False)
        self.wg          = WireGuardManager(log_fn=self.log_msg)
        self._build_ui()

    # ── Chrome helpers ───────────────────────────────────────────────
    def _minimize_chrome(self, driver):
        try:
            driver.execute_script("window.moveTo(0,0); window.resizeTo(1,1);")
        except:
            pass

    def _maximize_chrome(self, driver):
        try:
            driver.execute_script("window.moveTo(100,50); window.resizeTo(1280,800);")
        except:
            pass

    # ── JS helpers (NHANH HON) ───────────────────────────────────────
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

    def wait_clickable(self, driver, xpath, timeout=60):
        return WebDriverWait(driver, timeout).until(
            EC.element_to_be_clickable((By.XPATH, xpath))
        )

    # ── UI ───────────────────────────────────────────────────────────
    def _build_ui(self):
        tk.Label(self, text="VIMEO AUTO TOOL", font=("Courier New", 18, "bold"),
                 bg="#0f0f0f", fg="#00ff88").pack(pady=(18, 2))
        tk.Label(self, text="─"*62, bg="#0f0f0f", fg="#333").pack()

        cfg = tk.Frame(self, bg="#0f0f0f")
        cfg.pack(padx=24, pady=8, fill="x")

        def row(parent, label, default, r):
            tk.Label(parent, text=label, bg="#0f0f0f", fg="#aaa",
                     font=("Courier New", 10), width=18, anchor="w").grid(row=r, column=0, pady=3)
            var = tk.StringVar(value=default)
            tk.Entry(parent, textvariable=var, bg="#1a1a1a", fg="#00ff88",
                     insertbackground="#00ff88", font=("Courier New", 10),
                     relief="flat", bd=4, width=30).grid(row=r, column=1, pady=3, padx=6)
            return var

        self.var_email_prefix = row(cfg, "Email prefix:",   "name",            0)
        self.var_email_domain = row(cfg, "Email domain:",   "@lvcmail24h.com", 1)
        self.var_email_start  = row(cfg, "Index bat dau:",  "0",               2)
        self.var_email_end    = row(cfg, "Index ket thuc:", "999",             3)
        self.var_password     = row(cfg, "Password:",       "123456!@#",       4)
        self.var_chrome_ver   = row(cfg, "Chrome version:", "146",             5)

        tk.Label(self, text="─"*62, bg="#0f0f0f", fg="#333").pack()

        # ── WireGuard section ────────────────────────────────────────
        wg_frame = tk.Frame(self, bg="#141414", bd=0)
        wg_frame.pack(padx=16, pady=6, fill="x")

        tk.Label(wg_frame, text="⚡ WIREGUARD VPN", font=("Courier New", 10, "bold"),
                 bg="#141414", fg="#4db8ff").pack(anchor="w", padx=10, pady=(8,2))

        row_vpn = tk.Frame(wg_frame, bg="#141414")
        row_vpn.pack(fill="x", padx=10, pady=4)

        tk.Checkbutton(row_vpn, text="Bat VPN – doi IP sau moi email bi chan",
                       variable=self.use_vpn,
                       bg="#141414", fg="#4db8ff", selectcolor="#141414",
                       font=("Courier New", 9),
                       activebackground="#141414", activeforeground="#4db8ff",
                       command=self._on_vpn_toggle).pack(side="left")

        conf_row = tk.Frame(wg_frame, bg="#141414")
        conf_row.pack(fill="x", padx=10, pady=(0, 8))

        tk.Label(conf_row, text="WG conf dir/file:", bg="#141414", fg="#888",
                 font=("Courier New", 9), width=16, anchor="w").pack(side="left")

        self.var_wg_path = tk.StringVar(value="")
        self.ent_wg_path = tk.Entry(conf_row, textvariable=self.var_wg_path,
                                    bg="#1a1a1a", fg="#4db8ff",
                                    insertbackground="#4db8ff", font=("Courier New", 9),
                                    relief="flat", bd=3, width=26)
        self.ent_wg_path.pack(side="left", padx=4)

        tk.Button(conf_row, text="Browse", command=self._browse_wg,
                  bg="#223344", fg="#4db8ff", font=("Courier New", 8),
                  relief="flat", padx=6, pady=2, cursor="hand2").pack(side="left", padx=2)

        tk.Label(wg_frame,
                 text="⚠ Can chay tool voi quyen Admin (chuot phai → Run as administrator)",
                 bg="#141414", fg="#ffaa00", font=("Courier New", 8)).pack(anchor="w", padx=10)

        self.lbl_wg_status = tk.Label(wg_frame, text="● VPN: OFF",
                                      font=("Courier New", 9, "bold"),
                                      bg="#141414", fg="#555")
        self.lbl_wg_status.pack(anchor="w", padx=10, pady=(0, 6))

        tk.Label(self, text="─"*62, bg="#0f0f0f", fg="#333").pack()

        # ── Options ──────────────────────────────────────────────────
        opt_frame = tk.Frame(self, bg="#0f0f0f")
        opt_frame.pack(pady=4)
        tk.Checkbutton(opt_frame,
                       text="🔒 An cua so Chrome (chay ngam)",
                       variable=self.hide_window,
                       bg="#0f0f0f", fg="#00ff88", selectcolor="#0f0f0f",
                       font=("Courier New", 9),
                       activebackground="#0f0f0f", activeforeground="#00ff88").pack()

        # ── Buttons ──────────────────────────────────────────────────
        btn_frame = tk.Frame(self, bg="#0f0f0f")
        btn_frame.pack(pady=8)

        self.btn_start = tk.Button(btn_frame, text="▶  START", command=self._start,
                                   bg="#00ff88", fg="#0f0f0f", font=("Courier New", 11, "bold"),
                                   relief="flat", padx=20, pady=8, cursor="hand2")
        self.btn_start.grid(row=0, column=0, padx=8)

        self.btn_stop = tk.Button(btn_frame, text="■  STOP", command=self._stop,
                                  bg="#ff4455", fg="white", font=("Courier New", 11, "bold"),
                                  relief="flat", padx=20, pady=8, cursor="hand2", state="disabled")
        self.btn_stop.grid(row=0, column=1, padx=8)

        self.btn_accounts = tk.Button(btn_frame, text="📄 accounts.txt",
                                      command=self._open_accounts,
                                      bg="#1a1a1a", fg="#00ff88", font=("Courier New", 10),
                                      relief="flat", padx=14, pady=8, cursor="hand2")
        self.btn_accounts.grid(row=0, column=2, padx=8)

        self.lbl_status = tk.Label(self, text="● IDLE", font=("Courier New", 10, "bold"),
                                   bg="#0f0f0f", fg="#555")
        self.lbl_status.pack()

        tk.Label(self, text="─"*62, bg="#0f0f0f", fg="#333").pack()
        self.log = scrolledtext.ScrolledText(
            self, height=13, bg="#0d0d0d", fg="#ccc",
            font=("Courier New", 9), relief="flat",
            insertbackground="white", state="disabled")
        self.log.pack(padx=16, pady=6, fill="both")

        self.lbl_count = tk.Label(self, text="Accounts tao: 0",
                                  font=("Courier New", 10), bg="#0f0f0f", fg="#555")
        self.lbl_count.pack(pady=(0, 10))
        self.count = 0

    def log_msg(self, msg):
        self.log.configure(state="normal")
        self.log.insert("end", msg + "\n")
        self.log.see("end")
        self.log.configure(state="disabled")

    def log_error(self, msg):
        self.log.configure(state="normal")
        self.log.insert("end", msg + "\n", "error")
        self.log.tag_config("error", foreground="#ff4455")
        self.log.see("end")
        self.log.configure(state="disabled")

    def set_status(self, text, color="#00ff88"):
        self.lbl_status.configure(text=f"● {text}", fg=color)

    def _on_vpn_toggle(self):
        if self.use_vpn.get():
            self.lbl_wg_status.configure(text="● VPN: ENABLED (se doi IP khi bi chan)", fg="#4db8ff")
        else:
            self.lbl_wg_status.configure(text="● VPN: OFF", fg="#555")

    def _browse_wg(self):
        path = filedialog.askdirectory(title="Chon thu muc chua file .conf WireGuard")
        if not path:
            path = filedialog.askopenfilename(
                title="Chon file .conf WireGuard",
                filetypes=[("WireGuard Config", "*.conf"), ("All", "*.*")]
            )
        if path:
            self.var_wg_path.set(path)
            self.wg.load_configs(path)
            self.lbl_wg_status.configure(
                text=f"● VPN: {len(self.wg.conf_files)} tunnel(s) loaded", fg="#00ff88")

    def _open_accounts(self):
        if os.path.exists(ACCOUNTS_FILE):
            os.startfile(ACCOUNTS_FILE)
        else:
            messagebox.showinfo("Thong bao", "Chua co file accounts.txt!")

    # ── Captcha popup ────────────────────────────────────────────────
    def _show_captcha_window(self, driver):
        done = threading.Event()

        def popup():
            win = tk.Toplevel(self)
            win.title("Xac thuc Captcha")
            win.geometry("340x160")
            win.configure(bg="#1a1a1a")
            win.attributes("-topmost", True)

            tk.Label(win, text="Cloudflare Captcha phat hien!",
                     bg="#1a1a1a", fg="#ffaa00",
                     font=("Courier New", 11, "bold")).pack(pady=(20, 6))
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

    # ── Driver factory ───────────────────────────────────────────────
    def _restart_driver(self, chrome_ver):
        try:
            if self.driver:
                self.driver.quit()
        except:
            pass

        options = uc.ChromeOptions()
        options.add_argument("--disable-blink-features=AutomationControlled")
        options.add_argument("--no-sandbox")
        options.add_argument("--disable-dev-shm-usage")
        options.add_argument("--window-size=1,1")
        options.add_argument("--window-position=0,0")

        prefs = {
            "credentials_enable_service": False,
            "profile.password_manager_enabled": False,
            "profile.default_content_setting_values.notifications": 2
        }
        options.add_experimental_option("prefs", prefs)

        self.driver = uc.Chrome(version_main=chrome_ver, options=options)

        if self.hide_window.get():
            self._minimize_chrome(self.driver)

        return self.driver

    # ── Start / Stop ─────────────────────────────────────────────────
    def _start(self):
        try:
            int(self.var_email_start.get())
            int(self.var_email_end.get())
            int(self.var_chrome_ver.get())
        except ValueError:
            messagebox.showerror("Loi", "Index va Chrome version phai la so!")
            return

        if self.use_vpn.get() and not self.wg.conf_files:
            path = self.var_wg_path.get()
            if path:
                self.wg.load_configs(path)
            if not self.wg.conf_files:
                messagebox.showerror("Loi VPN",
                    "Ban bat VPN nhung chua chon thu muc/file .conf WireGuard!")
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

    # ── Main worker (TỐI ƯU NHANH NHƯ CODE ĐẦU) ───────────────────────
    def _run(self):
        try:
            chrome_ver  = int(self.var_chrome_ver.get())
            prefix      = self.var_email_prefix.get()
            domain      = self.var_email_domain.get()
            password    = self.var_password.get()
            email_index = int(self.var_email_start.get())
            email_end   = int(self.var_email_end.get())
            do_vpn      = self.use_vpn.get()

            # Khởi tạo driver lần đầu
            driver = self._restart_driver(chrome_ver)
            driver.get("https://vimeo.com/join")
            
            if self.hide_window.get():
                self._minimize_chrome(driver)
                self.log_msg("Da an cua so Chrome (chay ngam)")
            else:
                self.log_msg("Che do hien thi Chrome (khong an)")

            # Khởi tạo VPN nếu bật
            if do_vpn:
                self.log_msg("[VPN] Khoi tao tunnel dau tien...")
                self.wg.rotate()
                self.after(0, lambda: self.lbl_wg_status.configure(
                    text=f"● VPN: Active – {self.wg.active_name}", fg="#00ff88"))
                time.sleep(3)
                driver.refresh()

            while self.running and email_index <= email_end:
                self.log_msg(f"\n=== START LOOP index {email_index} ===")
                current_email = f"{prefix}{email_index}{domain}"
                email_valid = False

                # Vòng lặp thử email (nhanh gọn như code đầu)
                while self.running:
                    self.log_msg(f"\nDang thu email: {current_email}")

                    # Kiểm tra captcha Cloudflare
                    if self.check_cloudflare_page(driver):
                        self.log_msg("Cloudflare - can tich tay!")
                        self._show_captcha_window(driver)

                    # Tick captcha nếu có
                    try:
                        cap_el = WebDriverWait(driver, 3).until(
                            EC.presence_of_element_located((By.XPATH, CAPTCHA_XPATH)))
                        self.js_click(driver, cap_el)
                        self.log_msg("[OK] Da tick captcha!")
                    except TimeoutException:
                        pass

                    # Đợi ô email xuất hiện
                    email_el = self.wait_el(driver, EMAIL_XPATH, 120)
                    self.log_msg("[OK] Tim thay o email!")

                    # Dùng JS input (nhanh hơn send_keys)
                    self.js_input(driver, email_el, current_email)
                    self.log_msg(f"[3] Da dien email: {current_email}")

                    # Click submit lần 1 bằng JS (nhanh)
                    sub1 = self.wait_clickable(driver, SUBMIT1_XPATH, 60)
                    self.js_click(driver, sub1)
                    self.log_msg("[OK] Da submit email")

                    # Kiểm tra email đã tồn tại (chờ tối đa 5s)
                    try:
                        WebDriverWait(driver, 5).until(
                            EC.presence_of_element_located((By.XPATH, EMAIL_EXISTS_XPATH)))
                        self.log_msg(f"[TON TAI] {current_email} da duoc su dung")
                        email_index += 1
                        current_email = f"{prefix}{email_index}{domain}"
                        driver.get("https://vimeo.com/join")
                        continue
                    except TimeoutException:
                        pass

                    # Kiểm tra xem có sang được trang nhập tên không
                    try:
                        self.wait_el(driver, NAME_XPATH, 5)
                        self.log_msg("[OK] EMAIL HOP LE!")
                        email_valid = True
                        break
                    except TimeoutException:
                        self.log_msg("[LOI] Khong tim thay o name, refresh...")
                        driver.refresh()
                        continue

                if not email_valid:
                    continue

                # ===== ĐĂNG KÝ TÀI KHOẢN =====
                self.log_msg("\n=== BAT DAU DANG KY ===")
                random_name = ''.join(random.choices(string.ascii_letters, k=6))

                name_el = self.wait_el(driver, NAME_XPATH, 60)
                self.js_input(driver, name_el, random_name)
                self.log_msg(f"[4] Ten: {random_name}")

                pw_el = self.wait_el(driver, PASSWORD_XPATH, 60)
                self.js_input(driver, pw_el, password)
                self.log_msg("[5] Da dien password")

                cf_el = self.wait_el(driver, CONFIRM_XPATH, 60)
                self.js_input(driver, cf_el, password)
                self.log_msg("[6] Da dien confirm password")

                cb_el = self.wait_clickable(driver, CHECKBOX_XPATH, 60)
                self.js_click(driver, cb_el)
                self.log_msg("[7] Da tick checkbox")

                sf_el = self.wait_clickable(driver, SUBMIT_FINAL_XPATH, 60)
                self.js_click(driver, sf_el)
                self.log_msg("[8] Da submit lan cuoi")

                # Về trang chủ ngay lập tức
                driver.get("https://vimeo.com/")
                self.log_msg("[9] Da ve trang chu ngay lap tuc")

                # Kiểm tra đăng nhập thành công
                try:
                    WebDriverWait(driver, 10).until(
                        EC.presence_of_element_located((By.XPATH, LOGGED_IN_XPATH)))
                    self.log_msg("[OK] Dang nhap thanh cong, IP hoat dong tot")
                except TimeoutException:
                    self.log_error("=" * 50)
                    self.log_error("[WARNING] BI NHAY SANG TRANG PAGE (SURVEY/INTERSTITIAL)")
                    self.log_error(f"[WARNING] Email: {current_email} chua dang nhap duoc")
                    self.log_error("[WARNING] Dong trinh duyet va chuyen sang email tiep theo")
                    self.log_error("=" * 50)
                    
                    with open(EMAIL_FAILED_FILE, "a", encoding="utf-8") as f:
                        f.write(f"{time.strftime('%Y-%m-%d %H:%M:%S')} - Page survey - Email: {current_email}\n")
                    
                    # Đổi IP nếu có VPN
                    if do_vpn:
                        self.log_msg("[VPN] Dang doi IP qua WireGuard...")
                        ok = self.wg.rotate()
                        if ok:
                            self.after(0, lambda: self.lbl_wg_status.configure(
                                text=f"● VPN: Active – {self.wg.active_name}", fg="#00ff88"))
                            self.log_msg("[VPN] Da doi IP thanh cong!")
                            time.sleep(3)
                    
                    driver = self._restart_driver(chrome_ver)
                    driver.get("https://vimeo.com/join")
                    email_index += 1
                    continue

                # Lưu account thành công
                with open(ACCOUNTS_FILE, "a", encoding="utf-8") as f:
                    f.write(f"{current_email}|{password}\n")
                self.log_msg(f"[DA LUU] Tao tai khoan thanh cong: {current_email}")

                self.count += 1
                self.after(0, lambda c=self.count: self.lbl_count.configure(text=f"Accounts tao: {c}"))

                # ===== KIỂM TRA LẠI EMAIL VỪA TẠO (3 LẦN) =====
                self.log_msg("\n=== KIEM TRA LAI EMAIL VUA TAO ===")
                driver.get("https://vimeo.com/join")
                time.sleep(2)

                test_success = False
                retry_create_count = 0
                max_retries = 3

                while not test_success and self.running and retry_create_count < max_retries:
                    retry_create_count += 1
                    self.log_msg(f"\n[LAN KIEM TRA {retry_create_count}/{max_retries}] Email: {current_email}")
                    
                    # Tick captcha nếu có
                    try:
                        cap_el = WebDriverWait(driver, 3).until(
                            EC.presence_of_element_located((By.XPATH, CAPTCHA_XPATH)))
                        self.js_click(driver, cap_el)
                        self.log_msg("[OK] Da tick captcha!")
                    except TimeoutException:
                        pass
                    
                    # Đợi ô email
                    try:
                        email_el = self.wait_el(driver, EMAIL_XPATH, 60)
                        self.log_msg("[OK] Tim thay o email")
                    except TimeoutException:
                        self.log_msg("[LOI] Khong tim thay o email, refresh...")
                        driver.refresh()
                        time.sleep(2)
                        continue
                    
                    # Điền email
                    self.js_input(driver, email_el, current_email)
                    self.log_msg(f"[TEST] Dang dung email: {current_email}")
                    
                    # Click submit
                    sub1 = self.wait_clickable(driver, SUBMIT1_XPATH, 30)
                    self.js_click(driver, sub1)
                    
                    # Kiểm tra xem có vào được trang nhập tên không
                    try:
                        name_test = WebDriverWait(driver, 5).until(
                            EC.presence_of_element_located((By.XPATH, NAME_XPATH)))
                        
                        self.log_error(f"\n[CHUA TAO] Email {current_email} VAN CO THE DANG KY (lan thu {retry_create_count})")
                        
                        if retry_create_count >= max_retries:
                            self.log_error("\n" + "="*60)
                            self.log_error("[ERROR] DA TAO LAI 3 LAN VAN THAT BAI!")
                            self.log_error("[ERROR] EMAIL VAN SANG DUOC TRANG NHAP TEN")
                            self.log_error("[ERROR] => KHA NANG CAO IP/PROXY DA BI CHAN <=")
                            self.log_error("[ERROR] VUI LONG DOI PROXY VA CHAY LAI CHUONG TRINH")
                            self.log_error("="*60)
                            
                            # Ghi log error_proxy.txt
                            with open(ERROR_PROXY_FILE, "a", encoding='utf-8') as f:
                                f.write(f"{time.strftime('%Y-%m-%d %H:%M:%S')} - Can doi proxy - Email that bai: {current_email}\n")
                            
                            # Hiện messagebox cảnh báo
                            self.after(0, lambda: messagebox.showerror(
                                "CANH BAO DOI PROXY",
                                f"Da tao lai {max_retries} lan nhung email {current_email} van co the dang ky!\n"
                                f"IP/PROXY cua ban da bi Vimeo chan.\n\n"
                                f"Vui long:\n"
                                f"1. Doi proxy/WireGuard config khac\n"
                                f"2. Chay lai chuong trinh\n\n"
                                f"Da ghi log vao: {ERROR_PROXY_FILE}"
                            ))
                            
                            self.running = False
                            break
                        
                        # Nếu chưa đủ 3 lần, thử tạo lại tài khoản
                        self.log_msg(f"[TAO LAI LAN {retry_create_count}] Dang tao lai tai khoan...")
                        
                        random_name_new = ''.join(random.choices(string.ascii_letters, k=6))
                        self.js_input(driver, name_test, random_name_new)
                        self.log_msg(f"[TAO LAI] Ten moi: {random_name_new}")
                        
                        pw_test = self.wait_el(driver, PASSWORD_XPATH, 30)
                        self.js_input(driver, pw_test, password)
                        
                        cf_test = self.wait_el(driver, CONFIRM_XPATH, 30)
                        self.js_input(driver, cf_test, password)
                        
                        cb_test = self.wait_clickable(driver, CHECKBOX_XPATH, 30)
                        self.js_click(driver, cb_test)
                        
                        sf_test = self.wait_clickable(driver, SUBMIT_FINAL_XPATH, 30)
                        self.js_click(driver, sf_test)
                        
                        self.log_msg("[TAO LAI THANH CONG]")
                        driver.get("https://vimeo.com/")
                        time.sleep(2)
                        
                        self.log_msg("\n[TEST LAI SAU KHI TAO] Quay lai trang join...")
                        driver.get("https://vimeo.com/join")
                        time.sleep(2)
                        
                    except TimeoutException:
                        self.log_msg(f"[OK] Email {current_email} da ton tai, khong the dang ky lai")
                        self.log_msg("[KET LUAN] Tai khoan da duoc tao thanh cong!")
                        test_success = True
                        break

                if not self.running:
                    # Nếu bị dừng do lỗi proxy, thoát khỏi vòng lặp chính
                    return

                email_index += 1
                driver.get("https://vimeo.com/join")

                if self.hide_window.get():
                    self._minimize_chrome(driver)

            self.log_msg("\n=== HOAN THANH TAT CA EMAIL ===")

        except Exception as e:
            self.log_msg(f"LOI: {e}")
            import traceback
            self.log_msg(traceback.format_exc())

        finally:
            try:
                if self.driver:
                    self.driver.quit()
            except:
                pass
            if self.use_vpn.get():
                self.wg.shutdown()
            self.running = False
            self.after(0, self._on_done)

    def _on_done(self):
        self.btn_start.configure(state="normal")
        self.btn_stop.configure(state="disabled")
        self.set_status("DONE", "#ffaa00")
        self.log_msg("─── Ket thuc ───")


if __name__ == "__main__":
    if sys.platform == "win32":
        import ctypes
        if not ctypes.windll.shell32.IsUserAnAdmin():
            script = sys.executable if getattr(sys, "frozen", False) else __file__
            params = " ".join([f'"{a}"' for a in sys.argv[1:]])
            ret = ctypes.windll.shell32.ShellExecuteW(
                None, "runas", sys.executable,
                f'"{script}" {params}' if not getattr(sys, "frozen", False) else params,
                None, 1
            )
            if ret > 32:
                sys.exit(0)

    app = App()
    app.mainloop()