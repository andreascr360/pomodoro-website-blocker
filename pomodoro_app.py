import tkinter as tk
from tkinter import ttk, messagebox, simpledialog
import os
import sys
from pathlib import Path
import json
import math
import threading
import datetime
try:
    from playsound import playsound
    PLAYSOUND_AVAILABLE = True
except ImportError:
    PLAYSOUND_AVAILABLE = False
    print("Warning: playsound library not found. Sound notifications will be disabled. Install with 'pip install playsound'")
try:
    import pyautogui
    PYAUTOGUI_AVAILABLE = True
except ImportError:
    PYAUTOGUI_AVAILABLE = False
    print("Warning: pyautogui library not found. Browser reload simulation will be disabled. Install with 'pip install pyautogui'")
try:
    from PIL import Image, ImageTk
    PILLOW_AVAILABLE = True
except ImportError:
    PILLOW_AVAILABLE = False
    print("Warning: Pillow library (PIL) not found. Custom PNG icon support will be limited or unavailable.")
    print("Install with 'pip install Pillow' for full custom icon support.")


# --- Constants ---
# Paths
SCRIPT_DIR = Path(__file__).parent.resolve() # For robust asset paths
HOSTS_FILE_PATH = "/etc/hosts"
BLOCK_LIST_FILE_PATH = Path.home() / ".website_blocker_list.txt"
CONFIG_FILE_PATH = Path.home() / ".pomodoro_blocker_settings.json"
SOUND_DIR = SCRIPT_DIR / "sound" # Centralized sound directory
SCRIPT_DIR = Path(__file__).parent.resolve() # For robust asset paths
APP_ICON_PATH = SCRIPT_DIR / "pom.png"  # Assuming your icon is named app_icon.png and is in the same directory

# --- ASCII Art Streak Feature ---
ASCII_ART_PIECES = [
    {"id": "heart", "name": "Simple Heart", "art_string": "<3", "description": "A token of love. (2-day streak)"},
    {"id": "smiley", "name": "Smiley Face", "art_string": "@_@", "description": "A classic smiley. (3-day streak)"},
    {"id": "star", "name": "Little Star", "art_string": "*-*", "description": "Shine bright! (3-day streak)"},
    {"id": "cat", "name": "Curious Cat", "art_string": "=^_^=", "description": "Meow! (5-day streak)"},
    # Add more art pieces here, perhaps with increasing difficulty (length)
]

def get_symbols_from_art(art_string):
    """Helper function to get individual symbols from an art string."""
    return list(art_string)

# Network
REDIRECT_IP = "127.0.0.1"
POMODORO_COMMENT = "# Added by PomodoroBlocker"

# Default Durations (minutes)
DEFAULT_FOCUS_DURATION_MINUTES = 25
DEFAULT_SHORT_BREAK_DURATION_MINUTES = 5
DEFAULT_LONG_BREAK_DURATION_MINUTES = 15
DEFAULT_EATING_BREAK_DURATION_MINUTES = 30
DEFAULT_POMODOROS_FOR_FULL_XP = 4
DEFAULT_SEQUENCE = [
    {'type': "Focus", 'name': "Focus"},
    {'type': "Short Break", 'name': "Short Break"},
    {'type': "Focus", 'name': "Focus"},
    {'type': "Short Break", 'name': "Short Break"},
    {'type': "Focus", 'name': "Focus"},
    {'type': "Short Break", 'name': "Short Break"},
    {'type': "Focus", 'name': "Focus"},
    {'type': "Long Break", 'name': "Long Break"},
    {'type': "Focus", 'name': "Focus"},
    {'type': "Eating Break", 'name': "Eating Break"},
    {'type': "Focus", 'name': "Focus"}
]

# Sound Files (using resolved paths)
SOUND_FOCUS_COMPLETE = SOUND_DIR / "focus_complete.mp3"
SOUND_BREAK_COMPLETE = SOUND_DIR / "focus_complete.mp3"

# --- UI Appearance Constants ---
# Circle Timer
CIRCLE_CANVAS_SIZE = 180
CIRCLE_PADDING = 10
CIRCLE_THICKNESS = 12
CIRCLE_BG_COLOR = "grey80"
CIRCLE_FG_COLOR_FOCUS = "tomato"
CIRCLE_FG_COLOR_BREAK = "medium sea green"
CIRCLE_TEXT_COLOR = "black"

# XP Bar
XP_BAR_HEIGHT = 22
XP_BAR_BG_COLOR = "grey60"
XP_BAR_FG_COLOR = "forest green"
XP_BAR_HIGHLIGHT_COLOR = "pale green"
XP_BAR_TEXT_COLOR = "black"
XP_BAR_CORNER_RADIUS = 7

# Icons
ICON_SIZE = 42
ICON_PADDING_STOP = 6
ICON_PADDING_PLAY_PAUSE = 7

STOP_ICON_COLOR_ACTIVE = "firebrick"
STOP_ICON_COLOR_DISABLED = "gray75"

PAUSE_ICON_COLOR_ACTIVE = "royal blue"
PLAY_ICON_COLOR_ACTIVE = "lime green"
PAUSE_PLAY_ICON_COLOR_DISABLED = "gray75"

# +++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++
# BlockListManagerWindow Class
# +++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++
class BlockListManagerWindow(tk.Toplevel):
    def __init__(self, master, app_controller):
        super().__init__(master)
        self.app_controller = app_controller
        self.title("Manage Blocked Websites")
        self.geometry("450x400")
        self.transient(master)
        self.grab_set()

        ttk.Label(self, text="Website (e.g., example.com):").grid(row=0, column=0, padx=10, pady=(10,5), sticky="w") # Added top padding
        self.website_entry_manager = ttk.Entry(self, width=30)
        self.website_entry_manager.grid(row=0, column=1, padx=10, pady=(10,5), sticky="ew")

        self.add_button_manager = ttk.Button(self, text="Add to Block List", command=self._ui_add_website)
        self.add_button_manager.grid(row=0, column=2, padx=5, pady=(10,5))

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
        else:
            messagebox.showerror("Error", "Could not unblock selected website.", parent=self)

class AchievementsWindow(tk.Toplevel):
    def __init__(self, master, app_controller):
        super().__init__(master)
        self.app_controller = app_controller
        self.title("Unlocked Art Achievements")
        self.geometry("400x500")
        self.transient(master)
        self.grab_set()

        main_frame = ttk.Frame(self, padding="10")
        main_frame.pack(expand=True, fill=tk.BOTH)

        # Using a Text widget for better display of multi-line ASCII art
        self.text_area = tk.Text(main_frame, wrap=tk.WORD, height=20, width=50, relief=tk.SUNKEN, borderwidth=1)
        self.text_area.pack(pady=5, fill=tk.BOTH, expand=True)

        scrollbar = ttk.Scrollbar(main_frame, command=self.text_area.yview)
        scrollbar.pack(side=tk.RIGHT, fill=tk.Y, before=self.text_area) # position before text_area in packing order for right side
        self.text_area.config(yscrollcommand=scrollbar.set)


        self._populate_achievements()

        close_button = ttk.Button(main_frame, text="Close", command=self.destroy)
        close_button.pack(pady=10)

        self.protocol("WM_DELETE_WINDOW", self.destroy)

    def _populate_achievements(self):
        self.text_area.config(state=tk.NORMAL) # Enable editing to insert
        self.text_area.delete('1.0', tk.END) # Clear previous content

        if not self.app_controller.unlocked_achievements:
            self.text_area.insert(tk.END, "No art pieces unlocked yet. Keep up the streak!\n")
        else:
            for art_id in self.app_controller.unlocked_achievements:
                art_def = next((art for art in self.app_controller.ascii_art_definitions if art["id"] == art_id), None)
                if art_def:
                    self.text_area.insert(tk.END, f"--- {art_def['name']} ---\n", ("title",))
                    self.text_area.insert(tk.END, f"{art_def['art_string']}\n\n", ("art",))
                    self.text_area.insert(tk.END, f"({art_def['description']})\n")
                    self.text_area.insert(tk.END, "------------------------------------\n\n")

        self.text_area.tag_configure("title", font=("Helvetica", 14, "bold"), justify=tk.CENTER)
        self.text_area.tag_configure("art", font=("Courier", 12, "bold"), justify=tk.CENTER, spacing1=5, spacing3=5) # Add spacing around art
        self.text_area.config(state=tk.DISABLED) # Make read-only

