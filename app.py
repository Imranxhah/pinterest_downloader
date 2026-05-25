import tkinter as tk
from tkinter import ttk, filedialog, messagebox
import threading
import json
import csv
import os
import time

from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.common.exceptions import StaleElementReferenceException
from selenium.webdriver.common.keys import Keys

# ─── Paths ────────────────────────────────────────────────────────────────────
SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
CREDENTIALS_FILE = os.path.join(SCRIPT_DIR, "credentials.json")

# ─── Credential Helpers ────────────────────────────────────────────────────────
def load_credentials():
    if os.path.exists(CREDENTIALS_FILE):
        try:
            with open(CREDENTIALS_FILE, "r", encoding="utf-8") as f:
                return json.load(f)
        except Exception:
            return {}
    return {}

def save_credentials(email, password):
    with open(CREDENTIALS_FILE, "w", encoding="utf-8") as f:
        json.dump({"email": email, "password": password}, f, indent=2)

# ─── Main App Class ────────────────────────────────────────────────────────────
class PinterestScraperApp:
    def __init__(self, root):
        self.root = root
        self.root.title("Pinterest Image Scraper")
        self.root.geometry("820x600")
        self.root.resizable(False, False)
        self.root.configure(bg="#1a1a2e")

        # State
        self._stop_event = threading.Event()
        self._scraping_thread = None
        self._collected_count = 0
        self._target_count = 0
        self._driver = None
        self._selected_csv_path = tk.StringVar(value="")
        self._auto_scroll_enabled = True
        self._remote_window = None

        self._setup_styles()
        self._build_ui()
        self._load_saved_credentials()

    # ──────────────────────────────────────────────────────────────────────────
    # Styles
    # ──────────────────────────────────────────────────────────────────────────
    def _setup_styles(self):
        style = ttk.Style()
        style.theme_use("clam")

        style.configure("TFrame", background="#1a1a2e")
        style.configure("Card.TFrame", background="#16213e", relief="flat")

        style.configure(
            "TLabel",
            background="#1a1a2e",
            foreground="#e0e0e0",
            font=("Segoe UI", 10),
        )
        style.configure(
            "Header.TLabel",
            background="#1a1a2e",
            foreground="#e94560",
            font=("Segoe UI", 18, "bold"),
        )
        style.configure(
            "Sub.TLabel",
            background="#1a1a2e",
            foreground="#a0a0b0",
            font=("Segoe UI", 9),
        )
        style.configure(
            "Card.TLabel",
            background="#16213e",
            foreground="#e0e0e0",
            font=("Segoe UI", 10),
        )
        style.configure(
            "Counter.TLabel",
            background="#16213e",
            foreground="#e94560",
            font=("Segoe UI", 22, "bold"),
        )
        style.configure(
            "CounterSub.TLabel",
            background="#16213e",
            foreground="#a0a0b0",
            font=("Segoe UI", 9),
        )

        # Buttons
        style.configure(
            "Start.TButton",
            background="#e94560",
            foreground="#ffffff",
            font=("Segoe UI", 11, "bold"),
            borderwidth=0,
            focusthickness=0,
            padding=(12, 8),
        )
        style.map("Start.TButton", background=[("active", "#c73652")])

        style.configure(
            "Stop.TButton",
            background="#0f3460",
            foreground="#ffffff",
            font=("Segoe UI", 11, "bold"),
            borderwidth=0,
            focusthickness=0,
            padding=(12, 8),
        )
        style.map("Stop.TButton", background=[("active", "#0a2540")])

        style.configure(
            "Browse.TButton",
            background="#0f3460",
            foreground="#e0e0e0",
            font=("Segoe UI", 9),
            borderwidth=0,
            focusthickness=0,
            padding=(6, 4),
        )
        style.map("Browse.TButton", background=[("active", "#0a2540")])

        style.configure(
            "Clear.TButton",
            background="#2a2a4a",
            foreground="#a0a0b0",
            font=("Segoe UI", 9),
            borderwidth=0,
            focusthickness=0,
            padding=(6, 4),
        )
        style.map("Clear.TButton", background=[("active", "#1a1a3a")])

        style.configure(
            "red.Horizontal.TProgressbar",
            troughcolor="#0f3460",
            background="#e94560",
            borderwidth=0,
            thickness=14,
        )

    # ──────────────────────────────────────────────────────────────────────────
    # Build UI
    # ──────────────────────────────────────────────────────────────────────────
    def _build_ui(self):
        # ── Header ─────────────────────────────────────────────────────────
        header_frame = ttk.Frame(self.root, style="TFrame", padding=(24, 10, 24, 4))
        header_frame.pack(fill="x")

        ttk.Label(header_frame, text="📌 Pinterest Scraper", style="Header.TLabel").pack(
            anchor="w"
        )
        ttk.Label(
            header_frame,
            text="Scrape image URLs automatically and save them to CSV",
            style="Sub.TLabel",
        ).pack(anchor="w", pady=(1, 0))

        sep = tk.Frame(self.root, height=1, bg="#0f3460")
        sep.pack(fill="x", padx=24, pady=(6, 0))

        # ── Credentials Card ───────────────────────────────────────────────
        self._build_card(
            label="🔐  Account Credentials",
            builder=self._build_credentials_section,
        )

        # ── Search Card ────────────────────────────────────────────────────
        self._build_card(
            label="🔍  Search Settings",
            builder=self._build_search_section,
        )

        # ── CSV Card ───────────────────────────────────────────────────────
        self._build_card(
            label="📂  Output CSV",
            builder=self._build_csv_section,
        )

        # ── Counter + Progress Card ────────────────────────────────────────
        self._build_card(
            label="📊  Progress",
            builder=self._build_progress_section,
        )

        # ── Buttons ────────────────────────────────────────────────────────
        btn_frame = ttk.Frame(self.root, style="TFrame", padding=(24, 4, 24, 4))
        btn_frame.pack(fill="x")

        self._start_btn = ttk.Button(
            btn_frame,
            text="▶  Start Scraping",
            style="Start.TButton",
            command=self._on_start,
        )
        self._start_btn.pack(side="left", padx=(0, 8))

        self._stop_btn = ttk.Button(
            btn_frame,
            text="⏹  Stop",
            style="Stop.TButton",
            command=self._on_stop,
            state="disabled",
        )
        self._stop_btn.pack(side="left")

        # ── Log Area ───────────────────────────────────────────────────────
        log_outer = ttk.Frame(self.root, style="TFrame", padding=(24, 4, 24, 8))
        log_outer.pack(fill="both", expand=True)

        ttk.Label(log_outer, text="📋  Log", style="TLabel").pack(anchor="w", pady=(0, 4))

        log_bg = tk.Frame(log_outer, bg="#16213e", bd=0)
        log_bg.pack(fill="both", expand=True)

        self._log_text = tk.Text(
            log_bg,
            height=5,
            bg="#16213e",
            fg="#c0c0d0",
            insertbackground="#e94560",
            font=("Consolas", 9),
            borderwidth=0,
            relief="flat",
            state="disabled",
            wrap="word",
        )
        scrollbar = tk.Scrollbar(log_bg, command=self._log_text.yview, bg="#0f3460")
        self._log_text.configure(yscrollcommand=scrollbar.set)
        scrollbar.pack(side="right", fill="y")
        self._log_text.pack(fill="both", expand=True, padx=10, pady=8)

    def _build_card(self, label, builder):
        outer = ttk.Frame(self.root, style="TFrame", padding=(24, 3, 24, 0))
        outer.pack(fill="x")

        card = tk.Frame(outer, bg="#16213e", bd=0)
        card.pack(fill="x")

        title = tk.Label(
            card,
            text=label,
            bg="#16213e",
            fg="#a0a0b0",
            font=("Segoe UI", 9, "bold"),
            pady=4,
            padx=12,
            anchor="w",
        )
        title.pack(fill="x")

        sep = tk.Frame(card, height=1, bg="#0f3460")
        sep.pack(fill="x")

        content = tk.Frame(card, bg="#16213e")
        content.pack(fill="x", padx=12, pady=5)

        builder(content)

    # ──────────────────────────────────────────────────────────────────────────
    # Credential Section
    # ──────────────────────────────────────────────────────────────────────────
    def _build_credentials_section(self, parent):
        def make_row(p, lbl_text, var, show=""):
            row = tk.Frame(p, bg="#16213e")
            row.pack(fill="x", pady=2)
            tk.Label(row, text=lbl_text, bg="#16213e", fg="#a0a0b0",
                     font=("Segoe UI", 9), width=12, anchor="w").pack(side="left")
            entry = tk.Entry(
                row, textvariable=var, show=show,
                bg="#0f3460", fg="#e0e0e0",
                insertbackground="#e94560",
                font=("Segoe UI", 10),
                relief="flat", bd=0,
            )
            entry.pack(side="left", fill="x", expand=True, ipady=5, padx=(0, 4))
            return entry

        self._email_var = tk.StringVar()
        self._pass_var = tk.StringVar()
        self._show_pass = tk.BooleanVar(value=False)

        make_row(parent, "Email:", self._email_var)
        pass_frame = tk.Frame(parent, bg="#16213e")
        pass_frame.pack(fill="x", pady=3)
        tk.Label(pass_frame, text="Password:", bg="#16213e", fg="#a0a0b0",
                 font=("Segoe UI", 9), width=12, anchor="w").pack(side="left")

        self._pass_entry = tk.Entry(
            pass_frame, textvariable=self._pass_var, show="●",
            bg="#0f3460", fg="#e0e0e0",
            insertbackground="#e94560",
            font=("Segoe UI", 10),
            relief="flat", bd=0,
        )
        self._pass_entry.pack(side="left", fill="x", expand=True, ipady=5, padx=(0, 4))

        toggle_btn = tk.Button(
            pass_frame, text="👁", bg="#0f3460", fg="#a0a0b0",
            font=("Segoe UI", 9), relief="flat", bd=0, cursor="hand2",
            command=self._toggle_password,
        )
        toggle_btn.pack(side="left")

        info = tk.Label(
            parent,
            text="✔ Credentials are saved locally in credentials.json for future sessions.",
            bg="#16213e", fg="#4a7c59",
            font=("Segoe UI", 8),
        )
        info.pack(anchor="w", pady=(4, 0))

    def _toggle_password(self):
        if self._pass_entry.cget("show") == "●":
            self._pass_entry.config(show="")
        else:
            self._pass_entry.config(show="●")

    # ──────────────────────────────────────────────────────────────────────────
    # Search Section
    # ──────────────────────────────────────────────────────────────────────────
    def _build_search_section(self, parent):
        self._search_var = tk.StringVar()
        self._target_var = tk.StringVar(value="2000")

        for lbl, var in [("Search Term:", self._search_var), ("Target Count:", self._target_var)]:
            row = tk.Frame(parent, bg="#16213e")
            row.pack(fill="x", pady=2)
            tk.Label(row, text=lbl, bg="#16213e", fg="#a0a0b0",
                     font=("Segoe UI", 9), width=14, anchor="w").pack(side="left")
            tk.Entry(
                row, textvariable=var,
                bg="#0f3460", fg="#e0e0e0",
                insertbackground="#e94560",
                font=("Segoe UI", 10),
                relief="flat", bd=0,
            ).pack(side="left", fill="x", expand=True, ipady=5)

    # ──────────────────────────────────────────────────────────────────────────
    # CSV Section
    # ──────────────────────────────────────────────────────────────────────────
    def _build_csv_section(self, parent):
        row1 = tk.Frame(parent, bg="#16213e")
        row1.pack(fill="x", pady=2)

        tk.Label(row1, text="Existing CSV:", bg="#16213e", fg="#a0a0b0",
                 font=("Segoe UI", 9), width=14, anchor="w").pack(side="left")

        self._csv_path_label = tk.Label(
            row1, textvariable=self._selected_csv_path,
            bg="#0f3460", fg="#e0e0e0",
            font=("Segoe UI", 9),
            anchor="w", relief="flat",
        )
        self._csv_path_label.pack(side="left", fill="x", expand=True, ipady=5, padx=(0, 6))

        browse_btn = tk.Button(
            row1, text="📂 Browse", bg="#0f3460", fg="#e0e0e0",
            font=("Segoe UI", 9), relief="flat", bd=0, cursor="hand2",
            padx=8, pady=4,
            command=self._browse_csv,
        )
        browse_btn.pack(side="left", padx=(0, 4))

        clear_btn = tk.Button(
            row1, text="✖ Clear", bg="#2a2a4a", fg="#a0a0b0",
            font=("Segoe UI", 9), relief="flat", bd=0, cursor="hand2",
            padx=8, pady=4,
            command=lambda: self._selected_csv_path.set(""),
        )
        clear_btn.pack(side="left")

        info = tk.Label(
            parent,
            text="Leave empty to create a new file named after the search term. "
                 "Select a file to append new unique links to it.",
            bg="#16213e", fg="#4a7c59",
            font=("Segoe UI", 8),
            wraplength=700, justify="left",
        )
        info.pack(anchor="w", pady=(4, 0))

    def _browse_csv(self):
        path = filedialog.askopenfilename(
            title="Select an existing CSV file",
            filetypes=[("CSV files", "*.csv"), ("All files", "*.*")],
            initialdir=SCRIPT_DIR,
        )
        if path:
            self._selected_csv_path.set(path)

    # ──────────────────────────────────────────────────────────────────────────
    # Progress Section
    # ──────────────────────────────────────────────────────────────────────────
    def _build_progress_section(self, parent):
        counter_row = tk.Frame(parent, bg="#16213e")
        counter_row.pack(fill="x", pady=(1, 3))

        self._counter_label = tk.Label(
            counter_row, text="0 / 0",
            bg="#16213e", fg="#e94560",
            font=("Segoe UI", 16, "bold"),
        )
        self._counter_label.pack(side="left")

        tk.Label(counter_row, text=" links collected",
                 bg="#16213e", fg="#a0a0b0",
                 font=("Segoe UI", 9)).pack(side="left", pady=(8, 0))

        self._progress = ttk.Progressbar(
            parent,
            style="red.Horizontal.TProgressbar",
            orient="horizontal",
            mode="determinate",
            maximum=100,
            value=0,
        )
        self._progress.pack(fill="x", pady=(0, 2))

        self._status_label = tk.Label(
            parent, text="Idle — ready to scrape.",
            bg="#16213e", fg="#a0a0b0",
            font=("Segoe UI", 9),
        )
        self._status_label.pack(anchor="w")

    # ──────────────────────────────────────────────────────────────────────────
    # Load / Save credentials
    # ──────────────────────────────────────────────────────────────────────────
    def _load_saved_credentials(self):
        creds = load_credentials()
        if creds.get("email"):
            self._email_var.set(creds["email"])
        if creds.get("password"):
            self._pass_var.set(creds["password"])

    # ──────────────────────────────────────────────────────────────────────────
    # Logging
    # ──────────────────────────────────────────────────────────────────────────
    def _log(self, message):
        # UI update
        self._log_text.config(state="normal")
        self._log_text.insert("end", f"› {message}\n")
        self._log_text.see("end")
        self._log_text.config(state="disabled")

        # File logging
        try:
            log_file = os.path.join(SCRIPT_DIR, "scraper_log.txt")
            timestamp = time.strftime("%Y-%m-%d %H:%M:%S")
            with open(log_file, "a", encoding="utf-8") as f:
                f.write(f"[{timestamp}] {message}\n")
                f.flush() # Ensure it's written immediately
        except Exception:
            pass

    # ──────────────────────────────────────────────────────────────────────────
    # Start / Stop handlers
    # ──────────────────────────────────────────────────────────────────────────
    def _on_start(self):
        email = self._email_var.get().strip()
        password = self._pass_var.get().strip()
        search_term = self._search_var.get().strip()
        target_str = self._target_var.get().strip()

        if not email or not password:
            messagebox.showerror("Missing Credentials", "Please enter your email and password.")
            return
        if not search_term:
            messagebox.showerror("Missing Search Term", "Please enter a search term.")
            return
        try:
            target = int(target_str)
            if target <= 0:
                raise ValueError
        except ValueError:
            messagebox.showerror("Invalid Target", "Target count must be a positive integer.")
            return

        # Save credentials
        save_credentials(email, password)

        # Reset state
        self._stop_event.clear()
        self._collected_count = 0
        self._target_count = target
        self._counter_label.config(text=f"0 / {target}")
        self._progress["value"] = 0
        self._status_label.config(text="Starting…")

        self._log_text.config(state="normal")
        self._log_text.delete("1.0", "end")
        self._log_text.config(state="disabled")

        # Clear/Create log file for new session
        try:
            log_file = os.path.join(SCRIPT_DIR, "scraper_log.txt")
            with open(log_file, "w", encoding="utf-8") as f:
                f.write("=== NEW SCRAPING SESSION STARTED ===\n")
        except Exception:
            pass

        self._start_btn.config(state="disabled")
        self._stop_btn.config(state="normal")
        self._auto_scroll_enabled = True
        self._show_remote_control()

        # Determine CSV path
        csv_path = self._selected_csv_path.get().strip()
        if not csv_path:
            output_dir = os.path.join(SCRIPT_DIR, "CSV_DATA")
            if not os.path.exists(output_dir):
                os.makedirs(output_dir)
            safe_name = search_term.replace(" ", "_").lower()
            csv_path = os.path.join(output_dir, f"{safe_name}.csv")

        self._scraping_thread = threading.Thread(
            target=self._run_scraper,
            args=(email, password, search_term, target, csv_path),
            daemon=True,
        )
        self._scraping_thread.start()
        self._poll_progress()

    def _on_stop(self):
        self._stop_event.set()
        self._status_label.config(text="Stopping… please wait.")
        self._stop_btn.config(state="disabled")
        self._hide_remote_control()

    def _show_remote_control(self):
        if self._remote_window:
            return

        self._remote_window = tk.Toplevel(self.root)
        self._remote_window.title("Remote")
        self._remote_window.geometry("200x120")
        self._remote_window.resizable(False, False)
        self._remote_window.configure(bg="#1a1a2e")
        self._remote_window.attributes("-topmost", True)
        
        # Position at right side of screen
        screen_width = self._remote_window.winfo_screenwidth()
        screen_height = self._remote_window.winfo_screenheight()
        self._remote_window.geometry(f"200x120+{screen_width-220}+100")

        ttk.Label(self._remote_window, text="Scroll Control", style="Sub.TLabel").pack(pady=10)
        
        self._remote_pause_btn = ttk.Button(
            self._remote_window,
            text="⏸ Pause Scrolling",
            style="Browse.TButton",
            command=self._on_toggle_scroll
        )
        self._remote_pause_btn.pack(expand=True, fill="x", padx=20, pady=5)

    def _hide_remote_control(self):
        if self._remote_window:
            self._remote_window.destroy()
            self._remote_window = None

    def _on_toggle_scroll(self):
        self._auto_scroll_enabled = not self._auto_scroll_enabled
        if self._auto_scroll_enabled:
            if hasattr(self, "_remote_pause_btn"):
                self._remote_pause_btn.config(text="⏸ Pause Scrolling")
            self._log("Auto-scrolling resumed.")
        else:
            if hasattr(self, "_remote_pause_btn"):
                self._remote_pause_btn.config(text="▶ Resume Scrolling")
            self._log("Auto-scrolling paused. You can now click images manually.")

    # ──────────────────────────────────────────────────────────────────────────
    # Poll progress from main thread (safe tkinter update)
    # ──────────────────────────────────────────────────────────────────────────
    def _poll_progress(self):
        if self._target_count > 0:
            pct = min(100, int(self._collected_count / self._target_count * 100))
            self._counter_label.config(
                text=f"{self._collected_count} / {self._target_count}"
            )
            self._progress["value"] = pct
            
            if self._remote_window and hasattr(self, "_remote_progress_label"):
                self._remote_progress_label.config(
                    text=f"{self._collected_count} / {self._target_count}"
                )

        if self._scraping_thread and self._scraping_thread.is_alive():
            self.root.after(500, self._poll_progress)
        else:
            self._start_btn.config(state="normal")
            self._stop_btn.config(state="disabled")

    # ──────────────────────────────────────────────────────────────────────────
    # Scraper (runs in background thread)
    # ──────────────────────────────────────────────────────────────────────────
    def _run_scraper(self, email, password, search_term, target, csv_path):
        unique_urls = set()
        self.root.after(0, self._log, f"Thread started. Target: {target}, Path: {csv_path}")

        # ── Pre-load existing URLs if appending ──────────────────────────
        if os.path.exists(csv_path):
            try:
                with open(csv_path, "r", encoding="utf-8") as f:
                    reader = csv.reader(f)
                    next(reader, None)  # skip header
                    for row in reader:
                        if row:
                            unique_urls.add(row[0])
                self.root.after(0, self._log,
                    f"Loaded {len(unique_urls)} existing URLs from CSV (will skip duplicates).")
            except Exception as e:
                self.root.after(0, self._log, f"Warning: could not read existing CSV — {e}")

        try:
            self.root.after(0, self._log, "Launching Chrome…")
            self._driver = webdriver.Chrome()
            wait = WebDriverWait(self._driver, 10)

            # ── Login ──────────────────────────────────────────────────────
            self.root.after(0, self._log, "Navigating to Pinterest login…")
            self._driver.get("https://www.pinterest.com/login/")

            email_input = wait.until(
                EC.presence_of_element_located(
                    (By.CSS_SELECTOR, '[data-test-id="emailInputField"]')
                )
            )
            email_input.send_keys(email)

            password_input = self._driver.find_element(
                By.CSS_SELECTOR, '[data-test-id="passwordInputField"]'
            )
            password_input.send_keys(password)

            login_button = wait.until(
                EC.element_to_be_clickable(
                    (By.CSS_SELECTOR, '[data-test-id="registerFormSubmitButton"] button')
                )
            )
            self._driver.execute_script("arguments[0].click();", login_button)

            self.root.after(0, self._log, "Waiting for home feed to load…")
            self.root.after(0, lambda: self._status_label.config(text="Logged in. Waiting for feed…"))
            time.sleep(8)

            if self._stop_event.is_set():
                raise InterruptedError("Stopped by user.")

            # ── Search ─────────────────────────────────────────────────────
            self.root.after(0, self._log, f"Searching for '{search_term}'…")
            search_box = wait.until(
                EC.element_to_be_clickable(
                    (By.CSS_SELECTOR, '[data-test-id="search-box-input"]')
                )
            )
            search_box.send_keys(search_term)
            search_box.send_keys(Keys.RETURN)

            self.root.after(0, self._log, "Waiting for search results…")
            self.root.after(0, lambda: self._status_label.config(text="Search results loading…"))
            time.sleep(10)

            if self._stop_event.is_set():
                raise InterruptedError("Stopped by user.")

            # ── Scrape Loop ────────────────────────────────────────────────
            self.root.after(0, self._log, f"Scraping started. Target: {target} links.")
            self.root.after(0, lambda: self._status_label.config(text="Scraping…"))

            empty_batch_count = 0
            while len(unique_urls) < target:
                if self._stop_event.is_set():
                    self.root.after(0, self._log, "Stop event detected in loop.")
                    break

                try:
                    images = self._driver.find_elements(
                        By.CSS_SELECTOR, '[data-test-id="pinrep-image"] img'
                    )
                except Exception as e:
                    self.root.after(0, self._log, f"Notice: Element lookup issue (retrying): {e}")
                    images = []

                new_count_this_batch = 0
                if images:
                    empty_batch_count = 0
                    for img in images:
                        if self._stop_event.is_set():
                            break
                        try:
                            url = img.get_attribute("src")
                            if url and "/videos/" not in url:
                                if url not in unique_urls:
                                    unique_urls.add(url)
                                    new_count_this_batch += 1
                            if len(unique_urls) >= target:
                                break
                        except StaleElementReferenceException:
                            continue
                        except Exception as e:
                            self.root.after(0, self._log, f"Error getting attribute: {e}")
                            continue
                else:
                    empty_batch_count += 1
                    if empty_batch_count > 10:
                        self.root.after(0, self._log, "No more images found after multiple scrolls. Stopping.")
                        break

                self._collected_count = len(unique_urls)
                self.root.after(
                    0, self._log,
                    f"Collected {len(unique_urls)}/{target} unique URLs (Added {new_count_this_batch} new)."
                )

                if len(unique_urls) >= target:
                    self.root.after(0, self._log, "Target count reached. Exiting loop.")
                    break

                if self._auto_scroll_enabled:
                    self._driver.execute_script("window.scrollBy(0, 800);")
                    time.sleep(1.5)
                else:
                    time.sleep(0.5)
            
            self.root.after(0, self._log, f"Loop finished with {len(unique_urls)} total URLs.")

        except InterruptedError:
            self.root.after(0, self._log, "Scraping stopped by user.")
        except Exception as e:
            self.root.after(0, self._log, f"Error: {e}")
            self.root.after(
                0,
                lambda e=e: self._status_label.config(text=f"Error: {e}"),
            )
        finally:
            if self._driver:
                try:
                    self._driver.quit()
                except Exception:
                    pass
                self._driver = None

            # ── Save CSV ───────────────────────────────────────────────────
            if unique_urls:
                try:
                    # We use 'w' mode because unique_urls already contains both 
                    # newly scraped and previously existing URLs (if any).
                    with open(csv_path, mode="w", newline="", encoding="utf-8") as f:
                        writer = csv.writer(f)
                        writer.writerow(["Image URL"])
                        for url in unique_urls:
                            writer.writerow([url])
                    self.root.after(
                        0, self._log,
                        f"Saved {len(unique_urls)} URLs to: {csv_path}"
                    )
                    self.root.after(
                        0,
                        lambda: self._status_label.config(
                            text=f"Done — {len(unique_urls)} URLs saved."
                        ),
                    )
                except Exception as e:
                    self.root.after(0, self._log, f"CSV save error: {e}")
            else:
                self.root.after(0, self._log, "No URLs collected — nothing saved.")
                self.root.after(
                    0, lambda: self._status_label.config(text="Idle — no URLs collected.")
                )

            self._collected_count = len(unique_urls)

# ─── Entry Point ──────────────────────────────────────────────────────────────
if __name__ == "__main__":
    root = tk.Tk()
    app = PinterestScraperApp(root)
    root.mainloop()
