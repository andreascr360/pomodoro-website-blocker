import tkinter as tk
from tkinter import ttk, messagebox, simpledialog
import os
import sys
from pathlib import Path
import json
import math

# Constants
HOSTS_FILE_PATH = "/etc/hosts"
BLOCK_LIST_FILE_PATH = Path.home() / ".website_blocker_list.txt"
CONFIG_FILE_PATH = Path.home() / ".pomodoro_blocker_settings.json"
REDIRECT_IP = "127.0.0.1"
POMODORO_COMMENT = "# Added by PomodoroBlocker"

DEFAULT_FOCUS_DURATION_MINUTES = 25
DEFAULT_SHORT_BREAK_DURATION_MINUTES = 5
DEFAULT_LONG_BREAK_DURATION_MINUTES = 15
DEFAULT_EATING_BREAK_DURATION_MINUTES = 30
DEFAULT_POMODOROS_FOR_FULL_XP = 4

# Circle Timer Constants
CIRCLE_CANVAS_SIZE = 200
CIRCLE_PADDING = 10
CIRCLE_THICKNESS = 10
CIRCLE_BG_COLOR = "grey70"
CIRCLE_FG_COLOR_FOCUS = "tomato"
CIRCLE_FG_COLOR_BREAK = "medium sea green"
CIRCLE_TEXT_COLOR = "black"

# XP Bar Constants
XP_BAR_HEIGHT = 25
XP_BAR_WIDTH_FACTOR = 0.9
XP_BAR_BG_COLOR = "grey50"
XP_BAR_FG_COLOR = "light green"
XP_BAR_SHADOW_COLOR = "white"
XP_BAR_TEXT_COLOR = "black"
XP_BAR_CORNER_RADIUS = 8

# Icon Constants
STOP_ICON_SIZE = 50
STOP_ICON_PADDING = 5
STOP_ICON_SQUARE_COLOR_ACTIVE = "firebrick"
STOP_ICON_SQUARE_COLOR_DISABLED = "gray60"

PAUSE_PLAY_ICON_SIZE = 50
PAUSE_PLAY_ICON_PADDING = 6 # Adjusted for better visual balance of play/pause symbols
PAUSE_ICON_COLOR_ACTIVE = "dodger blue"
PLAY_ICON_COLOR_ACTIVE = "lime green"
PAUSE_PLAY_ICON_COLOR_DISABLED = "gray70"


# +++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++
# BlockListManagerWindow Class (Remains Unchanged)
# +++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++
class BlockListManagerWindow(tk.Toplevel):
    def __init__(self, master, app_controller):
        super().__init__(master)
        self.app_controller = app_controller
        self.title("Manage Blocked Websites")
        self.geometry("450x400")
        self.transient(master)
        self.grab_set()

        ttk.Label(self, text="Website (e.g., example.com):").grid(row=0, column=0, padx=10, pady=5, sticky="w")
        self.website_entry_manager = ttk.Entry(self, width=30)
        self.website_entry_manager.grid(row=0, column=1, padx=10, pady=5, sticky="ew")

        self.add_button_manager = ttk.Button(self, text="Add to Block List", command=self._ui_add_website)
        self.add_button_manager.grid(row=0, column=2, padx=5, pady=5)

        ttk.Label(self, text="Blocked Websites:").grid(row=1, column=0, padx=10, pady=5, sticky="nw")
        self.listbox_frame_manager = ttk.Frame(self)
        self.listbox_frame_manager.grid(row=2, column=0, columnspan=3, padx=10, pady=5, sticky="nsew")

        self.listbox_manager = tk.Listbox(self.listbox_frame_manager, selectmode=tk.SINGLE, height=10)
        self.listbox_scrollbar_manager = ttk.Scrollbar(self.listbox_frame_manager, orient=tk.VERTICAL, command=self.listbox_manager.yview)
        self.listbox_manager.configure(yscrollcommand=self.listbox_scrollbar_manager.set)
        self.listbox_manager.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        self.listbox_scrollbar_manager.pack(side=tk.RIGHT, fill=tk.Y)

        self.unblock_button_manager = ttk.Button(self, text="Unblock Selected", command=self._ui_unblock_selected_website)
        self.unblock_button_manager.grid(row=3, column=0, columnspan=3, padx=10, pady=10)

        self.close_button = ttk.Button(self, text="Done", command=self.destroy)
        self.close_button.grid(row=4, column=0, columnspan=3, padx=10, pady=10)

        self.grid_columnconfigure(1, weight=1)
        self.grid_rowconfigure(2, weight=1)
        self._refresh_listbox()

    def _refresh_listbox(self):
        self.listbox_manager.delete(0, tk.END)
        for site in sorted(list(self.app_controller.blocked_websites)):
            self.listbox_manager.insert(tk.END, site)

    def _ui_add_website(self):
        website = self.website_entry_manager.get().strip()
        if not website:
            messagebox.showwarning("Input Error", "Please enter a website domain.", parent=self)
            return
        normalized_website = website.lower().replace("http://", "").replace("https://", "").split('/')[0]
        if not normalized_website:
            messagebox.showwarning("Input Error", "Invalid website domain entered.", parent=self)
            return
        success, message = self.app_controller.add_domain_to_blocklist_core(normalized_website)
        if success:
            self._refresh_listbox()
            self.website_entry_manager.delete(0, tk.END)
            messagebox.showinfo("Success", message, parent=self)
        else:
            messagebox.showwarning("Info", message, parent=self)

    def _ui_unblock_selected_website(self):
        selected_indices = self.listbox_manager.curselection()
        if not selected_indices:
            messagebox.showwarning("Selection Error", "Please select a website to unblock.", parent=self)
            return
        selected_website = self.listbox_manager.get(selected_indices[0])
        success, message = self.app_controller.remove_domain_from_blocklist_core(selected_website)
        if success:
            self._refresh_listbox()
            messagebox.showinfo("Success", message, parent=self)
        else:
            messagebox.showerror("Error", "Could not unblock selected website.", parent=self)

