import tkinter as tk
from tkinter import ttk, messagebox, simpledialog # Added simpledialog
import os
import sys
from pathlib import Path
import json # Added for saving/loading settings

HOSTS_FILE_PATH = "/etc/hosts"
BLOCK_LIST_FILE_PATH = Path.home() / ".website_blocker_list.txt"
CONFIG_FILE_PATH = Path.home() / ".pomodoro_blocker_settings.json" # For timer durations
REDIRECT_IP = "127.0.0.1"
POMODORO_COMMENT = "# Added by PomodoroBlocker"

# Default timer durations (in minutes)
DEFAULT_FOCUS_DURATION_MINUTES = 25
DEFAULT_SHORT_BREAK_DURATION_MINUTES = 5
DEFAULT_LONG_BREAK_DURATION_MINUTES = 15

class PomodoroWebsiteBlocker:
    def __init__(self, root_window):
        self.root = root_window
        self.root.title("Pomodoro Website Blocker")
        self.root.geometry("550x730")

        if not self._is_admin():
            messagebox.showerror(
                "Admin Privileges Required",
                "This application must be run with sudo privileges to modify the hosts file."
            )
            self.root.destroy()
            return

        # Initialize timer durations with defaults, then load saved settings
        self.focus_duration_minutes = DEFAULT_FOCUS_DURATION_MINUTES
        self.short_break_duration_minutes = DEFAULT_SHORT_BREAK_DURATION_MINUTES
        self.long_break_duration_minutes = DEFAULT_LONG_BREAK_DURATION_MINUTES
        self._load_settings() # Load saved durations

        self.blocked_websites = set()
        self.pomodoro_count = 0
        self.timer_running = False
        self.current_state = "Idle"
        self.remaining_seconds = 0
        self._timer_id = None

        self._create_menubar() # Create macOS menu bar

        # --- UI Elements ---
        # ... (Existing UI element creation code from your last version) ...
        # Website Entry (Row 0)
        ttk.Label(self.root, text="Website (e.g., example.com):").grid(row=0, column=0, padx=10, pady=5, sticky="w")
        self.website_entry = ttk.Entry(self.root, width=30)
        self.website_entry.grid(row=0, column=1, columnspan=2, padx=10, pady=5, sticky="ew")
        self.add_button = ttk.Button(self.root, text="Add to Block List", command=self._add_website)
        self.add_button.grid(row=0, column=3, padx=5, pady=5)

        # Blocked Websites Listbox (Row 1, 2)
        ttk.Label(self.root, text="Blocked Websites:").grid(row=1, column=0, padx=10, pady=5, sticky="nw")
        self.listbox_frame = ttk.Frame(self.root)
        self.listbox_frame.grid(row=2, column=0, columnspan=4, padx=10, pady=5, sticky="nsew")
        self.listbox = tk.Listbox(self.listbox_frame, selectmode=tk.SINGLE, height=8)
        self.listbox_scrollbar = ttk.Scrollbar(self.listbox_frame, orient=tk.VERTICAL, command=self.listbox.yview)
        self.listbox.configure(yscrollcommand=self.listbox_scrollbar.set)
        self.listbox.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        self.listbox_scrollbar.pack(side=tk.RIGHT, fill=tk.Y)

        self.unblock_button = ttk.Button(self.root, text="Unblock Selected", command=self._unblock_selected_website)
        self.unblock_button.grid(row=3, column=0, columnspan=4, padx=10, pady=5)

        # Pomodoro Controls Separator (Row 4)
        ttk.Separator(self.root, orient='horizontal').grid(row=4, column=0, columnspan=4, sticky='ew', pady=5)

        # Timer Status Labels (Row 5, 6)
        self.timer_label = ttk.Label(self.root, text="Status: Idle", font=("Helvetica", 14))
        self.timer_label.grid(row=5, column=0, columnspan=4, padx=10, pady=5)
        self.countdown_label = ttk.Label(self.root, text="Time: 00:00", font=("Helvetica", 24, "bold"))
        self.countdown_label.grid(row=6, column=0, columnspan=4, padx=10, pady=5)

        # Action Buttons (Row 7) - Focus and Stop
        self.start_focus_button = ttk.Button(self.root, text="", command=self._start_focus_session) # Text set by _update_button_labels
        self.start_focus_button.grid(row=7, column=0, columnspan=2, padx=5, pady=5, sticky="ew")
        self.stop_session_button = ttk.Button(self.root, text="Stop Session", command=self._stop_current_session)
        self.stop_session_button.grid(row=7, column=2, columnspan=2, padx=5, pady=5, sticky="ew")

        # Break Buttons (Row 8)
        self.start_short_break_button = ttk.Button(self.root, text="", command=self._start_short_break_session) # Text set by _update_button_labels
        self.start_short_break_button.grid(row=8, column=0, columnspan=2, padx=5, pady=5, sticky="ew")
        self.start_long_break_button = ttk.Button(self.root, text="", command=self._start_long_break_session) # Text set by _update_button_labels
        self.start_long_break_button.grid(row=8, column=2, columnspan=2, padx=5, pady=5, sticky="ew")
        
        # Pomodoro Tracker (Row 9)
        self.pomodoros_completed_label = ttk.Label(self.root, text=f"Pomodoros Completed: {self.pomodoro_count}")
        self.pomodoros_completed_label.grid(row=9, column=0, columnspan=2, padx=10, pady=10, sticky="w")
        self.reset_counter_button = ttk.Button(self.root, text="Reset Counter", command=self._reset_pomodoro_counter)
        self.reset_counter_button.grid(row=9, column=2, columnspan=2, padx=10, pady=10, sticky="e")

        self.root.grid_columnconfigure(0, weight=1)
        self.root.grid_columnconfigure(1, weight=1)
        self.root.grid_columnconfigure(2, weight=1)
        self.root.grid_columnconfigure(3, weight=1)
        self.root.grid_rowconfigure(2, weight=1)

        self._update_button_labels() # Set initial button texts based on loaded/default durations
        self._load_block_list_from_file()
        self._ensure_all_blocked_sites_are_unblocked_on_startup()
        self._update_ui_for_timer_state()


    def _create_menubar(self):
        menubar = tk.Menu(self.root)
        
        # Edit Menu
        edit_menu = tk.Menu(menubar, name='edit', tearoff=0) # 'name' helps with macOS integration
        edit_menu.add_command(label="Set Focus Duration...", command=self._edit_focus_duration)
        edit_menu.add_command(label="Set Short Break Duration...", command=self._edit_short_break_duration)
        edit_menu.add_command(label="Set Long Break Duration...", command=self._edit_long_break_duration)
        menubar.add_cascade(label="Edit", menu=edit_menu)

        # --- Standard macOS App Menu (File, Edit, Window, Help) ---
        # Tkinter on macOS usually creates a default app menu (with Quit).
        # For more control or to add items like "Preferences" to the app menu (not "Edit"),
        # you'd use specific tcl/tk commands or more platform-aware libraries.
        # For now, our "Edit" menu will appear alongside the default app menu.

        self.root.config(menu=menubar)

    def _load_settings(self):
        try:
            if CONFIG_FILE_PATH.exists():
                with open(CONFIG_FILE_PATH, "r", encoding='utf-8') as f:
                    settings = json.load(f)
                    self.focus_duration_minutes = int(settings.get("focus_duration_minutes", DEFAULT_FOCUS_DURATION_MINUTES))
                    self.short_break_duration_minutes = int(settings.get("short_break_duration_minutes", DEFAULT_SHORT_BREAK_DURATION_MINUTES))
                    self.long_break_duration_minutes = int(settings.get("long_break_duration_minutes", DEFAULT_LONG_BREAK_DURATION_MINUTES))
                    # Basic validation for loaded values
                    if not (0 < self.focus_duration_minutes <= 180): self.focus_duration_minutes = DEFAULT_FOCUS_DURATION_MINUTES
                    if not (0 < self.short_break_duration_minutes <= 60): self.short_break_duration_minutes = DEFAULT_SHORT_BREAK_DURATION_MINUTES
                    if not (0 < self.long_break_duration_minutes <= 90): self.long_break_duration_minutes = DEFAULT_LONG_BREAK_DURATION_MINUTES

            else: # Config file doesn't exist, use defaults and save them
                self._save_settings() # Save defaults if no file
        except (json.JSONDecodeError, ValueError, TypeError) as e: # Catch potential errors from loading/parsing
            print(f"Error loading settings: {e}. Using default values.")
            # Reset to defaults in case of corrupt file
            self.focus_duration_minutes = DEFAULT_FOCUS_DURATION_MINUTES
            self.short_break_duration_minutes = DEFAULT_SHORT_BREAK_DURATION_MINUTES
            self.long_break_duration_minutes = DEFAULT_LONG_BREAK_DURATION_MINUTES
            self._save_settings() # Try to save defaults
        except Exception as e:
            print(f"An unexpected error occurred loading settings: {e}. Using default values.")
            # Ensure defaults are set
            self.focus_duration_minutes = DEFAULT_FOCUS_DURATION_MINUTES
            self.short_break_duration_minutes = DEFAULT_SHORT_BREAK_DURATION_MINUTES
            self.long_break_duration_minutes = DEFAULT_LONG_BREAK_DURATION_MINUTES


    def _save_settings(self):
        settings = {
            "focus_duration_minutes": self.focus_duration_minutes,
            "short_break_duration_minutes": self.short_break_duration_minutes,
            "long_break_duration_minutes": self.long_break_duration_minutes,
        }
        try:
            with open(CONFIG_FILE_PATH, "w", encoding='utf-8') as f:
                json.dump(settings, f, indent=4)
            print("Settings saved.")
        except Exception as e:
            messagebox.showerror("Settings Error", f"Could not save timer settings: {e}")
            print(f"Error saving settings: {e}")

    def _update_button_labels(self):
        self.start_focus_button.config(text=f"Start Focus ({self.focus_duration_minutes} min)")
        self.start_short_break_button.config(text=f"Short Break ({self.short_break_duration_minutes} min)")
        self.start_long_break_button.config(text=f"Long Break ({self.long_break_duration_minutes} min)")

    def _edit_focus_duration(self):
        new_duration = simpledialog.askinteger(
            "Focus Duration", 
            "Enter focus duration (minutes):",
            parent=self.root,
            minvalue=1, 
            maxvalue=180, # e.g., 3 hours max
            initialvalue=self.focus_duration_minutes
        )
        if new_duration is not None:
            self.focus_duration_minutes = new_duration
            self._update_button_labels()
            self._save_settings()

    def _edit_short_break_duration(self):
        new_duration = simpledialog.askinteger(
            "Short Break Duration",
            "Enter short break duration (minutes):",
            parent=self.root,
            minvalue=1,
            maxvalue=60, 
            initialvalue=self.short_break_duration_minutes
        )
        if new_duration is not None:
            self.short_break_duration_minutes = new_duration
            self._update_button_labels()
            self._save_settings()

    def _edit_long_break_duration(self):
        new_duration = simpledialog.askinteger(
            "Long Break Duration",
            "Enter long break duration (minutes):",
            parent=self.root,
            minvalue=1,
            maxvalue=90,
            initialvalue=self.long_break_duration_minutes
        )
        if new_duration is not None:
            self.long_break_duration_minutes = new_duration
            self._update_button_labels()
            self._save_settings()

    # --- Existing methods ---
    # (Keep _is_admin, _read_hosts_file, _write_hosts_file, _load_block_list_from_file,
    #  _save_block_list_to_file, _update_listbox, _get_domains_to_manage, _add_website,
    #  _block_domains, _unblock_domains, _unblock_selected_website,
    #  _ensure_all_blocked_sites_are_unblocked_on_startup, _update_ui_for_timer_state,
    #  _stop_current_session, _tick_countdown, _reset_session_end_actions,
    #  _reset_pomodoro_counter, on_closing as they are, but update timer start methods)

    def _is_admin(self):
        try: return os.geteuid() == 0
        except AttributeError: return False

    def _read_hosts_file(self):
        try:
            with open(HOSTS_FILE_PATH, "r", encoding='utf-8') as f: return f.readlines()
        except FileNotFoundError: messagebox.showerror("Error", f"{HOSTS_FILE_PATH} not found."); return None
        except Exception as e: messagebox.showerror("Error", f"Could not read {HOSTS_FILE_PATH}: {e}"); return None

    def _write_hosts_file(self, lines):
        try:
            processed_lines = []
            if lines:
                for line in lines:
                    stripped_line = line.strip()
                    if stripped_line: processed_lines.append(stripped_line + "\n")
                if processed_lines and not processed_lines[-1].endswith("\n"): processed_lines[-1] += "\n"
            with open(HOSTS_FILE_PATH, "w", encoding='utf-8') as f: f.writelines(processed_lines)
            return True
        except PermissionError: messagebox.showerror("Permission Error", f"Could not write to {HOSTS_FILE_PATH}. Run with sudo."); return False
        except Exception as e: messagebox.showerror("Error", f"Could not write to {HOSTS_FILE_PATH}: {e}"); return False

    def _load_block_list_from_file(self):
        self.blocked_websites.clear()
        if BLOCK_LIST_FILE_PATH.exists():
            try:
                with open(BLOCK_LIST_FILE_PATH, "r", encoding='utf-8') as f:
                    for line in f:
                        site = line.strip()
                        if site: self.blocked_websites.add(site)
            except Exception as e: messagebox.showwarning("Load Error", f"Could not read {BLOCK_LIST_FILE_PATH}: {e}")
        self._update_listbox()

    def _save_block_list_to_file(self):
        try:
            with open(BLOCK_LIST_FILE_PATH, "w", encoding='utf-8') as f:
                for site in sorted(list(self.blocked_websites)): f.write(site + "\n")
        except Exception as e: messagebox.showerror("Save Error", f"Could not write to {BLOCK_LIST_FILE_PATH}: {e}")

    def _update_listbox(self):
        self.listbox.delete(0, tk.END)
        for site in sorted(list(self.blocked_websites)): self.listbox.insert(tk.END, site)

    def _get_domains_to_manage(self, domain):
        domains = {domain.lower()}
        if domain.startswith("www."): domains.add(domain[4:])
        else: domains.add("www." + domain)
        return domains

    def _add_website(self):
        website = self.website_entry.get().strip()
        if not website: messagebox.showwarning("Input Error", "Please enter a website domain."); return
        normalized_website = website.lower().replace("http://", "").replace("https://", "").split('/')[0]
        if not normalized_website: messagebox.showwarning("Input Error", "Invalid website domain entered."); return
        if normalized_website in self.blocked_websites:
            messagebox.showinfo("Already Blocked", f"{normalized_website} is already in the block list.")
            self.website_entry.delete(0, tk.END); return
        self.blocked_websites.add(normalized_website)
        self._save_block_list_to_file()
        self._update_listbox()
        self.website_entry.delete(0, tk.END)
        messagebox.showinfo("Success", f"{normalized_website} added to block list.")

    def _block_domains(self, domains_to_block_list):
        if not domains_to_block_list: return
        original_hosts_lines = self._read_hosts_file()
        if original_hosts_lines is None: return
        all_managed_variants_to_block = set()
        for domain_base in domains_to_block_list: all_managed_variants_to_block.update(self._get_domains_to_manage(domain_base))
        filtered_lines = []
        modified_by_removal = False
        for line in original_hosts_lines:
            stripped_line = line.strip()
            parts = stripped_line.split(None, 2)
            should_remove_line = False
            if len(parts) >= 2 and parts[0] == REDIRECT_IP and parts[1] in all_managed_variants_to_block:
                should_remove_line = True; modified_by_removal = True
            if not should_remove_line: filtered_lines.append(line)
        new_blocking_entries_to_add = [f"{REDIRECT_IP}\t{md}\t{POMODORO_COMMENT}\n" for md in sorted(list(all_managed_variants_to_block))]
        final_lines = filtered_lines + new_blocking_entries_to_add
        if modified_by_removal or new_blocking_entries_to_add:
            if self._write_hosts_file(final_lines): print(f"Hosts updated to block: {', '.join(domains_to_block_list)}")
        else: print(f"No changes for blocking: {', '.join(domains_to_block_list)}")

    def _unblock_domains(self, domains_to_unblock_list):
        if not domains_to_unblock_list: return
        original_hosts_lines = self._read_hosts_file()
        if original_hosts_lines is None: return
        all_managed_variants_to_unblock = set()
        for domain_base in domains_to_unblock_list: all_managed_variants_to_unblock.update(self._get_domains_to_manage(domain_base))
        new_lines = []
        modified = False
        for line in original_hosts_lines:
            keep_line = True
            stripped_line = line.strip()
            parts = stripped_line.split(None, 2)
            if len(parts) >= 2 and parts[0] == REDIRECT_IP and parts[1] in all_managed_variants_to_unblock:
                keep_line = False; modified = True
            if keep_line: new_lines.append(line)
        if modified:
            if self._write_hosts_file(new_lines): print(f"Hosts updated to unblock: {', '.join(domains_to_unblock_list)}")
        else: print(f"No unblocking changes for: {', '.join(domains_to_unblock_list)}")

    def _unblock_selected_website(self):
        selected_indices = self.listbox.curselection()
        if not selected_indices: messagebox.showwarning("Selection Error", "Please select a website to unblock."); return
        selected_website = self.listbox.get(selected_indices[0])
        self._unblock_domains([selected_website])
        if selected_website in self.blocked_websites: self.blocked_websites.remove(selected_website)
        self._save_block_list_to_file()
        self._update_listbox()
        messagebox.showinfo("Success", f"{selected_website} unblocked and removed from list.")

    def _ensure_all_blocked_sites_are_unblocked_on_startup(self):
        if BLOCK_LIST_FILE_PATH.exists():
            sites_from_file = []
            with open(BLOCK_LIST_FILE_PATH, "r", encoding='utf-8') as f:
                for line in f:
                    site = line.strip()
                    if site: sites_from_file.append(site)
            if sites_from_file:
                print(f"Ensuring sites unblocked on startup: {sites_from_file}")
                self._unblock_domains(sites_from_file)

    def _update_ui_for_timer_state(self):
        if self.timer_running:
            self.start_focus_button.config(state=tk.DISABLED)
            self.start_short_break_button.config(state=tk.DISABLED)
            self.start_long_break_button.config(state=tk.DISABLED)
            self.stop_session_button.config(state=tk.NORMAL)
            self.add_button.config(state=tk.DISABLED)
            self.unblock_button.config(state=tk.DISABLED)
            self.reset_counter_button.config(state=tk.DISABLED)
        else: # Idle state
            self.start_focus_button.config(state=tk.NORMAL)
            self.start_short_break_button.config(state=tk.NORMAL)
            self.start_long_break_button.config(state=tk.NORMAL)
            self.stop_session_button.config(state=tk.DISABLED)
            self.add_button.config(state=tk.NORMAL)
            self.unblock_button.config(state=tk.NORMAL)
            self.reset_counter_button.config(state=tk.NORMAL)
            self.timer_label.config(text="Status: Idle")
            self.countdown_label.config(text="Time: 00:00")

    def _start_focus_session(self):
        if self.timer_running: messagebox.showwarning("Timer Active", "A session is already in progress."); return
        if not self.blocked_websites and not messagebox.askyesno("No Websites Blocked", "Your block list is empty. Start focus anyway?"): return
        self.timer_running = True
        self.current_state = "Focus"
        self.timer_label.config(text="Status: Focus Time")
        self._update_ui_for_timer_state()
        self._block_domains(list(self.blocked_websites))
        self.remaining_seconds = self.focus_duration_minutes * 60 # Use configured duration
        self._tick_countdown()

    def _start_automatic_break_session(self):
        self.timer_running = True
        self.current_state = "Break"
        self.timer_label.config(text=f"Status: Short Break ({self.short_break_duration_minutes} min)") # Use configured
        self.remaining_seconds = self.short_break_duration_minutes * 60 # Use configured
        self._tick_countdown()

    def _start_short_break_session(self):
        if self.timer_running: messagebox.showwarning("Timer Active", "A session is already in progress."); return
        self.timer_running = True
        self.current_state = "Break"
        self.timer_label.config(text=f"Status: Short Break ({self.short_break_duration_minutes} min)") # Use configured
        self._update_ui_for_timer_state()
        self.remaining_seconds = self.short_break_duration_minutes * 60 # Use configured
        self._tick_countdown()

    def _start_long_break_session(self):
        if self.timer_running: messagebox.showwarning("Timer Active", "A session is already in progress."); return
        self.timer_running = True
        self.current_state = "Break"
        self.timer_label.config(text=f"Status: Long Break ({self.long_break_duration_minutes} min)") # Use configured
        self._update_ui_for_timer_state()
        self.remaining_seconds = self.long_break_duration_minutes * 60 # Use configured
        self._tick_countdown()

    def _stop_current_session(self):
        if not self.timer_running: return
        was_focus_session = (self.current_state == "Focus")
        self.timer_running = False
        if self._timer_id: self.root.after_cancel(self._timer_id); self._timer_id = None
        current_session_type = self.current_state
        self.current_state = "Idle"
        self.remaining_seconds = 0
        if was_focus_session:
            self._unblock_domains(list(self.blocked_websites))
            self.timer_label.config(text="Status: Focus Stopped")
        elif current_session_type == "Break": self.timer_label.config(text="Status: Break Stopped")
        else: self.timer_label.config(text="Status: Session Stopped")
        self.countdown_label.config(text="Time: 00:00")
        self._update_ui_for_timer_state()

    def _tick_countdown(self):
        if not self.timer_running or self.remaining_seconds < 0:
            if self.current_state != "Idle": self._reset_session_end_actions()
            return
        mins, secs = divmod(self.remaining_seconds, 60)
        time_format = f"{mins:02d}:{secs:02d}"
        self.countdown_label.config(text=f"Time: {time_format}")
        if self.remaining_seconds == 0: self._handle_natural_session_completion()
        else:
            self.remaining_seconds -= 1
            self._timer_id = self.root.after(1000, self._tick_countdown)

    def _handle_natural_session_completion(self):
        if self.current_state == "Focus":
            self.pomodoro_count += 1
            self.pomodoros_completed_label.config(text=f"Pomodoros Completed: {self.pomodoro_count}")
            messagebox.showinfo("Focus Ended", "Focus session complete! Time for an automatic short break.")
            self._unblock_domains(list(self.blocked_websites))
            self._start_automatic_break_session()
        elif self.current_state == "Break":
            messagebox.showinfo("Break Over", "Break time is over!")
            self._reset_session_end_actions()

    def _reset_session_end_actions(self):
        was_focus_before_idle = (self.current_state == "Focus")
        self.timer_running = False
        self.current_state = "Idle"
        if self._timer_id: self.root.after_cancel(self._timer_id); self._timer_id = None
        if was_focus_before_idle and self.blocked_websites: self._unblock_domains(list(self.blocked_websites))
        self._update_ui_for_timer_state()

    def _reset_pomodoro_counter(self):
        if self.timer_running: messagebox.showwarning("Session Active", "Cannot reset counter during an active session."); return
        if messagebox.askyesno("Reset Counter", "Are you sure you want to reset the Pomodoro counter?"):
            self.pomodoro_count = 0
            self.pomodoros_completed_label.config(text=f"Pomodoros Completed: {self.pomodoro_count}")

    def on_closing(self):
        # Save settings on close
        self._save_settings()
        
        if self.timer_running:
            self.timer_running = False
            if self._timer_id: self.root.after_cancel(self._timer_id); self._timer_id = None
        
        print("Application closing.")
        if self.blocked_websites:
             print("Ensuring sites from list are unblocked on close.")
             self._unblock_domains(list(self.blocked_websites))
        self.root.destroy()

if __name__ == "__main__":
    main_root = tk.Tk()
    is_admin_check = False
    try: is_admin_check = (os.geteuid() == 0)
    except AttributeError: is_admin_check = False

    if not is_admin_check:
        try: messagebox.showerror("Admin Privileges Required", "This application must be run with sudo privileges.")
        except tk.TclError: print("Error: Admin Privileges Required.", file=sys.stderr)
        main_root.destroy()
        sys.exit(1)

    app = PomodoroWebsiteBlocker(main_root)
    if hasattr(app, 'root') and app.root.winfo_exists():
        # Ensure the window has focus for the menubar to be properly associated on some setups.
        main_root.focus_force() 
        main_root.protocol("WM_DELETE_WINDOW", app.on_closing)
        main_root.mainloop()
    else: print("Application could not start.")