# +++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++
# RepeatingNotificationWindow Class
# +++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++
class RepeatingNotificationWindow(tk.Toplevel):

    def _on_ok_event_handler(self, event=None):
        """Handles the Enter key press event by calling the _on_ok method."""
        self._on_ok()

    def __init__(self, master, title, message, sound_file_to_repeat, on_ok_callback, app_controller):
        super().__init__(master)
        self.master_window = master
        self.app_controller = app_controller # Instance of PomodoroWebsiteBlocker
        self.title(title)
        
        self.transient(master)
        self.focus_set() 
        self.lift() 

        self.sound_file_to_repeat = sound_file_to_repeat
        self.on_ok_callback = on_ok_callback
        
        self._is_destroyed = False 
        self._repetition_active = True 
        self._after_id_pause = None  

        self.geometry("350x150") 
        main_frame = ttk.Frame(self, padding="20")
        main_frame.pack(expand=True, fill=tk.BOTH)

        message_label = ttk.Label(main_frame, text=message, wraplength=300, justify=tk.CENTER)
        message_label.pack(pady=(0, 20), expand=True)

        ok_button = ttk.Button(main_frame, text="OK", command=self._on_ok, style="Accent.TButton")
        ok_button.pack(pady=10)

        self.protocol("WM_DELETE_WINDOW", self._on_close)
        
        # Add this line to bind the Enter key:
        self.bind("<Return>", self._on_ok_event_handler)
        
        self.update_idletasks() 
        master_x = master.winfo_x()
        master_y = master.winfo_y()
        master_width = master.winfo_width()
        master_height = master.winfo_height()
        win_width = self.winfo_width()
        win_height = self.winfo_height()
        x = master_x + (master_width // 2) - (win_width // 2)
        y = master_y + (master_height // 2) - (win_height // 2)
        self.geometry(f'+{x}+{y}')
        
        self._play_sound_and_initiate_next_cycle()

    def _play_sound_and_initiate_next_cycle(self): # <--- THIS METHOD WAS MISSING/INCORRECT
        if not self._repetition_active or self._is_destroyed:
            return
        
        self.app_controller._play_sound_with_callback_on_finish(
            self.sound_file_to_repeat,
            self._handle_sound_playback_finished # Pass the method itself as a callback
        )

    def _handle_sound_playback_finished(self): # This method IS in your file
        """Called (in main thread) after a sound playback attempt finishes."""
        if not self._repetition_active or self._is_destroyed:
            return

        if self._after_id_pause: 
            self.after_cancel(self._after_id_pause)
            
        # Schedule the *next call to start playing the sound*, after the pause
        self._after_id_pause = self.after(5000, self._play_sound_and_initiate_next_cycle)

    def _stop_sound_repetition_cycle(self): # This method IS in your file
        self._repetition_active = False 
        if self._after_id_pause:
            self.after_cancel(self._after_id_pause)
            self._after_id_pause = None

    def _on_ok(self): # This method IS in your file
        self._stop_sound_repetition_cycle()
        if self.on_ok_callback:
            self.on_ok_callback()
        self.destroy() 

    def _on_close(self): # This method IS in your file
        self._on_ok() 

    def destroy(self): # This method IS in your file
        self._is_destroyed = True 
        self._stop_sound_repetition_cycle()
        super().destroy()
    
    # REMOVE the old _start_repeating_sound and _stop_repeating_sound methods
    # from your current RepeatingNotificationWindow class (lines 179-190 in your file)
    # as they implement the older, overlapping logic.

# +++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++
# SequenceEditorWindow Class
# +++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++
class SequenceEditorWindow(tk.Toplevel):
    def __init__(self, master, app_controller):
        super().__init__(master)
        self.app_controller = app_controller
        self.title("Edit Pomodoro Sequence & Durations")
        # Potentially increase height slightly more if needed, e.g., 550x680
        self.geometry("550x680") # Adjusted height for the new label
        self.transient(master)
        self.grab_set()

        self.editable_sequence = list(self.app_controller.custom_sequence)
        self.session_types = ["Focus", "Short Break", "Long Break", "Eating Break"]
        self.base_time = datetime.datetime.now()

        # --- UI Elements ---
        instruction_label = ttk.Label(self, text="Define sequence and session durations.")
        instruction_label.grid(row=0, column=0, columnspan=3, padx=10, pady=10, sticky="w")
        
        listbox_frame = ttk.LabelFrame(self, text="Current Sequence")
        listbox_frame.grid(row=1, column=0, columnspan=3, padx=10, pady=5, sticky="nsew")
        # ... (rest of listbox_frame setup as before, e.g., self.sequence_listbox) ...
        self.sequence_listbox = tk.Listbox(listbox_frame, selectmode=tk.SINGLE, height=8)
        self.sequence_listbox.grid(row=0, column=0, sticky="nsew")
        listbox_scrollbar = ttk.Scrollbar(listbox_frame, orient=tk.VERTICAL, command=self.sequence_listbox.yview)
        self.sequence_listbox.configure(yscrollcommand=listbox_scrollbar.set)
        listbox_scrollbar.grid(row=0, column=1, sticky="ns")
        self.sequence_listbox.bind("<Return>", self._rename_selected_session_dialog)

        # --- NEW: Total Sequence Time Label ---
        self.total_sequence_time_label = ttk.Label(self, text="Total Time: Calculating...", font=("Helvetica", 10, "italic"))
        self.total_sequence_time_label.grid(row=2, column=0, columnspan=3, padx=10, pady=(5, 0), sticky="w")
        # --- End NEW Total Sequence Time Label ---

        add_buttons_frame = ttk.LabelFrame(self, text="Add Session Type to Sequence")
        add_buttons_frame.grid(row=3, column=0, columnspan=3, padx=10, pady=5, sticky="ew") # Changed row to 3
        # ... (rest of add_buttons_frame setup as before) ...
        button_configs = [
            {"text": f"Add {self.session_types[0]}", "command": lambda: self._add_session_type(self.session_types[0]), "row": 0, "col": 0},
            {"text": f"Add {self.session_types[1]}", "command": lambda: self._add_session_type(self.session_types[1]), "row": 0, "col": 1},
            {"text": f"Add {self.session_types[2]}", "command": lambda: self._add_session_type(self.session_types[2]), "row": 1, "col": 0},
            {"text": f"Add {self.session_types[3]}", "command": lambda: self._add_session_type(self.session_types[3]), "row": 1, "col": 1},
        ]
        for i in range(2): 
            add_buttons_frame.grid_columnconfigure(i, weight=1)
        for config in button_configs:
            btn = ttk.Button(add_buttons_frame, text=config["text"], command=config["command"])
            btn.grid(row=config["row"], column=config["col"], padx=5, pady=5, sticky="ew")


        modify_buttons_frame = ttk.Frame(self)
        modify_buttons_frame.grid(row=4, column=0, columnspan=3, padx=10, pady=5, sticky="ew") # Changed row to 4
        # ... (rest of modify_buttons_frame setup as before) ...
        self.remove_button = ttk.Button(modify_buttons_frame, text="Remove Selected", command=self._remove_selected_session)
        self.remove_button.pack(side=tk.LEFT, padx=5, pady=5, expand=True, fill=tk.X)
        self.move_up_button = ttk.Button(modify_buttons_frame, text="Move Up", command=self._move_selected_session_up)
        self.move_up_button.pack(side=tk.LEFT, padx=5, pady=5, expand=True, fill=tk.X)
        self.move_down_button = ttk.Button(modify_buttons_frame, text="Move Down", command=self._move_selected_session_down)
        self.move_down_button.pack(side=tk.LEFT, padx=5, pady=5, expand=True, fill=tk.X)


        durations_frame = ttk.LabelFrame(self, text="Edit Session Durations (minutes)")
        durations_frame.grid(row=5, column=0, columnspan=3, padx=10, pady=10, sticky="ew") # Changed row to 5
        # ... (rest of durations_frame setup as before, including labels and buttons) ...
        durations_frame.grid_columnconfigure(0, weight=1) 
        durations_frame.grid_columnconfigure(1, weight=0) 
        self.focus_duration_label = ttk.Label(durations_frame, text="")
        self.focus_duration_label.grid(row=0, column=0, padx=5, pady=2, sticky="w")
        ttk.Button(durations_frame, text="Edit Focus", command=self._edit_focus_duration_in_editor).grid(row=0, column=1, padx=5, pady=2, sticky="e")
        self.short_break_duration_label = ttk.Label(durations_frame, text="")
        self.short_break_duration_label.grid(row=1, column=0, padx=5, pady=2, sticky="w")
        ttk.Button(durations_frame, text="Edit Short Break", command=self._edit_short_break_duration_in_editor).grid(row=1, column=1, padx=5, pady=2, sticky="e")
        self.long_break_duration_label = ttk.Label(durations_frame, text="")
        self.long_break_duration_label.grid(row=2, column=0, padx=5, pady=2, sticky="w")
        ttk.Button(durations_frame, text="Edit Long Break", command=self._edit_long_break_duration_in_editor).grid(row=2, column=1, padx=5, pady=2, sticky="e")
        self.eating_break_duration_label = ttk.Label(durations_frame, text="")
        self.eating_break_duration_label.grid(row=3, column=0, padx=5, pady=2, sticky="w")
        ttk.Button(durations_frame, text="Edit Eating Break", command=self._edit_eating_break_duration_in_editor).grid(row=3, column=1, padx=5, pady=2, sticky="e")

        action_buttons_frame = ttk.Frame(self)
        action_buttons_frame.grid(row=6, column=0, columnspan=3, padx=10, pady=(10,10), sticky="sew") # Changed row to 6
        # ... (rest of action_buttons_frame setup as before) ...
        action_buttons_frame.grid_columnconfigure(0, weight=1)
        action_buttons_frame.grid_columnconfigure(1, weight=1)
        self.save_button = ttk.Button(action_buttons_frame, text="Save Sequence", command=self._save_sequence, style="Accent.TButton")
        self.save_button.grid(row=0, column=1, padx=5, pady=5, sticky="ew")
        self.cancel_button = ttk.Button(action_buttons_frame, text="Cancel", command=self.destroy)
        self.cancel_button.grid(row=0, column=0, padx=5, pady=5, sticky="ew")
        
        self.grid_rowconfigure(1, weight=1) # Listbox frame
        # self.grid_rowconfigure(2, weight=0) # Total time label (no vertical expansion)
        # self.grid_rowconfigure(5, weight=0) # Durations frame (no vertical expansion by default)
        self.grid_columnconfigure(0, weight=1)

        self._refresh_duration_displays()
        self._refresh_listbox() # This will now also call the total time calculation
        self.protocol("WM_DELETE_WINDOW", self.destroy)

    
    def _format_total_time(self, total_minutes):
        if total_minutes < 0:
            total_minutes = 0

        hours = total_minutes // 60
        minutes = total_minutes % 60

        if hours > 0:
            return f"Total Sequence Time: {hours} hour{'s' if hours != 1 else ''} {minutes} minute{'s' if minutes != 1 else ''}"
        else:
            return f"Total Sequence Time: {minutes} minute{'s' if minutes != 1 else ''}"

    def _calculate_and_display_total_sequence_time(self):
        total_minutes = 0
        if self.editable_sequence:
            for item in self.editable_sequence:
                try:
                    duration_minutes = self.app_controller._get_duration_for_type(item['type'])
                    total_minutes += duration_minutes
                except Exception as e:
                    print(f"Error calculating total time for item type {item.get('type', 'N/A')}: {e}")

        formatted_time_str = self._format_total_time(total_minutes)
        if hasattr(self, 'total_sequence_time_label'): # Ensure label exists
            self.total_sequence_time_label.config(text=formatted_time_str)

    def _rename_selected_session_dialog(self, event=None): # event is passed by bind
        selected_indices = self.sequence_listbox.curselection()
        if not selected_indices:
            # This shouldn't happen if bound to <Return> on a selected item, but good check
            return 

        index = selected_indices[0]
        current_item = self.editable_sequence[index]
        current_name = current_item.get('name', current_item.get('type', ''))

        new_name = simpledialog.askstring("Rename Session", 
                                        f"Enter new name for '{current_name}':",
                                        initialvalue=current_name,
                                        parent=self)

        if new_name and new_name.strip(): # If user provided a new name (not None or empty)
            self.editable_sequence[index]['name'] = new_name.strip()
            self._refresh_listbox()
            # Re-select the item
            self.sequence_listbox.selection_set(index)
            self.sequence_listbox.activate(index)
            self.sequence_listbox.see(index)
        elif new_name == "": # User entered an empty string
            messagebox.showwarning("Invalid Name", "Session name cannot be empty.", parent=self)


    def _refresh_duration_displays(self):
        self.focus_duration_label.config(text=f"Focus Duration: {self.app_controller.focus_duration_minutes} min")
        self.short_break_duration_label.config(text=f"Short Break Duration: {self.app_controller.short_break_duration_minutes} min")
        self.long_break_duration_label.config(text=f"Long Break Duration: {self.app_controller.long_break_duration_minutes} min")
        self.eating_break_duration_label.config(text=f"Eating Break Duration: {self.app_controller.eating_break_duration_minutes} min")

    def _edit_focus_duration_in_editor(self):
        new_duration = simpledialog.askinteger(
            "Focus Duration", "Enter focus duration (minutes):",
            parent=self, minvalue=1, maxvalue=180,
            initialvalue=self.app_controller.focus_duration_minutes
        )
        if new_duration is not None:
            self.app_controller.focus_duration_minutes = new_duration
            self.app_controller._save_settings()
            self._refresh_duration_displays()
            self._refresh_listbox() # Durations affect projected times

    def _edit_short_break_duration_in_editor(self):
        new_duration = simpledialog.askinteger(
            "Short Break Duration", "Enter short break duration (minutes):",
            parent=self, minvalue=1, maxvalue=60,
            initialvalue=self.app_controller.short_break_duration_minutes
        )
        if new_duration is not None:
            self.app_controller.short_break_duration_minutes = new_duration
            self.app_controller._save_settings()
            self._refresh_duration_displays()
            self._refresh_listbox()

    def _edit_long_break_duration_in_editor(self):
        new_duration = simpledialog.askinteger(
            "Long Break Duration", "Enter long break duration (minutes):",
            parent=self, minvalue=1, maxvalue=90,
            initialvalue=self.app_controller.long_break_duration_minutes
        )
        if new_duration is not None:
            self.app_controller.long_break_duration_minutes = new_duration
            self.app_controller._save_settings()
            self._refresh_duration_displays()
            self._refresh_listbox()

    def _edit_eating_break_duration_in_editor(self):
        new_duration = simpledialog.askinteger(
            "Eating Break Duration", "Enter eating break duration (minutes, 5-120):",
            parent=self, minvalue=5, maxvalue=120,
            initialvalue=self.app_controller.eating_break_duration_minutes
        )
        if new_duration is not None:
            self.app_controller.eating_break_duration_minutes = new_duration
            self.app_controller._save_settings()
            self._refresh_duration_displays()
            self._refresh_listbox()


    def _refresh_listbox(self):
        self.sequence_listbox.delete(0, tk.END)

        if not self.editable_sequence:
            self.sequence_listbox.insert(tk.END, "Sequence is empty. Add sessions to begin.")
            self._calculate_and_display_total_sequence_time() # Update total time even for empty sequence
            return

        current_projected_time = self.base_time # Reset base time for projection
        for i, item in enumerate(self.editable_sequence):
            display_name = item.get('name', item.get('type', 'Unknown Session'))
            duration_minutes = 0
            try:
                duration_minutes = self.app_controller._get_duration_for_type(item['type'])
            except Exception as e:
                print(f"Error getting duration for type {item.get('type', 'N/A')} in _refresh_listbox: {e}")

            current_projected_time += datetime.timedelta(minutes=duration_minutes)
            time_str = current_projected_time.strftime("%H:%M")
            self.sequence_listbox.insert(tk.END, f"{i+1}. {display_name} — {time_str}")

        self._calculate_and_display_total_sequence_time()


    def _add_session_type(self, session_type_str):
        # New items get their type as their initial name
        new_item = {'type': session_type_str, 'name': session_type_str}
        self.editable_sequence.append(new_item)
        self._refresh_listbox()
        self.sequence_listbox.see(tk.END) 

    def _remove_selected_session(self):
        selected_indices = self.sequence_listbox.curselection()
        if not selected_indices:
            messagebox.showwarning("Selection Error", "Please select a session to remove.", parent=self)
            return
        
        index_to_remove = selected_indices[0]
        del self.editable_sequence[index_to_remove]
        self._refresh_listbox()

        # Optionally re-select an item
        if self.editable_sequence:
            new_selection_index = min(index_to_remove, len(self.editable_sequence) - 1)
            if new_selection_index >=0:
                self.sequence_listbox.selection_set(new_selection_index)
                self.sequence_listbox.activate(new_selection_index)


    def _move_selected_session_up(self):
        selected_indices = self.sequence_listbox.curselection()
        if not selected_indices:
            messagebox.showwarning("Selection Error", "Please select a session to move.", parent=self)
            return
        
        index = selected_indices[0]
        if index == 0: # Already at the top
            return
        
        # Swap with the item above
        item_to_move = self.editable_sequence.pop(index)
        self.editable_sequence.insert(index - 1, item_to_move)
        
        self._refresh_listbox()
        self.sequence_listbox.selection_set(index - 1) # Keep the moved item selected
        self.sequence_listbox.activate(index - 1)
        self.sequence_listbox.see(index - 1)


    def _move_selected_session_down(self):
        selected_indices = self.sequence_listbox.curselection()
        if not selected_indices:
            messagebox.showwarning("Selection Error", "Please select a session to move.", parent=self)
            return
        
        index = selected_indices[0]
        if index == len(self.editable_sequence) - 1: # Already at the bottom
            return
            
        # Swap with the item below
        item_to_move = self.editable_sequence.pop(index)
        self.editable_sequence.insert(index + 1, item_to_move)

        self._refresh_listbox()
        self.sequence_listbox.selection_set(index + 1) # Keep the moved item selected
        self.sequence_listbox.activate(index + 1)
        self.sequence_listbox.see(index + 1)


    def _save_sequence(self):
        if not self.editable_sequence:
            if not messagebox.askyesno("Empty Sequence", 
                                    "The sequence is empty. Saving will result in no defined sequence. Continue?",
                                    parent=self):
                return

        self.app_controller.custom_sequence = list(self.editable_sequence) # Update the main app's sequence

        # Recalculate XP goal based on the new sequence
        self.app_controller._recalculate_xp_goal_from_sequence() 

        self.app_controller._save_settings() # Persist sequence and other settings to file

        if not self.app_controller.timer_running:
            self.app_controller.current_sequence_index = -1

        messagebox.showinfo("Sequence Saved", "The new Pomodoro sequence and settings have been saved.", parent=self)
        self.destroy()

# +++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++
# Main Application Class: PomodoroWebsiteBlocker
# +++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++
class PomodoroWebsiteBlocker:
    def __init__(self, root_window):
        self.root = root_window
        self.root.title("Pomodoro XP Blocker")
        estimated_height = 10 + 30 + 20 + ICON_SIZE + 20 + CIRCLE_CANVAS_SIZE + 20 + 30 + XP_BAR_HEIGHT + 30 + 20
        self.root.geometry(f"350x{estimated_height}")

        self.custom_sequence = [] 
        self.current_sequence_index = -1


        if not self._is_admin():
            messagebox.showerror("Admin Privileges Required", "This application must be run with sudo privileges.")
            self.root.destroy(); return

        self._initialize_durations()

        # Streak Feature Attributes
        self.ascii_art_definitions = ASCII_ART_PIECES
        self.unlocked_achievements = []  # List of art piece IDs
        self.current_art_piece_id = None
        self.current_art_progress = 0    # Symbols revealed for the current piece
        self.last_xp_full_date_str = None # Store as YYYY-MM-DD string

        self._load_settings() # This will now also load custom_sequence

        self._timer_id = None
        self.block_list_manager_window = None
        self.sequence_editor_window = None
        self.notification_window = None
        self.reload_attempted_early = False

        self.blocked_websites = set()
        self.pomodoro_count = 0
        self.timer_running = False
        self.timer_paused = False
        self.current_state = "Idle"
        self.current_break_type = ""
        self.remaining_seconds = 0
        self.total_seconds_for_session = 0
        self._timer_id = None
        self.block_list_manager_window = None

        self._create_menubar()
        self._setup_ui()

        self._update_current_art_piece() # Determine first/next art piece
        self._update_streak_display()

        self._load_block_list_from_file()
        self._ensure_all_blocked_sites_are_unblocked_on_startup()
        self._update_timer_display()
        self._draw_xp_bar()
        self._update_ui_for_timer_state() # Now sequence attributes are guaranteed to exist

        # --- MODIFICATION: Removed redundant block of admin check and settings load ---
        # self.custom_sequence = [] # Will be loaded from settings # MOVED EARLIER
        # self.current_sequence_index = -1  # -1 indicates sequence not active or finished # MOVED EARLIER

        # if not self._is_admin(): # THIS ENTIRE BLOCK IS REDUNDANT AND REMOVED
        #     messagebox.showerror("Admin Privileges Required", "This application must be run with sudo privileges.")
        #     self.root.destroy(); return
        #
        # self._initialize_durations()
        # self._load_settings()
        # --- END MODIFICATION ---

        self.root.bind("<Configure>", self._on_window_resize)

    # --- MODIFICATION: Removed first (incomplete/buggy) definitions of _load_settings, _save_settings, _reset_to_default_settings_and_save ---
    # Old _load_settings was here (approx lines 194-233) - REMOVED
    # Old _save_settings was here (approx lines 235-247) - REMOVED
    # Old _reset_to_default_settings_and_save was here (approx lines 249-257) - REMOVED
    # --- END MODIFICATION ---

    def _get_duration_for_type(self, session_type_str):
        if session_type_str == "Focus":
            return self.focus_duration_minutes
        elif session_type_str == "Short Break":
            return self.short_break_duration_minutes
        elif session_type_str == "Long Break":
            return self.long_break_duration_minutes
        elif session_type_str == "Eating Break":
            return self.eating_break_duration_minutes
        else:
            print(f"Warning: Unknown session type '{session_type_str}' in sequence. Defaulting to focus duration.")
            return self.focus_duration_minutes
        
    def _play_sound_with_callback_on_finish(self, sound_file_path_obj, on_finish_callback=None):
        """
        Plays a sound in a separate thread.
        Executes on_finish_callback in the main Tkinter thread when sound finishes or if an error occurs.
        """
        if not PLAYSOUND_AVAILABLE:
            if on_finish_callback:
                # If sounds are disabled, trigger callback immediately to allow logic to proceed
                self.root.after(0, on_finish_callback)
            return

        def play_and_callback():
            sound_file_str = "" # Initialize for finally block
            try:
                sound_file_str = str(sound_file_path_obj) # playsound needs string
                if sound_file_path_obj.exists():
                    print(f"Playing sound (with callback): {sound_file_str}")
                    playsound(sound_file_str) # This is blocking within this thread
                    print(f"Finished playing sound: {sound_file_str}")
                else:
                    print(f"Sound file not found (with callback): {sound_file_str}")
            except Exception as e:
                print(f"Error playing sound '{sound_file_str}' (with callback): {e}")
            finally:
                # Ensure callback happens even if sound fails, so the repeat logic isn't stuck
                if on_finish_callback and hasattr(self.root, 'winfo_exists') and self.root.winfo_exists():
                    # Schedule the callback to run in the main Tkinter thread
                    self.root.after(0, on_finish_callback)
                elif on_finish_callback: # Fallback if root doesn't exist (should not happen in this context)
                    print("Root window for callback no longer exists.")


        sound_thread = threading.Thread(target=play_and_callback, daemon=True)
        sound_thread.start()

    def _update_current_art_piece(self):
        """Determines and sets the current art piece the user is working on."""
        initial_art_piece_id = self.current_art_piece_id
        new_current_art_piece_found = False

        for art_def in self.ascii_art_definitions:
            if art_def["id"] not in self.unlocked_achievements:
                self.current_art_piece_id = art_def["id"]
                if initial_art_piece_id != self.current_art_piece_id : # Changed to a new piece
                    self.current_art_progress = 0 # Reset progress for this new piece
                new_current_art_piece_found = True
                break

        if not new_current_art_piece_found: # All pieces might be unlocked
            if self.unlocked_achievements and len(self.unlocked_achievements) == len(self.ascii_art_definitions):
                print("All art pieces unlocked!")
                self.current_art_piece_id = "ALL_UNLOCKED" # Special ID
                self.current_art_progress = 0
            elif not self.ascii_art_definitions:
                print("No art pieces defined.")
                self.current_art_piece_id = None
            # If some are unlocked but somehow no new one found (shouldn't happen with good definitions)
            # keep current_art_piece_id as is, or nullify if it was for an already unlocked piece.
            # The logic above should handle finding the *first* non-unlocked.

        # If after trying to find a new piece, current_art_piece_id points to an unlocked one,
        # (e.g. due to manual settings edit or loading old data)
        # it means we should nullify it or re-run to find the actual next one.
        # The loop above should find the *first available one*.
        # If self.current_art_piece_id is still an ID that's in unlocked_achievements, then all are done.
        if self.current_art_piece_id and self.current_art_piece_id in self.unlocked_achievements:
            self.current_art_piece_id = "ALL_UNLOCKED" # Mark as all done
            self.current_art_progress = 0


        if initial_art_piece_id != self.current_art_piece_id or not hasattr(self, 'streak_display_label'): # Update display if piece changed or label not yet made
            if hasattr(self, '_update_streak_display'): # Check if UI method exists
                self._update_streak_display()

    def _simulate_browser_reload(self):
        if not PYAUTOGUI_AVAILABLE:
            print("pyautogui library is not available. Skipping browser reload simulation.")
            # Optionally, inform the user via a non-blocking way if this is critical
            # messagebox.showinfo("Info", "pyautogui library not found. Browser reload cannot be simulated.", parent=self.root)
            return

        if not self.root.winfo_exists(): # Ensure main window is still around
            return

        print("Attempting to simulate browser reload (Cmd/Ctrl+R). Ensure your browser is the active window.")
        
        # A very short delay can sometimes help, but it's not a reliable fix for focus issues.
        # import time # Add 'import time' at the top of your file if you use this
        # time.sleep(0.2) # Small delay

        try:
            if sys.platform == "darwin":  # macOS
                pyautogui.hotkey('command', 'r')
                print("Simulated Cmd+R")
            elif sys.platform == "win32" or sys.platform.startswith("linux"):  # Windows or Linux
                pyautogui.hotkey('ctrl', 'r')
                print("Simulated Ctrl+R")
            else:
                print(f"Browser reload hotkey not configured for platform: {sys.platform}")
                return # Don't show a message if platform is not common for this action
            
            # It's hard to know if it actually worked, so no success message here.
            # The print statement above is for logging.

        except Exception as e:
            # pyautogui can raise various errors, e.g., if it can't connect to the display server (common on headless Linux)
            # or due to permissions issues.
            print(f"Error attempting to simulate reload hotkey: {e}")
            error_message = f"Could not simulate browser reload: {e}\n\n"
            error_message += "Please ensure your browser window was active."
            if sys.platform == "darwin":
                error_message += ("\nOn macOS, this application (Terminal or IDE) might need "
                                  "Accessibility permissions in System Settings > Privacy & Security.")
            messagebox.showwarning("Reload Simulation Error", error_message, parent=self.root)

    def _proceed_to_next_in_sequence(self):
        if self.current_sequence_index == -1 and not self.custom_sequence:
             messagebox.showinfo("Sequence Info", "No custom sequence defined. Please configure one or use manual mode.", parent=self.root)
             self._reset_session_end_actions() 
             return

        self.current_sequence_index += 1 

        if self.current_sequence_index < len(self.custom_sequence):
            next_session_item = self.custom_sequence[self.current_sequence_index]
            next_session_type_str = next_session_item['type']
            next_session_display_name = next_session_item['name']
            duration_minutes = self._get_duration_for_type(next_session_type_str)

            # ... (session_name_for_log, next_up_message, print statements - these are fine) ...
            session_name_for_log = f"{next_session_display_name} (Type: {next_session_type_str}, {duration_minutes} min)" 
            next_up_message = f"Next in sequence: {session_name_for_log}"
            if self.current_sequence_index + 1 < len(self.custom_sequence):
                next_next_session_item = self.custom_sequence[self.current_sequence_index + 1]
                next_up_message += f"\nFollowing that: {next_next_session_item['name']}"
            else:
                next_up_message += "\nThis is the last session in the sequence."
            print(next_up_message)
            
            self.timer_running = False # Ensure these are not commented out
            self.current_state = "Idle"  # Ensure these are not commented out
            success = False
            
            if next_session_type_str == "Focus":
                success = self._start_session_common("Focus", "", duration_minutes)
                #if success: # If focus session started successfully (sites are now blocked)
                #    self.root.after(100, self._simulate_browser_reload) # Call after a very brief delay
            elif next_session_type_str == "Short Break":
                success = self._start_session_common("Break", "Short", duration_minutes)
            elif next_session_type_str == "Long Break":
                success = self._start_session_common("Break", "Long", duration_minutes)
            elif next_session_type_str == "Eating Break":
                success = self._start_session_common("Break", "Eating", duration_minutes)
            else:
                print(f"Error: Encountered unknown session type '{next_session_type_str}' during sequence progression.")
                self._reset_session_end_actions()
                self.current_sequence_index = -1
                return

            if not success:
                print("Could not start the next session in the sequence. Sequence interrupted.")
                self._reset_session_end_actions()
                self.current_sequence_index = -1
        else:
            # ... (sequence finished logic - this is fine) ...
            self.root.lift()
            self.root.focus_force()
            messagebox.showinfo("Sequence Complete", "The defined Pomodoro sequence has finished!", parent=self.root)
            self._reset_session_end_actions()
            self.current_sequence_index = -1

    def _initialize_durations(self):
        """Sets default durations for all timers."""
        self.focus_duration_minutes = DEFAULT_FOCUS_DURATION_MINUTES
        self.short_break_duration_minutes = DEFAULT_SHORT_BREAK_DURATION_MINUTES
        self.long_break_duration_minutes = DEFAULT_LONG_BREAK_DURATION_MINUTES
        self.eating_break_duration_minutes = DEFAULT_EATING_BREAK_DURATION_MINUTES
        self.pomodoros_for_full_xp = DEFAULT_POMODOROS_FOR_FULL_XP

    def _setup_ui(self):
        """Creates and grids all UI elements for the main window."""
        ttk.Separator(self.root, orient='horizontal').grid(row=0, column=0, columnspan=4, sticky='ew', pady=5)
        self.timer_label = ttk.Label(self.root, text="Status: Idle", font=("Helvetica", 14, "italic"))
        self.timer_label.grid(row=1, column=0, columnspan=4, padx=10, pady=(10,0))
        timer_controls_frame = ttk.Frame(self.root)
        timer_controls_frame.grid(row=2, column=0, columnspan=4, sticky="ew", pady=(5,15))
        timer_controls_frame.grid_columnconfigure(0, weight=1)
        timer_controls_frame.grid_columnconfigure(1, weight=2)
        timer_controls_frame.grid_columnconfigure(2, weight=1)
        self.stop_icon_canvas = tk.Canvas(timer_controls_frame, width=ICON_SIZE, height=ICON_SIZE,
                                          bg=self.root.cget('bg'), highlightthickness=0, cursor="hand2")
        self.stop_icon_canvas.grid(row=0, column=0, padx=(20, 5), pady=5, sticky="w")
        self.stop_icon_canvas.bind("<Button-1>", self._on_stop_icon_click)
        self.timer_canvas = tk.Canvas(timer_controls_frame, width=CIRCLE_CANVAS_SIZE, height=CIRCLE_CANVAS_SIZE,
                                      bg=self.root.cget('bg'), highlightthickness=0)
        self.timer_canvas.grid(row=0, column=1, pady=5, sticky="n")
        self._setup_timer_canvas_elements()
        self.pause_play_icon_canvas = tk.Canvas(timer_controls_frame, width=ICON_SIZE, height=ICON_SIZE,
                                                bg=self.root.cget('bg'), highlightthickness=0, cursor="hand2")
        self.pause_play_icon_canvas.grid(row=0, column=2, padx=(5, 20), pady=5, sticky="e")
        self.pause_play_icon_canvas.bind("<Button-1>", self._on_pause_play_icon_click)

        self.xp_bar_canvas = tk.Canvas(self.root, height=XP_BAR_HEIGHT + 20,
                                       bg=self.root.cget('bg'), highlightthickness=0)
        self.xp_bar_canvas.grid(row=3, column=0, columnspan=4, padx=10, pady=(10,5), sticky="ew")
        counter_frame = ttk.Frame(self.root)
        counter_frame.grid(row=4, column=0, columnspan=4, sticky="ew", padx=10, pady=(0,5)) # Reduced bottom pady
        counter_frame.grid_columnconfigure(0, weight=1)
        self.pomodoros_completed_label = ttk.Label(counter_frame, text="")
        self.pomodoros_completed_label.grid(row=0, column=0, sticky="w")

        # New Streak Display Label
        self.streak_display_label = ttk.Label(self.root, text="Streak: Initializing...", font=("Helvetica", 10))
        self.streak_display_label.grid(row=5, column=0, columnspan=4, padx=10, pady=(0, 10), sticky="ew")
        for i in range(4): self.root.grid_columnconfigure(i, weight=1)

    def _update_streak_display(self):
        if not hasattr(self, 'streak_display_label'): # UI not ready
            return

        display_text = "Streak: "
        if not self.current_art_piece_id:
            display_text += "No art challenge defined or available."
        elif self.current_art_piece_id == "ALL_UNLOCKED":
            display_text += "All art pieces unlocked! Congratulations!"
        else:
            target_art_def = next((art for art in self.ascii_art_definitions if art["id"] == self.current_art_piece_id), None)
            if target_art_def:
                required_symbols = get_symbols_from_art(target_art_def["art_string"])
                total_len = len(required_symbols)
                revealed_symbols = required_symbols[:self.current_art_progress]

                # Construct partial art string for display
                placeholder_char = "_" 
                partial_art_str = "".join(revealed_symbols) + \
                                placeholder_char * (total_len - self.current_art_progress)

                display_text += f"{target_art_def['name']} | Progress: {partial_art_str} ({self.current_art_progress}/{total_len})"
            else:
                display_text += "Loading art challenge..."

        self.streak_display_label.config(text=display_text)

    def _on_window_resize(self, event=None):
        if hasattr(self, 'xp_bar_canvas') and self.xp_bar_canvas.winfo_exists():
            self.xp_bar_canvas.after_idle(self._draw_xp_bar)

    def _create_rounded_rect(self, canvas, x1, y1, x2, y2, radius, **kwargs):
        if x2 < x1 or y2 < y1: return None
        radius = min(radius, (x2 - x1) / 2, (y2 - y1) / 2)
        if radius < 0: radius = 0
        points = [
            x1 + radius, y1, x2 - radius, y1,
            x2 - radius, y1, x2, y1, x2, y1 + radius,
            x2, y1 + radius, x2, y2 - radius,
            x2, y2 - radius, x2, y2, x2 - radius, y2,
            x2 - radius, y2, x1 + radius, y2,
            x1 + radius, y2, x1, y2, x1, y2 - radius,
            x1, y2 - radius, x1, y1 + radius,
            x1, y1 + radius, x1, y1, x1 + radius, y1,
        ]
        return canvas.create_polygon(points, **kwargs, smooth=True)

    def _create_menubar(self):
        menubar = tk.Menu(self.root)
        edit_menu = tk.Menu(menubar, name='edit', tearoff=0)
        edit_menu.add_command(label="Manage Blocked Websites...", command=self._open_block_list_manager)
        edit_menu.add_separator()
        edit_menu.add_command(label="Edit Pomodoro Sequence...", command=self._open_sequence_editor) # New Menu Item

        achievements_menu = tk.Menu(menubar, name='achievements', tearoff=0)
        achievements_menu.add_command(label="View Unlocked Art", command=self._open_achievements_viewer)
        menubar.add_cascade(label="Achievements", menu=achievements_menu) # Add it as a top-level menu

        menubar.add_cascade(label="Edit", menu=edit_menu)
        self.root.config(menu=menubar)

    def _open_sequence_editor(self):
        if self.sequence_editor_window is None or not self.sequence_editor_window.winfo_exists():
            self.sequence_editor_window = SequenceEditorWindow(self.root, self) # Pass self as app_controller
            self.sequence_editor_window.protocol("WM_DELETE_WINDOW", self._on_sequence_editor_close)
        else:
            self.sequence_editor_window.lift()
            self.sequence_editor_window.focus_set()

    def _on_sequence_editor_close(self):
        if self.sequence_editor_window:
            self.sequence_editor_window.destroy()
            self.sequence_editor_window = None
    
    def _open_achievements_viewer(self):
        if not hasattr(self, '_achievements_window') or \
        not self._achievements_window or \
        not self._achievements_window.winfo_exists():
            self._achievements_window = AchievementsWindow(self.root, self)
        else:
            self._achievements_window.lift()
            self._achievements_window.focus_set()

    def _draw_xp_bar(self):
        if not hasattr(self, 'xp_bar_canvas') or not self.xp_bar_canvas.winfo_exists(): return
        self.xp_bar_canvas.delete("all")
        canvas_width = self.xp_bar_canvas.winfo_width()
        if canvas_width <= 20: canvas_width = 400
        bar_x_start = 10
        bar_y_start = 5
        bar_width = canvas_width - (bar_x_start * 2)
        if bar_width <= 0: return
        self._create_rounded_rect(self.xp_bar_canvas, bar_x_start, bar_y_start,
                                  bar_x_start + bar_width, bar_y_start + XP_BAR_HEIGHT,
                                  XP_BAR_CORNER_RADIUS, fill=XP_BAR_BG_COLOR, outline=XP_BAR_BG_COLOR)
        xp_percentage = 0.0
        if self.pomodoros_for_full_xp > 0:
            xp_percentage = min(self.pomodoro_count / self.pomodoros_for_full_xp, 1.0)
        filled_width = bar_width * xp_percentage
        if filled_width > 0:
            self._create_rounded_rect(self.xp_bar_canvas, bar_x_start, bar_y_start,
                                      bar_x_start + filled_width, bar_y_start + XP_BAR_HEIGHT,
                                      XP_BAR_CORNER_RADIUS, fill=XP_BAR_FG_COLOR, outline=XP_BAR_FG_COLOR)
            highlight_thickness = 1
            if filled_width > XP_BAR_CORNER_RADIUS * 2 and XP_BAR_HEIGHT > highlight_thickness * 2:
                self.xp_bar_canvas.create_line(
                    bar_x_start + XP_BAR_CORNER_RADIUS, bar_y_start + highlight_thickness,
                    bar_x_start + filled_width - XP_BAR_CORNER_RADIUS, bar_y_start + highlight_thickness,
                    fill=XP_BAR_HIGHLIGHT_COLOR, width=highlight_thickness
                )
        self.pomodoros_completed_label.config(text=f"XP: {self.pomodoro_count} / {self.pomodoros_for_full_xp} Pomodoros")
    
    def _handle_xp_bar_full(self):
        """Called when pomodoro_count reaches pomodoros_for_full_xp."""
        print("XP bar is full. Processing streak.")

        if not self.current_art_piece_id or self.current_art_piece_id == "ALL_UNLOCKED":
            print("XP bar full, but no current art piece to progress or all unlocked.")
            if self.current_art_piece_id != "ALL_UNLOCKED": # If None, try to set one.
                self._update_current_art_piece() 
            if not self.current_art_piece_id or self.current_art_piece_id == "ALL_UNLOCKED":
                # Reset pomodoro count even if no art piece to progress for consistency
                self.pomodoro_count = 0
                self._draw_xp_bar()
                return

        today_obj = datetime.date.today()
        today_str = today_obj.isoformat()

        target_art_def = next((art for art in self.ascii_art_definitions if art["id"] == self.current_art_piece_id), None)
        if not target_art_def:
            print(f"Error: Current art piece ID '{self.current_art_piece_id}' not found.")
            self._update_current_art_piece() # Attempt to recover
            self.pomodoro_count = 0 # Reset XP for next attempt
            self._draw_xp_bar()
            return

        required_symbols = get_symbols_from_art(target_art_def["art_string"])
        required_streak_length = len(required_symbols)

        # 1. Check if already awarded today
        if self.last_xp_full_date_str == today_str:
            print("Daily art progress already awarded for today.")
            # XP bar should remain full until next day's first focus completion makes it 0 again
            # Or, if we want it to reset now to allow re-earning:
            # self.pomodoro_count = 0
            # self._draw_xp_bar()
            return # Crucially, don't process further for *this* XP fill event if already awarded today

        # 2. Check for broken streak (if there was a previous date and some progress)
        streak_broken_this_time = False
        if self.last_xp_full_date_str and self.current_art_progress > 0:
            try:
                last_date_obj = datetime.date.fromisoformat(self.last_xp_full_date_str)
                days_diff = (today_obj - last_date_obj).days
                if days_diff > 1:
                    print(f"Streak broken for '{target_art_def['name']}'. Progress was {self.current_art_progress}, days_diff: {days_diff}")
                    messagebox.showinfo("Streak Broken!",
                                        f"You missed a day! Your progress on art piece '{target_art_def['name']}' has been reset.",
                                        parent=self.root)
                    self.current_art_progress = 0
                    streak_broken_this_time = True # Progress will be 1 after today's award
            except ValueError:
                print(f"Error parsing last_xp_full_date_str: {self.last_xp_full_date_str}. Assuming new streak.")
                self.current_art_progress = 0 # Treat as new streak if date is corrupt

        # 3. Award progress for today
        self.current_art_progress += 1
        self.last_xp_full_date_str = today_str # Update to today

        # Display logic for current art progress (partial art)
        revealed_art_so_far = "".join(required_symbols[:self.current_art_progress])
        placeholder_char = "_" # Or "." or "?"
        display_progress_art = revealed_art_so_far + placeholder_char * (required_streak_length - self.current_art_progress)

        if streak_broken_this_time:
            print(f"Streak for '{target_art_def['name']}' restarted. Progress: 1/{required_streak_length}. Art: {display_progress_art}")
        else:
            print(f"Streak progress for '{target_art_def['name']}': {self.current_art_progress}/{required_streak_length}. Art: {display_progress_art}")

        self._update_streak_display() # Update the UI label

        # 4. Check for art piece completion
        if self.current_art_progress >= required_streak_length:
            self.unlocked_achievements.append(self.current_art_piece_id)
            print(f"Art piece '{target_art_def['name']}' ({target_art_def['art_string']}) unlocked!")
            messagebox.showinfo("Achievement Unlocked!",
                                f"Congratulations! You've completed the art piece:\n{target_art_def['name']}\n\n{target_art_def['art_string']}",
                                parent=self.root)

            # Reset for the next piece
            self.current_art_progress = 0 
            # self.last_xp_full_date_str = None # Let this be handled by next day's check
            self._update_current_art_piece() # Sets up the next art piece (and calls _update_streak_display)

        # 5. Reset pomodoro_count as XP is now "spent" for today's art symbol
        self.pomodoro_count = 0
        self._draw_xp_bar()

        self._save_settings()

    def _setup_timer_canvas_elements(self):
        center_x = CIRCLE_CANVAS_SIZE / 2
        center_y = CIRCLE_CANVAS_SIZE / 2
        radius = (CIRCLE_CANVAS_SIZE / 2) - CIRCLE_PADDING
        x0 = center_x - radius
        y0 = center_y - radius
        x1 = center_x + radius
        y1 = center_y + radius
        self.arc_bbox = (x0, y0, x1, y1)
        self.timer_canvas.create_arc(
            self.arc_bbox, start=0, extent=359.99,
            outline=CIRCLE_BG_COLOR, width=CIRCLE_THICKNESS, style=tk.ARC
        )
        self.progress_arc_id = self.timer_canvas.create_arc(
            self.arc_bbox, start=90, extent=0,
            outline=CIRCLE_FG_COLOR_FOCUS, width=CIRCLE_THICKNESS, style=tk.ARC
        )
        self.time_text_id = self.timer_canvas.create_text(
            center_x, center_y, text="00:00",
            font=("Helvetica", int(CIRCLE_CANVAS_SIZE / 4.5), "bold"), fill=CIRCLE_TEXT_COLOR
        )

    def _start_automatic_focus_session(self):
        print("Starting automatic focus session.")
        self.timer_running = False
        self.current_state = "Idle"
        if not self._start_session_common("Focus", "", self.focus_duration_minutes):
            self._reset_session_end_actions()

    def _update_timer_display(self):
        mins, secs = divmod(max(0, self.remaining_seconds), 60)
        time_format = f"{int(mins):02d}:{int(secs):02d}"
        if hasattr(self, 'time_text_id') and self.time_text_id:
             self.timer_canvas.itemconfig(self.time_text_id, text=time_format)
        progress_extent = 0
        current_fg_color = CIRCLE_FG_COLOR_FOCUS
        if self.timer_running and self.total_seconds_for_session > 0:
            clamped_remaining = max(0, min(self.remaining_seconds, self.total_seconds_for_session))
            elapsed_seconds = self.total_seconds_for_session - clamped_remaining
            progress_percentage = elapsed_seconds / self.total_seconds_for_session
            progress_extent = progress_percentage * 359.99
            if self.current_state == "Focus":
                current_fg_color = CIRCLE_FG_COLOR_FOCUS
            elif self.current_state == "Break":
                current_fg_color = CIRCLE_FG_COLOR_BREAK
        if hasattr(self, 'progress_arc_id') and self.progress_arc_id:
            self.timer_canvas.itemconfig(self.progress_arc_id, extent=-progress_extent, outline=current_fg_color)
        if hasattr(self, 'timer_label'):
            status_text = "Status: Idle"
            if self.timer_running:
                if self.timer_paused:
                    status_text = f"Status: Paused ({self.current_state})"
                elif self.current_state == "Focus":
                    status_text = f"Status: Focus Time ({self.focus_duration_minutes} min)"
                elif self.current_state == "Break":
                    break_duration_attr = f"{self.current_break_type.lower()}_break_duration_minutes"
                    current_break_total_duration = getattr(self, break_duration_attr, self.short_break_duration_minutes)
                    status_text = f"Status: {self.current_break_type} Break ({current_break_total_duration} min)"
            self.timer_label.config(text=status_text)

    # --- MODIFICATION: This is now the primary (and only) _load_settings method ---
    def _load_settings(self):
        try:
            if CONFIG_FILE_PATH.exists():
                with open(CONFIG_FILE_PATH, "r", encoding='utf-8') as f:
                    settings = json.load(f)
                # ... (loading durations, custom_sequence as before) ...
                self.focus_duration_minutes = int(settings.get("focus_duration_minutes", self.focus_duration_minutes))
                self.short_break_duration_minutes = int(settings.get("short_break_duration_minutes", self.short_break_duration_minutes))
                self.long_break_duration_minutes = int(settings.get("long_break_duration_minutes", self.long_break_duration_minutes))
                self.eating_break_duration_minutes = int(settings.get("eating_break_duration_minutes", self.eating_break_duration_minutes))

                loaded_sequence_raw = settings.get("custom_sequence", DEFAULT_SEQUENCE)
                # ... (sequence loading logic as before) ...
                if not loaded_sequence_raw: # Handle empty sequence from file
                    self.custom_sequence = list(DEFAULT_SEQUENCE) 
                elif isinstance(loaded_sequence_raw, list) and loaded_sequence_raw and isinstance(loaded_sequence_raw[0], str):
                    self.custom_sequence = [{'type': item_str, 'name': item_str} for item_str in loaded_sequence_raw]
                elif isinstance(loaded_sequence_raw, list) and all(isinstance(item, dict) and 'type' in item and 'name' in item for item in loaded_sequence_raw):
                    self.custom_sequence = loaded_sequence_raw 
                else: 
                    self.custom_sequence = list(DEFAULT_SEQUENCE) 

                # Load Streak Data
                self.unlocked_achievements = settings.get("unlocked_achievements", [])
                self.current_art_piece_id = settings.get("current_art_piece_id", None)
                self.current_art_progress = settings.get("current_art_progress", 0)
                self.last_xp_full_date_str = settings.get("last_xp_full_date_str", None)

            else: # Config file doesn't exist
                self.custom_sequence = list(DEFAULT_SEQUENCE)
                # Initialize streak defaults for a fresh start
                self.unlocked_achievements = []
                self.current_art_piece_id = None # Will be set by _update_current_art_piece
                self.current_art_progress = 0
                self.last_xp_full_date_str = None

            self._recalculate_xp_goal_from_sequence() # This should be called after custom_sequence is set

            if not CONFIG_FILE_PATH.exists():
                self._update_current_art_piece() # Set initial piece if new config
                self._save_settings() # Save initial settings

        # ... (except blocks as before, ensure _reset_to_default_settings_and_save also handles streak vars) ...
        except (json.JSONDecodeError, ValueError, TypeError) as e:
            print(f"Error loading settings file '{CONFIG_FILE_PATH}': {e}. Using default values.")
            self._reset_to_default_settings_and_save()
        except Exception as e:
            print(f"An unexpected error occurred while loading settings: {e}. Using default values.")
            self._reset_to_default_settings_and_save()
        finally:
            self.current_sequence_index = -1
            # Call _update_current_art_piece here too, to ensure consistency if loaded data was odd
            self._update_current_art_piece()

    # --- MODIFICATION: This is now the primary (and only) _reset_to_default_settings_and_save method ---
    def _reset_to_default_settings_and_save(self):
        """Resets all durations, sequence, and streak to defaults and saves them."""
        self._initialize_durations() # Sets self.pomodoros_for_full_xp to DEFAULT initially
        self.custom_sequence = list(DEFAULT_SEQUENCE)
        self.current_sequence_index = -1

        # Reset streak data
        self.unlocked_achievements = []
        self.current_art_piece_id = None # _update_current_art_piece will pick the first
        self.current_art_progress = 0
        self.last_xp_full_date_str = None

        self._recalculate_xp_goal_from_sequence()
        self._update_current_art_piece() # Set the first art piece as current

        self._save_settings()
        if hasattr(self, 'xp_bar_canvas') and self.xp_bar_canvas.winfo_exists(): # Ensure UI is ready
            self._draw_xp_bar()
            self._update_streak_display()

    def _recalculate_xp_goal_from_sequence(self):
        """
        Calculates and sets self.pomodoros_for_full_xp based on the number of 
        'Focus' sessions in the current custom_sequence.
        Updates the XP bar display.
        """
        focus_count = 0
        if self.custom_sequence:  # Check if sequence exists and is not empty
            for item in self.custom_sequence:
                if item.get('type') == "Focus":
                    focus_count += 1

        # If there are focus sessions, the goal is the number of focus sessions.
        # If there are no focus sessions (e.g., empty or break-only sequence),
        # set the goal to 1 to prevent division by zero and for sensible display.
        self.pomodoros_for_full_xp = focus_count if focus_count > 0 else 1

        print(f"Recalculated XP goal: {self.pomodoros_for_full_xp} based on {focus_count} focus sessions.")

        # Ensure XP bar is redrawn with the new goal
        if hasattr(self, 'xp_bar_canvas') and self.xp_bar_canvas.winfo_exists():
            self._draw_xp_bar()
        elif hasattr(self, 'pomodoros_completed_label'): # Fallback to update label text if canvas not ready
            self.pomodoros_completed_label.config(text=f"XP: {self.pomodoro_count} / {self.pomodoros_for_full_xp} Pomodoros")


    # --- MODIFICATION: This is now the primary (and only) _save_settings method ---
    def _save_settings(self):
        settings = {
            "focus_duration_minutes": self.focus_duration_minutes,
            "short_break_duration_minutes": self.short_break_duration_minutes,
            "long_break_duration_minutes": self.long_break_duration_minutes,
            "eating_break_duration_minutes": self.eating_break_duration_minutes,
            "custom_sequence": self.custom_sequence,
            # Streak Data
            "unlocked_achievements": self.unlocked_achievements,
            "current_art_piece_id": self.current_art_piece_id,
            "current_art_progress": self.current_art_progress,
            "last_xp_full_date_str": self.last_xp_full_date_str,
        }
        # ... (rest of saving logic as before) ...
        try:
            CONFIG_FILE_PATH.parent.mkdir(parents=True, exist_ok=True)
            with open(CONFIG_FILE_PATH, "w", encoding='utf-8') as f:
                json.dump(settings, f, indent=4)
            print("Settings saved (including streak data).")
        except Exception as e:
            messagebox.showerror("Settings Error", f"Could not save timer settings: {e}", parent=self.root if self.root.winfo_exists() else None)
            print(f"Error saving settings: {e}")

    def _update_ui_for_timer_state(self):
        timer_is_active = self.timer_running

        self._draw_stop_icon(is_enabled=timer_is_active)

        # Pause/Play icon:
        if timer_is_active:

            self._draw_pause_play_icon(show_play=self.timer_paused, is_enabled=True)
        else:
            can_start_new_sequence = bool(self.custom_sequence)
            self._draw_pause_play_icon(show_play=True, is_enabled=can_start_new_sequence)
        self._update_timer_display()


    def _play_sound_async(self, sound_file_path_obj):
        if not PLAYSOUND_AVAILABLE: return
        def play():
            try:
                sound_file_str = str(sound_file_path_obj)
                if sound_file_path_obj.exists():
                    print(f"Playing sound: {sound_file_str}")
                    playsound(sound_file_str)
                else:
                    print(f"Sound file not found: {sound_file_str}")
            except Exception as e:
                print(f"Error playing sound '{sound_file_str}': {e}")
        sound_thread = threading.Thread(target=play, daemon=True)
        sound_thread.start()

    def _handle_natural_session_completion(self):
        if not self.timer_running: return
        self.timer_paused = False 
        session_that_completed = self.current_state
        completed_break_type_for_message = self.current_break_type
        
        # --- Store whether early reload was done for *this specific break that just ended* ---
        # This is important because self.reload_attempted_early might be set by a tick just before this.
        early_reload_was_done_for_this_break = self.reload_attempted_early
        self.reload_attempted_early = False # Reset flag immediately for any future breaks
        # ---

        if self._timer_id:
            self.root.after_cancel(self._timer_id)
            self._timer_id = None

        # Main window de-iconify (lift() and focus_force() should still be commented out)
        if self.root.winfo_exists():
            if self.root.state() == 'iconic':
                self.root.deiconify() 
            # self.root.lift()          # Stays COMMENTED OUT
            # self.root.focus_force()   # Stays COMMENTED OUT

        def on_notification_acknowledged():
            if self.current_sequence_index >= -1 and self.custom_sequence:
                self._proceed_to_next_in_sequence()
            else:
                print("Session ended (notification acknowledged), but not in sequence. Resetting.")
                self._reset_session_end_actions()

        if hasattr(self, 'notification_window') and self.notification_window and self.notification_window.winfo_exists():
            try: self.notification_window.destroy() 
            except tk.TclError: pass
            finally: self.notification_window = None

        if session_that_completed == "Focus":
            # ... (Focus completion logic - unchanged) ...
            self.pomodoro_count += 1
            self._draw_xp_bar()
            if self.pomodoro_count >= self.pomodoros_for_full_xp: # Use >= just in case
            # Original message for XP Goal Reached (filling the bar)
                messagebox.showinfo("XP Goal Reached!", f"Congratulations! You've earned {self.pomodoros_for_full_xp} XP today!", parent=self.root)
                self._handle_xp_bar_full() # This will handle streak and potentially reset pomodoro_count

            if self.blocked_websites: # This should still happen
                self._unblock_domains(list(self.blocked_websites))
            
            self.notification_window = RepeatingNotificationWindow(
                master=self.root, title="Focus Ended",
                message="Focus session complete!\nPreparing next session in sequence.",
                sound_file_to_repeat=SOUND_FOCUS_COMPLETE,
                on_ok_callback=on_notification_acknowledged, app_controller=self)

        elif session_that_completed == "Break":
            print(f"Break '{completed_break_type_for_message}' naturally completed.")
            
            if not early_reload_was_done_for_this_break: # If early reload didn't happen
                next_session_is_focus = False
                peek_index = self.current_sequence_index + 1                 
                if self.custom_sequence: 
                    if 0 <= peek_index < len(self.custom_sequence):
                        next_session_details = self.custom_sequence[peek_index]
                        if next_session_details.get('type') == "Focus": 
                            next_session_is_focus = True
                else: 
                    next_session_is_focus = True 

                if next_session_is_focus and self.blocked_websites:
                    print("Next session will be Focus. Re-blocking websites now and attempting browser reload (standard timing).")
                    self._block_domains(list(self.blocked_websites))
                    self.root.after(250, self._simulate_browser_reload) 
                else: # Print appropriate skip message
                    if not next_session_is_focus: print(f"Break '{completed_break_type_for_message}' ended. Next session is not Focus. Skipping reload.")
                    elif not self.blocked_websites: print(f"Break '{completed_break_type_for_message}' ended. No websites in block list. Skipping reload.")
            else:
                print("Early reload sequence was already attempted for this break.")

            self.notification_window = RepeatingNotificationWindow(
                master=self.root, title="Break Over",
                message=f"{completed_break_type_for_message} break is over!\nPreparing next session in sequence.",
                sound_file_to_repeat=SOUND_BREAK_COMPLETE,
                on_ok_callback=on_notification_acknowledged, app_controller=self)

    def _draw_stop_icon(self, is_enabled=True):
        self.stop_icon_canvas.delete("all")
        square_color = STOP_ICON_COLOR_ACTIVE if is_enabled else STOP_ICON_COLOR_DISABLED
        pad = ICON_PADDING_STOP
        size = ICON_SIZE
        self.stop_icon_canvas.create_rectangle(pad, pad, size - pad, size - pad,
                                               fill=square_color, outline=square_color)

    def _on_stop_icon_click(self, event=None):
        if self.timer_running:
            self._stop_current_session()

    def _draw_pause_play_icon(self, show_play=True, is_enabled=True):
        self.pause_play_icon_canvas.delete("all")
        pad = ICON_PADDING_PLAY_PAUSE
        size = ICON_SIZE
        icon_color = PAUSE_PLAY_ICON_COLOR_DISABLED
        if is_enabled:
            icon_color = PLAY_ICON_COLOR_ACTIVE if show_play else PAUSE_ICON_COLOR_ACTIVE
        if show_play:
            points = [pad, pad, pad, size - pad, size - pad, size / 2]
            self.pause_play_icon_canvas.create_polygon(points, fill=icon_color, outline=icon_color)
        else:
            bar_width_ratio = 0.3
            total_bar_space = size - (2 * pad)
            bar_width = total_bar_space * bar_width_ratio
            gap = total_bar_space * (1 - 2 * bar_width_ratio) / 3
            if gap < 2 : gap = 2
            bar_width = (total_bar_space - gap) / 2
            if bar_width < 1: bar_width = 1
            x0_left = pad
            x1_left = pad + bar_width
            self.pause_play_icon_canvas.create_rectangle(x0_left, pad, x1_left, size - pad,
                                                         fill=icon_color, outline=icon_color)
            x0_right = x1_left + gap
            x1_right = x0_right + bar_width
            self.pause_play_icon_canvas.create_rectangle(x0_right, pad, x1_right, size - pad,
                                                         fill=icon_color, outline=icon_color)

    def _on_pause_play_icon_click(self, event=None):
        if self.timer_running:
            # Timer is running: Handle Pause/Resume
            self.timer_paused = not self.timer_paused
            if self.timer_paused:
                if self._timer_id:
                    self.root.after_cancel(self._timer_id)
                print("Timer Paused")
            else:
                print("Timer Resumed")
                self._tick_countdown() # Resume the countdown
        else:
            # Timer is NOT running: Handle Start Sequence
            if self.custom_sequence:
                # Ensure it's a fresh start or sequence truly ended.
                # _stop_current_session should set self.current_sequence_index to -1.
                if self.current_sequence_index == -1 or not self.timer_running:
                    print("Play icon clicked: Starting defined sequence.")
                    self.current_sequence_index = -1 # Reset to start from the beginning
                    self._proceed_to_next_in_sequence()
                # No 'else' needed here if _stop_current_session correctly resets the index
            else:
                messagebox.showerror("Sequence Error",
                                    "No Pomodoro sequence is defined. Please define one in Edit > Edit Pomodoro Sequence.",
                                    parent=self.root)
        self._update_ui_for_timer_state()

    def _start_session_common(self, state_name, break_type_name, duration_minutes):
        if self.timer_running:
            messagebox.showwarning("Timer Active", "A session is already in progress.", parent=self.root)
            return False
        if state_name == "Focus" and not self.blocked_websites:
            if not messagebox.askyesno("No Websites Blocked", "Your block list is empty. Start focus session anyway?", parent=self.root):
                return False
        self.timer_running = True
        self.timer_paused = False
        self.current_state = state_name
        self.current_break_type = break_type_name if state_name == "Break" else ""

        if state_name == "Break":
            self.reload_attempted_early = False
        
        self.total_seconds_for_session = duration_minutes * 60
        self.remaining_seconds = self.total_seconds_for_session
        if state_name == "Focus" and self.blocked_websites:
            self._block_domains(list(self.blocked_websites))
        self._update_ui_for_timer_state()
        self._tick_countdown()
        return True

    def _start_automatic_break_session(self):
        print("Starting automatic short break.")
        self.timer_running = False
        self.current_state = "Idle"
        if not self._start_session_common("Break", "Short", self.short_break_duration_minutes):
            self._reset_session_end_actions()


    def _stop_current_session(self):
        if not self.timer_running:
            return
        if hasattr(self, 'notification_window') and self.notification_window and self.notification_window.winfo_exists():
            try:
                self.notification_window._stop_repeating_sound()
                self.notification_window.destroy()
            except tk.TclError:
                pass # May already be in process of destroying
            finally:
                self.notification_window = None

        was_focus_session = (self.current_state == "Focus")
        stopped_break_type = self.current_break_type if self.current_state == "Break" else ""
        self.timer_running = False
        self.timer_paused = False
        if self._timer_id:
            self.root.after_cancel(self._timer_id)
            self._timer_id = None
        # --- MODIFICATION: Reset sequence index when a session is manually stopped ---
        if self.current_sequence_index != -1: # If a sequence was active
            print(f"Sequence interrupted by stopping the session. Current index was: {self.current_sequence_index}")
            self.current_sequence_index = -1 
        # --- END MODIFICATION ---
        self.current_state = "Idle"
        self.current_break_type = ""
        self.remaining_seconds = 0
        self.total_seconds_for_session = 0
        if was_focus_session and self.blocked_websites:
            self._unblock_domains(list(self.blocked_websites))
        log_message = "Focus session stopped." if was_focus_session else f"{stopped_break_type} break stopped."
        print(log_message)
        self._update_ui_for_timer_state()


    def _tick_countdown(self):
        if self.timer_paused:
            return
        if not self.timer_running or self.remaining_seconds < 0:
            if self.current_state != "Idle":
                self._reset_session_end_actions()
            return
        
        if self.current_state == "Break" and self.remaining_seconds == 3 and \
           not self.reload_attempted_early and self.blocked_websites:
            
            next_session_is_focus = False
            peek_index = self.current_sequence_index + 1
            if self.custom_sequence:
                if 0 <= peek_index < len(self.custom_sequence):
                    next_session_details = self.custom_sequence[peek_index]
                    if next_session_details.get('type') == "Focus":
                        next_session_is_focus = True
            else: # No custom sequence, default implies Focus after break
                next_session_is_focus = True
            
            if next_session_is_focus:
                print("Approaching end of break (3s remaining). Pre-emptively blocking sites and attempting reload.")
                self._block_domains(list(self.blocked_websites))
                # Call reload directly. The focus issue for pyautogui still remains paramount.
                # A tiny delay *might* help the OS register hosts file change before pyautogui acts.
                # This call is blocking for pyautogui, then _tick_countdown continues.
                # Consider if a self.root.after(50, self._simulate_browser_reload) is better
                # if _simulate_browser_reload takes too long and makes the 5-second tick inaccurate.
                # For now, direct call:
                self._simulate_browser_reload() 
                self.reload_attempted_early = True # Mark that we've done this for the current break
        self._update_timer_display()
        if self.remaining_seconds == 0:
            self._handle_natural_session_completion()
        else:
            self.remaining_seconds -= 1
            self._timer_id = self.root.after(1000, self._tick_countdown)


    def _reset_session_end_actions(self):
        was_focus_before_idle = (self.current_state == "Focus")
        self.timer_running = False
        self.timer_paused = False
        self.current_state = "Idle"
        self.current_break_type = ""
        self.remaining_seconds = 0
        self.total_seconds_for_session = 0
        if self._timer_id:
            self.root.after_cancel(self._timer_id)
            self._timer_id = None
        if was_focus_before_idle and self.blocked_websites:
            self._unblock_domains(list(self.blocked_websites))
        # --- MODIFICATION: Do not reset sequence index here, sequence completion handles it ---
        # if self.current_sequence_index != -1:
        #    print(f"Session ended. Sequence index remains: {self.current_sequence_index} until sequence completes or is stopped.")
        # --- END MODIFICATION ---
        self._update_ui_for_timer_state()


    def _reset_pomodoro_counter(self):
        if self.timer_running:
            messagebox.showwarning("Session Active", "Cannot reset XP during an active session.", parent=self.root)
            return
        if messagebox.askyesno("Reset XP", "Are you sure you want to reset the Pomodoro XP counter?", parent=self.root):
            self.pomodoro_count = 0
            self._draw_xp_bar()

    def on_closing(self):
        self._save_settings()
        if self.timer_running and self.current_state == "Focus" and self.blocked_websites:
            print("Unblocking sites as focus session was active on close.")
            self._unblock_domains(list(self.blocked_websites))
        self.timer_running = False
        self.timer_paused = False
        if self._timer_id:
            self.root.after_cancel(self._timer_id)
            self._timer_id = None
        print("Application closing.")
        if self.block_list_manager_window and self.block_list_manager_window.winfo_exists():
            self.block_list_manager_window.destroy()
        self.root.destroy()

    def _is_admin(self):
        try: return os.geteuid() == 0
        except AttributeError: return False

    def _open_block_list_manager(self):
        if self.block_list_manager_window is None or not self.block_list_manager_window.winfo_exists():
            self.block_list_manager_window = BlockListManagerWindow(self.root, self)
            self.block_list_manager_window.protocol("WM_DELETE_WINDOW", self._on_block_list_manager_close)
        else:
            self.block_list_manager_window.lift()
            self.block_list_manager_window.focus_set()

    def _on_block_list_manager_close(self):
        if self.block_list_manager_window:
            self.block_list_manager_window.destroy()
            self.block_list_manager_window = None

    def add_domain_to_blocklist_core(self, normalized_website):
        if normalized_website in self.blocked_websites:
            return False, f"{normalized_website} is already in the block list."
        self.blocked_websites.add(normalized_website)
        self._save_block_list_to_file()
        return True, f"{normalized_website} added to block list."

    def remove_domain_from_blocklist_core(self, selected_website):
        if selected_website not in self.blocked_websites:
            return False, f"{selected_website} not found in the block list."
        self._unblock_domains([selected_website])
        self.blocked_websites.remove(selected_website)
        self._save_block_list_to_file()
        return True, f"{selected_website} has been unblocked and removed from the list."

    def _load_block_list_from_file(self):
        self.blocked_websites.clear()
        if BLOCK_LIST_FILE_PATH.exists():
            try:
                with open(BLOCK_LIST_FILE_PATH, "r", encoding='utf-8') as f:
                    for line in f:
                        site = line.strip()
                        if site: self.blocked_websites.add(site)
            except Exception as e:
                messagebox.showwarning("Load Error", f"Could not read block list file:\n{BLOCK_LIST_FILE_PATH}\n{e}", parent=self.root)

    def _save_block_list_to_file(self):
        try:
            BLOCK_LIST_FILE_PATH.parent.mkdir(parents=True, exist_ok=True)
            with open(BLOCK_LIST_FILE_PATH, "w", encoding='utf-8') as f:
                for site in sorted(list(self.blocked_websites)):
                    f.write(site + "\n")
        except Exception as e:
            messagebox.showerror("Save Error", f"Could not write to block list file:\n{BLOCK_LIST_FILE_PATH}\n{e}", parent=self.root)

    def _get_domains_to_manage(self, domain):
        domain_lower = domain.lower()
        domains = {domain_lower}
        if domain_lower.startswith("www."):
            domains.add(domain_lower[4:])
        else:
            domains.add("www." + domain_lower)
        return domains

    def _read_hosts_file(self):
        try:
            with open(HOSTS_FILE_PATH, "r", encoding='utf-8') as f:
                return f.readlines()
        except FileNotFoundError:
            messagebox.showerror("Hosts File Error", f"{HOSTS_FILE_PATH} not found.", parent=self.root)
            return None
        except Exception as e:
            messagebox.showerror("Hosts File Error", f"Could not read {HOSTS_FILE_PATH}: {e}", parent=self.root)
            return None

    def _write_hosts_file(self, lines_to_write):
        try:
            processed_lines = []
            if lines_to_write:
                for line_content in lines_to_write:
                    stripped_line = line_content.strip()
                    if stripped_line:
                        processed_lines.append(stripped_line + "\n")
            with open(HOSTS_FILE_PATH, "w", encoding='utf-8') as f:
                f.writelines(processed_lines)
            return True
        except PermissionError:
            messagebox.showerror("Permission Error", f"Could not write to {HOSTS_FILE_PATH}. Run with sudo.", parent=self.root)
            return False
        except Exception as e:
            messagebox.showerror("Hosts File Error", f"Could not write to {HOSTS_FILE_PATH}: {e}", parent=self.root)
            return False

    def _block_domains(self, domains_to_block_list):
        if not domains_to_block_list: return
        original_hosts_lines = self._read_hosts_file()
        if original_hosts_lines is None: return
        all_managed_variants_to_block = set()
        for domain_base in domains_to_block_list:
            all_managed_variants_to_block.update(self._get_domains_to_manage(domain_base))
        filtered_lines = []
        modified = False
        for line in original_hosts_lines:
            stripped_line = line.strip()
            parts = stripped_line.split(None, 2)
            should_remove_this_line = False
            if len(parts) >= 2 and parts[0] == REDIRECT_IP:
                if parts[1] in all_managed_variants_to_block:
                    should_remove_this_line = True
                    modified = True
            if not should_remove_this_line:
                filtered_lines.append(line.rstrip('\n') + '\n')
        new_blocking_entries_to_add = []
        for managed_domain in sorted(list(all_managed_variants_to_block)):
            new_blocking_entries_to_add.append(f"{REDIRECT_IP}\t{managed_domain}\t{POMODORO_COMMENT}\n")
            modified = True
        final_lines = filtered_lines + new_blocking_entries_to_add
        if modified:
            if self._write_hosts_file(final_lines):
                print(f"Hosts file updated to BLOCK: {', '.join(domains_to_block_list)}")
        else:
             print(f"No changes needed to hosts file for BLOCKING: {', '.join(domains_to_block_list)}")

    def _unblock_domains(self, domains_to_unblock_list):
        if not domains_to_unblock_list: return
        original_hosts_lines = self._read_hosts_file()
        if original_hosts_lines is None: return
        all_managed_variants_to_unblock = set()
        for domain_base in domains_to_unblock_list:
            all_managed_variants_to_unblock.update(self._get_domains_to_manage(domain_base))
        resulting_lines = []
        modified = False
        for line in original_hosts_lines:
            keep_this_line = True
            stripped_line = line.strip()
            parts = stripped_line.split(None, 2)
            if len(parts) >= 2 and parts[0] == REDIRECT_IP:
                if parts[1] in all_managed_variants_to_unblock:
                    keep_this_line = False
                    modified = True
            if keep_this_line:
                resulting_lines.append(line.rstrip('\n') + '\n')
        if modified:
            if self._write_hosts_file(resulting_lines):
                print(f"Hosts file updated to UNBLOCK: {', '.join(domains_to_unblock_list)}")
        else:
            print(f"No unblocking changes needed in hosts file for: {', '.join(domains_to_unblock_list)}")

    def _ensure_all_blocked_sites_are_unblocked_on_startup(self):
        if self.blocked_websites:
            print(f"Ensuring sites from app's list are unblocked on startup: {list(self.blocked_websites)}")
            self._unblock_domains(list(self.blocked_websites))

# +++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++
# Main Execution
# +++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++
if __name__ == "__main__":
    main_root = tk.Tk()

    if PILLOW_AVAILABLE:
        try:
            if APP_ICON_PATH.exists():
                pil_img = Image.open(APP_ICON_PATH)
                icon_image = ImageTk.PhotoImage(pil_img)
                main_root.iconphoto(True, icon_image)
                print(f"Custom icon loaded from: {APP_ICON_PATH}")
            else:
                print(f"Warning: Custom icon file not found at {APP_ICON_PATH}. Using default icon.")
        except Exception as e:
            print(f"Error loading custom icon with Pillow: {e}. Using default icon.")
    else:
        print("Pillow not found. Custom icon setting skipped (non-Windows, no .ico fallback). Using default icon.")

    is_admin_check = False
    try:
        is_admin_check = (os.geteuid() == 0)
    except AttributeError:
        is_admin_check = False
    if not is_admin_check and sys.platform != "win32":
        try:
            messagebox.showerror("Admin Privileges Required", "This application must be run with sudo/administrator privileges to modify the hosts file.")
        except tk.TclError:
            print("CRITICAL ERROR: Admin Privileges Required. Please run with sudo or as Administrator.", file=sys.stderr)
        main_root.destroy()
        sys.exit(1)
    try:
        SOUND_DIR.mkdir(parents=True, exist_ok=True)
        print(f"Sound directory ensured at: {SOUND_DIR}")
        if not SOUND_FOCUS_COMPLETE.exists() or not SOUND_BREAK_COMPLETE.exists():
            print(f"Reminder: Place sound files ('{SOUND_FOCUS_COMPLETE.name}', '{SOUND_BREAK_COMPLETE.name}') in '{SOUND_DIR}' for audio notifications.")
    except Exception as e:
        print(f"Could not create sound directory '{SOUND_DIR}': {e}")

    app = PomodoroWebsiteBlocker(main_root)
    if hasattr(app, 'root') and app.root.winfo_exists():
        main_root.focus_force()
        main_root.protocol("WM_DELETE_WINDOW", app.on_closing)
        main_root.mainloop()
    else:
        print("Application could not complete initialization. Exiting.")