# +++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++
# PomodoroWebsiteBlocker Class
# +++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++
class PomodoroWebsiteBlocker:
    def __init__(self, root_window):
        self.root = root_window
        self.root.title("Pomodoro XP Blocker")
        self.root.geometry(f"500x{580 + CIRCLE_CANVAS_SIZE // 3}") # Adjusted for new layout

        if not self._is_admin():
            messagebox.showerror("Admin Privileges Required", "This application must be run with sudo privileges.")
            self.root.destroy(); return

        self.focus_duration_minutes = DEFAULT_FOCUS_DURATION_MINUTES
        self.short_break_duration_minutes = DEFAULT_SHORT_BREAK_DURATION_MINUTES
        self.long_break_duration_minutes = DEFAULT_LONG_BREAK_DURATION_MINUTES
        self.eating_break_duration_minutes = DEFAULT_EATING_BREAK_DURATION_MINUTES
        self.pomodoros_for_full_xp = DEFAULT_POMODOROS_FOR_FULL_XP
        self._load_settings()

        self.blocked_websites = set()
        self.pomodoro_count = 0
        self.timer_running = False
        self.timer_paused = False # NEW
        self.current_state = "Idle"
        self.current_break_type = ""
        self.remaining_seconds = 0
        self.total_seconds_for_session = 0
        self._timer_id = None
        self.block_list_manager_window = None

        self._create_menubar()

        # --- UI Layout ---
        # Row 0: Separator
        ttk.Separator(self.root, orient='horizontal').grid(row=0, column=0, columnspan=4, sticky='ew', pady=5)

        # Row 1: Status Label
        self.timer_label = ttk.Label(self.root, text="Status: Idle", font=("Helvetica", 14))
        self.timer_label.grid(row=1, column=0, columnspan=4, padx=10, pady=5)

        # --- Row 2: Control Icons and Circular Timer ---
        timer_controls_frame = ttk.Frame(self.root)
        # Grid the frame to span all columns and allow it to expand horizontally
        timer_controls_frame.grid(row=2, column=0, columnspan=4, sticky="ew", pady=10)
        # Make the frame's single column (where we'll pack) expand to fill the space
        timer_controls_frame.grid_columnconfigure(0, weight=1)


        # Stop Icon (Left) - Pack it to the left within the frame
        self.stop_icon_canvas = tk.Canvas(timer_controls_frame, width=STOP_ICON_SIZE, height=STOP_ICON_SIZE,
                                          bg=self.root.cget('bg'), highlightthickness=0, cursor="hand2")
        self.stop_icon_canvas.pack(side=tk.LEFT, padx=(30, 5), pady=5) # padx (left, right)
        self.stop_icon_canvas.bind("<Button-1>", self._on_stop_icon_click)
        self._draw_stop_icon(is_enabled=False)

        # Pause/Play Icon (Right) - Pack it to the right within the frame
        self.pause_play_icon_canvas = tk.Canvas(timer_controls_frame, width=PAUSE_PLAY_ICON_SIZE, height=PAUSE_PLAY_ICON_SIZE,
                                                bg=self.root.cget('bg'), highlightthickness=0, cursor="hand2")
        self.pause_play_icon_canvas.pack(side=tk.RIGHT, padx=(5, 30), pady=5)
        self.pause_play_icon_canvas.bind("<Button-1>", self._on_pause_play_icon_click)
        self._draw_pause_play_icon(show_play=True, is_enabled=False)
        
        # Circular Timer Canvas (Middle) - Pack it to fill remaining space, it will center
        self.timer_canvas = tk.Canvas(timer_controls_frame, width=CIRCLE_CANVAS_SIZE, height=CIRCLE_CANVAS_SIZE,
                                      bg=self.root.cget('bg'), highlightthickness=0)
        # Using pack with expand=True and fill=tk.BOTH would make it take all space.
        # We want it to center its fixed size.
        # Packing it last *without* expand=True should center it in the available space
        # between the left and right packed items.
        self.timer_canvas.pack(side=tk.TOP, pady=5, expand=False) # Let it take its natural size, pack will center it
        self._setup_timer_canvas_elements()


        # Row 3: Start Focus Button
        self.start_focus_button = ttk.Button(self.root, text="", command=self._start_focus_session)
        self.start_focus_button.grid(row=3, column=0, columnspan=4, padx=5, pady=10, sticky="ew")

        # Row 4: Standard Break Buttons
        self.start_short_break_button = ttk.Button(self.root, text="", command=self._start_short_break_session)
        self.start_short_break_button.grid(row=4, column=0, columnspan=2, padx=5, pady=10, sticky="ew")
        self.start_long_break_button = ttk.Button(self.root, text="", command=self._start_long_break_session)
        self.start_long_break_button.grid(row=4, column=2, columnspan=2, padx=5, pady=10, sticky="ew")

        # Row 5: Eating Break Button
        self.start_eating_break_button = ttk.Button(self.root, text="", command=self._start_eating_break_session)
        self.start_eating_break_button.grid(row=5, column=0, columnspan=4, padx=5, pady=10, sticky="ew")

        # Row 6: XP Bar
        self.xp_bar_canvas = tk.Canvas(self.root, height=XP_BAR_HEIGHT + 25,
                                       bg=self.root.cget('bg'), highlightthickness=0)
        self.xp_bar_canvas.grid(row=6, column=0, columnspan=4, padx=10, pady=(10,15), sticky="ew")

        for i in range(4): self.root.grid_columnconfigure(i, weight=1)

        self._update_button_labels()
        self._load_block_list_from_file()
        self._ensure_all_blocked_sites_are_unblocked_on_startup()
        self._update_timer_display()
        self._draw_xp_bar()
        self._update_ui_for_timer_state()

        self.root.bind("<Configure>", self._on_window_resize)

    def _on_window_resize(self, event=None):
        if hasattr(self, 'xp_bar_canvas') and self.xp_bar_canvas.winfo_exists():
            self._draw_xp_bar()

    def _create_rounded_rect(self, canvas, x1, y1, x2, y2, radius, **kwargs):
        points = [x1 + radius, y1, x1 + radius, y1, x2 - radius, y1, x2 - radius, y1, x2, y1, x2, y1 + radius, x2, y1 + radius, x2, y2 - radius, x2, y2 - radius, x2, y2, x2 - radius, y2, x2 - radius, y2, x1 + radius, y2, x1 + radius, y2, x1, y2, x1, y2 - radius, x1, y2 - radius, x1, y1 + radius, x1, y1 + radius, x1, y1]
        return canvas.create_polygon(points, **kwargs, smooth=True)

    def _draw_xp_bar(self):
        if not hasattr(self, 'xp_bar_canvas') or not self.xp_bar_canvas.winfo_exists(): return
        self.xp_bar_canvas.delete("all")
        canvas_width = self.xp_bar_canvas.winfo_width(); bar_x_start = 10; bar_y_start = 5
        if canvas_width <= 1: canvas_width = int(self.root.winfo_width() * XP_BAR_WIDTH_FACTOR * 0.95) if self.root.winfo_width() > 10 else 400 # Ensure root width is available
        bar_width = canvas_width - (bar_x_start * 2) # Adjust for padding on both sides
        
        self._create_rounded_rect(self.xp_bar_canvas, bar_x_start, bar_y_start, bar_x_start + bar_width, bar_y_start + XP_BAR_HEIGHT, XP_BAR_CORNER_RADIUS, fill=XP_BAR_BG_COLOR, outline=XP_BAR_BG_COLOR)
        xp_percentage = min(self.pomodoro_count / self.pomodoros_for_full_xp, 1.0) if self.pomodoros_for_full_xp > 0 else 0
        filled_width = bar_width * xp_percentage
        if filled_width > 0:
            self._create_rounded_rect(self.xp_bar_canvas, bar_x_start, bar_y_start, bar_x_start + filled_width, bar_y_start + XP_BAR_HEIGHT, XP_BAR_CORNER_RADIUS, fill=XP_BAR_FG_COLOR, outline=XP_BAR_FG_COLOR)
            highlight_thickness = 1
            if filled_width > highlight_thickness * 2 and XP_BAR_HEIGHT > highlight_thickness * 2:
                self.xp_bar_canvas.create_line(bar_x_start + XP_BAR_CORNER_RADIUS, bar_y_start + highlight_thickness, bar_x_start + filled_width - XP_BAR_CORNER_RADIUS, bar_y_start + highlight_thickness, fill=XP_BAR_SHADOW_COLOR, width=highlight_thickness)
                self.xp_bar_canvas.create_line(bar_x_start + highlight_thickness, bar_y_start + XP_BAR_CORNER_RADIUS, bar_x_start + highlight_thickness, bar_y_start + XP_BAR_HEIGHT - XP_BAR_CORNER_RADIUS, fill=XP_BAR_SHADOW_COLOR, width=highlight_thickness)
                if XP_BAR_CORNER_RADIUS > highlight_thickness:
                    arc_bbox_tl = (bar_x_start + highlight_thickness, bar_y_start + highlight_thickness, bar_x_start + (XP_BAR_CORNER_RADIUS * 2) - highlight_thickness, bar_y_start + (XP_BAR_CORNER_RADIUS * 2) - highlight_thickness)
                    self.xp_bar_canvas.create_arc(arc_bbox_tl, start=90, extent=90, style=tk.ARC, outline=XP_BAR_SHADOW_COLOR, width=highlight_thickness)
        xp_text = f"XP: {self.pomodoro_count} / {self.pomodoros_for_full_xp} Pomodoros"
        self.xp_bar_canvas.create_text(bar_x_start + bar_width / 2, bar_y_start + XP_BAR_HEIGHT + 10, text=xp_text, font=("Helvetica", 10), fill=XP_BAR_TEXT_COLOR, anchor=tk.CENTER)

    def _setup_timer_canvas_elements(self):
        center_x = CIRCLE_CANVAS_SIZE / 2; center_y = CIRCLE_CANVAS_SIZE / 2
        radius = (CIRCLE_CANVAS_SIZE / 2) - CIRCLE_PADDING
        x0, y0, x1, y1 = center_x - radius, center_y - radius, center_x + radius, center_y + radius
        self.arc_bbox = (x0, y0, x1, y1)
        self.timer_canvas.create_arc(self.arc_bbox, start=0, extent=359.9, outline=CIRCLE_BG_COLOR, width=CIRCLE_THICKNESS, style=tk.ARC)
        self.progress_arc_id = self.timer_canvas.create_arc(self.arc_bbox, start=90, extent=0, outline=CIRCLE_FG_COLOR_FOCUS, width=CIRCLE_THICKNESS, style=tk.ARC)
        self.time_text_id = self.timer_canvas.create_text(center_x, center_y, text="00:00", font=("Helvetica", int(CIRCLE_CANVAS_SIZE/5), "bold"), fill=CIRCLE_TEXT_COLOR)

    def _update_timer_display(self):
        mins, secs = divmod(self.remaining_seconds, 60)
        time_format = f"{mins:02d}:{secs:02d}"
        self.timer_canvas.itemconfig(self.time_text_id, text=time_format)
        progress_extent = 0; current_fg_color = CIRCLE_FG_COLOR_FOCUS
        if self.timer_running and self.total_seconds_for_session > 0:
            elapsed_seconds = self.total_seconds_for_session - self.remaining_seconds
            progress_percentage = elapsed_seconds / self.total_seconds_for_session
            progress_extent = progress_percentage * 359.9
            if self.current_state == "Focus": current_fg_color = CIRCLE_FG_COLOR_FOCUS
            elif self.current_state == "Break": current_fg_color = CIRCLE_FG_COLOR_BREAK
        self.timer_canvas.itemconfig(self.progress_arc_id, extent=-progress_extent, outline=current_fg_color)
        
        if self.timer_running:
            if self.timer_paused:
                self.timer_label.config(text="Status: Paused")
            elif self.current_state == "Focus":
                self.timer_label.config(text="Status: Focus Time")
            elif self.current_state == "Break":
                dur_attr = f"{self.current_break_type.lower()}_break_duration_minutes"
                duration = getattr(self, dur_attr, "?")
                self.timer_label.config(text=f"Status: {self.current_break_type} Break ({duration} min)")
        else:
            self.timer_label.config(text="Status: Idle")

    def _create_menubar(self):
        menubar = tk.Menu(self.root); edit_menu = tk.Menu(menubar, name='edit', tearoff=0)
        edit_menu.add_command(label="Manage Blocked Websites...", command=self._open_block_list_manager); edit_menu.add_separator()
        edit_menu.add_command(label="Set Focus Duration...", command=self._edit_focus_duration)
        edit_menu.add_command(label="Set Short Break Duration...", command=self._edit_short_break_duration)
        edit_menu.add_command(label="Set Long Break Duration...", command=self._edit_long_break_duration)
        edit_menu.add_command(label="Set Eating Break Duration...", command=self._edit_eating_break_duration); edit_menu.add_separator()
        edit_menu.add_command(label="Set Pomodoros for Full XP...", command=self._edit_pomodoros_for_full_xp)
        menubar.add_cascade(label="Edit", menu=edit_menu); self.root.config(menu=menubar)

    def _load_settings(self):
        try:
            if CONFIG_FILE_PATH.exists():
                with open(CONFIG_FILE_PATH, "r", encoding='utf-8') as f: settings = json.load(f)
                self.focus_duration_minutes = int(settings.get("focus_duration_minutes", DEFAULT_FOCUS_DURATION_MINUTES))
                self.short_break_duration_minutes = int(settings.get("short_break_duration_minutes", DEFAULT_SHORT_BREAK_DURATION_MINUTES))
                self.long_break_duration_minutes = int(settings.get("long_break_duration_minutes", DEFAULT_LONG_BREAK_DURATION_MINUTES))
                self.eating_break_duration_minutes = int(settings.get("eating_break_duration_minutes", DEFAULT_EATING_BREAK_DURATION_MINUTES))
                self.pomodoros_for_full_xp = int(settings.get("pomodoros_for_full_xp", DEFAULT_POMODOROS_FOR_FULL_XP))
                if not (0 < self.focus_duration_minutes <= 180): self.focus_duration_minutes = DEFAULT_FOCUS_DURATION_MINUTES
                if not (0 < self.short_break_duration_minutes <= 60): self.short_break_duration_minutes = DEFAULT_SHORT_BREAK_DURATION_MINUTES
                if not (0 < self.long_break_duration_minutes <= 90): self.long_break_duration_minutes = DEFAULT_LONG_BREAK_DURATION_MINUTES
                if not (5 <= self.eating_break_duration_minutes <= 120): self.eating_break_duration_minutes = DEFAULT_EATING_BREAK_DURATION_MINUTES
                if not (1 <= self.pomodoros_for_full_xp <= 100): self.pomodoros_for_full_xp = DEFAULT_POMODOROS_FOR_FULL_XP
            else: self._save_settings()
        except Exception as e: print(f"Error loading settings: {e}. Using defaults."); self._reset_to_default_settings_and_save()

    def _reset_to_default_settings_and_save(self):
        self.focus_duration_minutes = DEFAULT_FOCUS_DURATION_MINUTES; self.short_break_duration_minutes = DEFAULT_SHORT_BREAK_DURATION_MINUTES
        self.long_break_duration_minutes = DEFAULT_LONG_BREAK_DURATION_MINUTES; self.eating_break_duration_minutes = DEFAULT_EATING_BREAK_DURATION_MINUTES
        self.pomodoros_for_full_xp = DEFAULT_POMODOROS_FOR_FULL_XP; self._save_settings()

    def _save_settings(self):
        settings = {"focus_duration_minutes": self.focus_duration_minutes, "short_break_duration_minutes": self.short_break_duration_minutes, "long_break_duration_minutes": self.long_break_duration_minutes, "eating_break_duration_minutes": self.eating_break_duration_minutes, "pomodoros_for_full_xp": self.pomodoros_for_full_xp}
        try:
            CONFIG_FILE_PATH.parent.mkdir(parents=True, exist_ok=True)
            with open(CONFIG_FILE_PATH, "w", encoding='utf-8') as f: json.dump(settings, f, indent=4)
            print("Settings saved.")
        except Exception as e: messagebox.showerror("Settings Error", f"Could not save timer settings: {e}", parent=self.root); print(f"Error saving settings: {e}")

    def _edit_eating_break_duration(self):
        new_duration = simpledialog.askinteger("Eating Break Duration", "Enter eating break duration (minutes, 5-120):", parent=self.root, minvalue=5, maxvalue=120, initialvalue=self.eating_break_duration_minutes)
        if new_duration is not None: self.eating_break_duration_minutes = new_duration; self._update_button_labels(); self._save_settings()

    def _edit_pomodoros_for_full_xp(self):
        new_value = simpledialog.askinteger("XP Goal", "Enter Pomodoros needed for full XP bar (1-100):", parent=self.root, minvalue=1, maxvalue=100, initialvalue=self.pomodoros_for_full_xp)
        if new_value is not None: self.pomodoros_for_full_xp = new_value; self._save_settings(); self._draw_xp_bar()
        if self.pomodoro_count >= self.pomodoros_for_full_xp: messagebox.showinfo("XP Goal Met!", "You've already met or exceeded the new XP goal!", parent=self.root)

    def _update_button_labels(self):
        self.start_focus_button.config(text=f"Start Focus ({self.focus_duration_minutes} min)")
        self.start_short_break_button.config(text=f"Short Break ({self.short_break_duration_minutes} min)")
        self.start_long_break_button.config(text=f"Long Break ({self.long_break_duration_minutes} min)")
        self.start_eating_break_button.config(text=f"Eating Break ({self.eating_break_duration_minutes} min)")

    def _update_ui_for_timer_state(self): # UPDATED
        timer_is_on = self.timer_running
        
        self.start_focus_button.config(state=tk.DISABLED if timer_is_on else tk.NORMAL)
        self.start_short_break_button.config(state=tk.DISABLED if timer_is_on else tk.NORMAL)
        self.start_long_break_button.config(state=tk.DISABLED if timer_is_on else tk.NORMAL)
        self.start_eating_break_button.config(state=tk.DISABLED if timer_is_on else tk.NORMAL)
        
        self._draw_stop_icon(is_enabled=timer_is_on)
        
        if timer_is_on:
            self._draw_pause_play_icon(show_play=self.timer_paused, is_enabled=True)
        else: # Timer not running
            self._draw_pause_play_icon(show_play=True, is_enabled=False) # Show play, disabled

        self._update_timer_display()

    def _handle_natural_session_completion(self):
        self.timer_paused = False # Reset pause state
        session_that_completed = self.current_state
        if self._timer_id: self.root.after_cancel(self._timer_id); self._timer_id = None
        if session_that_completed == "Focus":
            self.pomodoro_count += 1; self._draw_xp_bar()
            if self.pomodoro_count == self.pomodoros_for_full_xp: messagebox.showinfo("XP Goal Reached!", "Congratulations! You've filled the XP bar!", parent=self.root)
            if self.blocked_websites: self._unblock_domains(list(self.blocked_websites))
            messagebox.showinfo("Focus Ended", "Focus session complete! Time for a break.", parent=self.root)
            self._reset_session_end_actions()
        elif session_that_completed == "Break":
            messagebox.showinfo("Break Over", f"{self.current_break_type} break is over! Ready for next session?", parent=self.root)
            self._reset_session_end_actions()

    def _draw_stop_icon(self, is_enabled=True):
        self.stop_icon_canvas.delete("all")
        square_color = STOP_ICON_SQUARE_COLOR_ACTIVE if is_enabled else STOP_ICON_SQUARE_COLOR_DISABLED
        self.stop_icon_canvas.create_rectangle(STOP_ICON_PADDING, STOP_ICON_PADDING, STOP_ICON_SIZE - STOP_ICON_PADDING, STOP_ICON_SIZE - STOP_ICON_PADDING, fill=square_color, outline=square_color)

    def _on_stop_icon_click(self, event=None):
        if self.timer_running: self._stop_current_session()

    def _draw_pause_play_icon(self, show_play=True, is_enabled=True): # UPDATED
        self.pause_play_icon_canvas.delete("all")
        pad = PAUSE_PLAY_ICON_PADDING
        size = PAUSE_PLAY_ICON_SIZE
        
        if not is_enabled:
            icon_color = PAUSE_PLAY_ICON_COLOR_DISABLED
            # Draw Play symbol (triangle) greyed out
            points = [pad, pad, pad, size - pad, size - pad, size / 2]
            self.pause_play_icon_canvas.create_polygon(points, fill=icon_color, outline=icon_color)
        elif show_play:
            icon_color = PLAY_ICON_COLOR_ACTIVE
            points = [pad, pad, pad, size - pad, size - pad, size / 2]
            self.pause_play_icon_canvas.create_polygon(points, fill=icon_color, outline=icon_color)
        else: # Draw Pause symbol (two vertical bars)
            icon_color = PAUSE_ICON_COLOR_ACTIVE
            bar_width = (size - (pad * 2) - pad / 1.5) / 2 # Adjusted for slightly thicker bars and gap
            gap = pad / 1.5
            # Left bar
            self.pause_play_icon_canvas.create_rectangle(pad, pad, pad + bar_width, size - pad, fill=icon_color, outline=icon_color)
            # Right bar
            self.pause_play_icon_canvas.create_rectangle(pad + bar_width + gap, pad, pad + bar_width * 2 + gap, size - pad, fill=icon_color, outline=icon_color)

    def _on_pause_play_icon_click(self, event=None): # UPDATED
        if not self.timer_running: return

        if self.timer_paused: # If paused, then play
            self.timer_paused = False
            # _update_ui_for_timer_state will redraw the icon
            self._tick_countdown() # Resume countdown
            print("Timer Resumed")
        else: # If playing, then pause
            self.timer_paused = True
            if self._timer_id: self.root.after_cancel(self._timer_id)
            # _update_ui_for_timer_state will redraw the icon
            print("Timer Paused")
        self._update_ui_for_timer_state() # Crucial to update icon and status label


    def _start_session_common(self, state_name, break_type_name, duration_minutes): # NEW helper
        if self.timer_running: messagebox.showwarning("Timer Active", "A session is already in progress.", parent=self.root); return False
        
        if state_name == "Focus" and not self.blocked_websites and \
           not messagebox.askyesno("No Websites Blocked", "Your block list is empty. Start focus anyway?", parent=self.root):
            return False

        self.timer_running = True
        self.timer_paused = False
        self.current_state = state_name
        self.current_break_type = break_type_name
        self.total_seconds_for_session = duration_minutes * 60
        self.remaining_seconds = self.total_seconds_for_session
        
        if state_name == "Focus" and self.blocked_websites:
            self._block_domains(list(self.blocked_websites))
        
        self._update_ui_for_timer_state()
        self._tick_countdown()
        return True

    def _start_focus_session(self):
        self._start_session_common("Focus", "", self.focus_duration_minutes)
    def _start_short_break_session(self):
        self._start_session_common("Break", "Short", self.short_break_duration_minutes)
    def _start_long_break_session(self):
        self._start_session_common("Break", "Long", self.long_break_duration_minutes)
    def _start_eating_break_session(self):
        self._start_session_common("Break", "Eating", self.eating_break_duration_minutes)

    def _stop_current_session(self):
        if not self.timer_running: return
        was_focus_session = (self.current_state == "Focus")
        stopped_break_type = self.current_break_type if self.current_state == "Break" else ""
        
        self.timer_running = False
        self.timer_paused = False # Reset pause state
        if self._timer_id: self.root.after_cancel(self._timer_id); self._timer_id = None
        
        self.current_state = "Idle"; self.current_break_type = ""
        self.remaining_seconds = 0; self.total_seconds_for_session = 0
        
        if was_focus_session and self.blocked_websites: self._unblock_domains(list(self.blocked_websites))
        
        log_message = "Focus session stopped." if was_focus_session else f"{stopped_break_type} break stopped."
        print(log_message)
        self._update_ui_for_timer_state()

    def _tick_countdown(self):
        if self.timer_paused: return # If paused, do nothing this tick
        if not self.timer_running or self.remaining_seconds < 0:
            if self.current_state != "Idle": self._reset_session_end_actions()
            return
        self._update_timer_display()
        if self.remaining_seconds == 0: self._handle_natural_session_completion()
        else: self.remaining_seconds -= 1; self._timer_id = self.root.after(1000, self._tick_countdown)

    def _reset_session_end_actions(self):
        was_focus_before_idle = (self.current_state == "Focus")
        self.timer_running = False; self.timer_paused = False
        self.current_state = "Idle"; self.current_break_type = ""
        self.remaining_seconds = 0; self.total_seconds_for_session = 0
        if self._timer_id: self.root.after_cancel(self._timer_id); self._timer_id = None
        if was_focus_before_idle and self.blocked_websites: self._unblock_domains(list(self.blocked_websites))
        self._update_ui_for_timer_state()

    def on_closing(self):
        self._save_settings()
        if self.timer_running:
            if self.current_state == "Focus" and self.blocked_websites: self._unblock_domains(list(self.blocked_websites))
            self.timer_running = False; self.timer_paused = False
            if self._timer_id: self.root.after_cancel(self._timer_id); self._timer_id = None
        print("Application closing.")
        if self.block_list_manager_window and self.block_list_manager_window.winfo_exists(): self.block_list_manager_window.destroy()
        self.root.destroy()

    # --- Unchanged Methods (BlockList, Hosts, Admin, etc.) ---
    def _open_block_list_manager(self):
        if self.block_list_manager_window is None or not self.block_list_manager_window.winfo_exists():
            self.block_list_manager_window = BlockListManagerWindow(self.root, self)
            self.block_list_manager_window.protocol("WM_DELETE_WINDOW", self._on_block_list_manager_close)
        else: self.block_list_manager_window.lift(); self.block_list_manager_window.focus_force()
    def _on_block_list_manager_close(self):
        if self.block_list_manager_window: self.block_list_manager_window.destroy(); self.block_list_manager_window = None
    def add_domain_to_blocklist_core(self, normalized_website):
        if normalized_website in self.blocked_websites: return False, f"{normalized_website} is already in the block list."
        self.blocked_websites.add(normalized_website); self._save_block_list_to_file()
        return True, f"{normalized_website} added to block list."
    def remove_domain_from_blocklist_core(self, selected_website):
        if selected_website not in self.blocked_websites: return False, f"{selected_website} not found in the block list."
        self._unblock_domains([selected_website]); self.blocked_websites.remove(selected_website); self._save_block_list_to_file()
        return True, f"{selected_website} has been unblocked and removed from the list."
    def _edit_focus_duration(self):
        new_duration = simpledialog.askinteger("Focus Duration", "Enter focus duration (minutes):", parent=self.root, minvalue=1, maxvalue=180, initialvalue=self.focus_duration_minutes)
        if new_duration is not None: self.focus_duration_minutes = new_duration; self._update_button_labels(); self._save_settings()
    def _edit_short_break_duration(self):
        new_duration = simpledialog.askinteger("Short Break Duration", "Enter short break duration (minutes):", parent=self.root, minvalue=1, maxvalue=60, initialvalue=self.short_break_duration_minutes)
        if new_duration is not None: self.short_break_duration_minutes = new_duration; self._update_button_labels(); self._save_settings()
    def _edit_long_break_duration(self):
        new_duration = simpledialog.askinteger("Long Break Duration", "Enter long break duration (minutes):", parent=self.root, minvalue=1, maxvalue=90, initialvalue=self.long_break_duration_minutes)
        if new_duration is not None: self.long_break_duration_minutes = new_duration; self._update_button_labels(); self._save_settings()
    def _load_block_list_from_file(self):
        self.blocked_websites.clear()
        if BLOCK_LIST_FILE_PATH.exists():
            try:
                with open(BLOCK_LIST_FILE_PATH, "r", encoding='utf-8') as f:
                    for line in f: self.blocked_websites.add(line.strip()) if line.strip() else None
                print(f"Loaded {len(self.blocked_websites)} websites from block list.")
            except Exception as e: messagebox.showerror("File Error", f"Could not load block list: {e}", parent=self.root); print(f"Error loading block list: {e}")
        else: print("Block list file not found. Starting empty.")
    def _save_block_list_to_file(self):
        try:
            BLOCK_LIST_FILE_PATH.parent.mkdir(parents=True, exist_ok=True)
            with open(BLOCK_LIST_FILE_PATH, "w", encoding='utf-8') as f:
                for website in sorted(list(self.blocked_websites)): f.write(website + "\n")
            print(f"Saved {len(self.blocked_websites)} websites to block list.")
        except Exception as e: messagebox.showerror("File Error", f"Could not save block list: {e}", parent=self.root); print(f"Error saving block list: {e}")
    def _is_admin(self):
        try: return os.geteuid() == 0
        except AttributeError: return False
    def _read_hosts_file(self):
        try:
            with open(HOSTS_FILE_PATH, "r", encoding='utf-8') as f: return f.readlines()
        except Exception as e: messagebox.showerror("Error", f"Could not read {HOSTS_FILE_PATH}: {e}", parent=self.root); return None
    def _write_hosts_file(self, lines):
        try:
            processed_lines = [line.strip() + "\n" for line in lines if line.strip()]
            if processed_lines and not processed_lines[-1].endswith("\n"): processed_lines[-1] += "\n"
            with open(HOSTS_FILE_PATH, "w", encoding='utf-8') as f: f.writelines(processed_lines)
            return True
        except Exception as e: messagebox.showerror("Error", f"Could not write to {HOSTS_FILE_PATH}: {e}", parent=self.root); return False
    def _get_domains_to_manage(self, domain):
        d = domain.lower(); return {d, f"www.{d}"} if not d.startswith("www.") else {d, d[4:]}
    def _block_domains(self, domains_to_block_list):
        if not domains_to_block_list: return
        original_lines = self._read_hosts_file();
        if original_lines is None: return
        variants_to_block = set().union(*(self._get_domains_to_manage(d) for d in domains_to_block_list))
        filtered_lines, modified = [], False
        for line in original_lines:
            parts = line.strip().split(None, 2)
            if not (len(parts) >= 2 and parts[0] == REDIRECT_IP and parts[1] in variants_to_block):
                filtered_lines.append(line)
            else: modified = True
        new_entries = [f"{REDIRECT_IP}\t{md}\t{POMODORO_COMMENT}\n" for md in sorted(list(variants_to_block))]
        if modified or (new_entries and not all(entry in original_lines for entry in new_entries)): # Check if actual change will happen
            if self._write_hosts_file(filtered_lines + new_entries): print(f"Hosts blocked: {domains_to_block_list}")
    def _unblock_domains(self, domains_to_unblock_list):
        if not domains_to_unblock_list: return
        original_lines = self._read_hosts_file()
        if original_lines is None: return
        variants_to_unblock = set().union(*(self._get_domains_to_manage(d) for d in domains_to_unblock_list))
        new_lines, modified = [], False
        for line in original_lines:
            parts = line.strip().split(None, 2)
            if len(parts) >= 2 and parts[0] == REDIRECT_IP and parts[1] in variants_to_unblock:
                modified = True; continue
            new_lines.append(line)
        if modified and self._write_hosts_file(new_lines): print(f"Hosts unblocked: {domains_to_unblock_list}")
    def _ensure_all_blocked_sites_are_unblocked_on_startup(self):
        if BLOCK_LIST_FILE_PATH.exists():
            sites = []
            try:
                with open(BLOCK_LIST_FILE_PATH, "r", encoding='utf-8') as f: sites = [l.strip() for l in f if l.strip()]
            except Exception as e: print(f"Cleanup read error: {e}"); return
            if sites: print(f"Startup unblock: {sites}"); self._unblock_domains(sites)

if __name__ == "__main__":
    main_root = tk.Tk()
    is_admin_check = False
    try: is_admin_check = (os.geteuid() == 0)
    except AttributeError: is_admin_check = False; print("Non-Unix system or euid check not available.")

    if not is_admin_check and os.name != 'nt':
        try: messagebox.showerror("Admin Privileges Required", "This application must be run with sudo/admin privileges.")
        except tk.TclError: print("Error: Admin Privileges Required.", file=sys.stderr)
        main_root.destroy(); sys.exit(1)
    
    app = PomodoroWebsiteBlocker(main_root)
    if hasattr(app, 'root') and app.root.winfo_exists():
        main_root.focus_force(); main_root.protocol("WM_DELETE_WINDOW", app.on_closing); main_root.mainloop()
    else:
        print("Application could not start properly.");
        if main_root.winfo_exists(): main_root.destroy()