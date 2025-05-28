import tkinter as tk
from tkinter import ttk, messagebox
import os
import sys
import time # Still used for initial timestamp logic if any, but not for sleep in countdown
import threading # Kept for potentially offloading heavy tasks if needed in future, but countdown is now on main thread via 'after'
from pathlib import Path
import queue # For safer thread communication if we were to use threads for more complex ops

HOSTS_FILE_PATH = "/etc/hosts"
BLOCK_LIST_FILE_PATH = Path.home() / ".website_blocker_list.txt"
REDIRECT_IP = "127.0.0.1"
POMODORO_COMMENT = "# Added by PomodoroBlocker"

class PomodoroWebsiteBlocker:
    def __init__(self, root_window):
        self.root = root_window
        self.root.title("Pomodoro Website Blocker")
        self.root.geometry("550x650")

        if not self._is_admin():
            messagebox.showerror(
                "Admin Privileges Required",
                "This application must be run with sudo privileges to modify the hosts file."
            )
            self.root.destroy()
            return

        self.blocked_websites = set()
        self.pomodoro_count = 0
        self.timer_running = False
        self.current_state = "Idle"  # Idle, Focus, Break
        self.remaining_seconds = 0
        self._timer_id = None # To store the ID of the 'after' job

        # --- UI Elements ---
        ttk.Label(self.root, text="Website (e.g., example.com):").grid(row=0, column=0, padx=10, pady=5, sticky="w")
        self.website_entry = ttk.Entry(self.root, width=30)
        self.website_entry.grid(row=0, column=1, padx=10, pady=5, sticky="ew")

        self.add_button = ttk.Button(self.root, text="Add to Block List", command=self._add_website)
        self.add_button.grid(row=0, column=2, padx=5, pady=5)

        ttk.Label(self.root, text="Blocked Websites:").grid(row=1, column=0, padx=10, pady=5, sticky="nw")
        self.listbox_frame = ttk.Frame(self.root)
        self.listbox_frame.grid(row=2, column=0, columnspan=3, padx=10, pady=5, sticky="nsew")
        self.listbox = tk.Listbox(self.listbox_frame, selectmode=tk.SINGLE, height=10)
        self.listbox_scrollbar = ttk.Scrollbar(self.listbox_frame, orient=tk.VERTICAL, command=self.listbox.yview)
        self.listbox.configure(yscrollcommand=self.listbox_scrollbar.set)
        self.listbox.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        self.listbox_scrollbar.pack(side=tk.RIGHT, fill=tk.Y)

        self.unblock_button = ttk.Button(self.root, text="Unblock Selected", command=self._unblock_selected_website)
        self.unblock_button.grid(row=3, column=0, columnspan=3, padx=10, pady=10)

        ttk.Separator(self.root, orient='horizontal').grid(row=4, column=0, columnspan=3, sticky='ew', pady=10)

        self.timer_label = ttk.Label(self.root, text="Status: Idle", font=("Helvetica", 14))
        self.timer_label.grid(row=5, column=0, columnspan=3, padx=10, pady=10)

        self.countdown_label = ttk.Label(self.root, text="Time: 00:00", font=("Helvetica", 24, "bold"))
        self.countdown_label.grid(row=6, column=0, columnspan=3, padx=10, pady=10)

        self.start_focus_button = ttk.Button(self.root, text="Start Focus (25 min)", command=self._start_focus_session)
        self.start_focus_button.grid(row=7, column=0, padx=5, pady=10)

        self.start_break_button = ttk.Button(
            self.root,
            text="Start Break (5 min)",
            command=self._start_manual_break_session
        )
        self.start_break_button.grid(row=8, column=0, padx=5, pady=5)


        self.pomodoros_completed_label = ttk.Label(self.root, text=f"Pomodoros Completed: {self.pomodoro_count}")
        self.pomodoros_completed_label.grid(row=7, column=1, padx=5, pady=10, sticky="w")

        self.reset_counter_button = ttk.Button(self.root, text="Reset Counter", command=self._reset_pomodoro_counter)
        self.reset_counter_button.grid(row=7, column=2, padx=5, pady=10, sticky="e")

        self.root.grid_columnconfigure(1, weight=1)
        self.root.grid_rowconfigure(2, weight=1)

        self._load_block_list_from_file() # This now correctly calls _update_listbox internally
        self._ensure_all_blocked_sites_are_unblocked_on_startup()

    def _is_admin(self):
        try:
            return os.geteuid() == 0
        except AttributeError:
            return False

    def _read_hosts_file(self):
        try:
            with open(HOSTS_FILE_PATH, "r", encoding='utf-8') as f:
                return f.readlines()
        except FileNotFoundError:
            messagebox.showerror("Error", f"{HOSTS_FILE_PATH} not found.")
            return None # Changed from [] to None to be more explicit for error
        except Exception as e:
            messagebox.showerror("Error", f"Could not read {HOSTS_FILE_PATH}: {e}")
            return None

    def _write_hosts_file(self, lines):
        try:
            # Ensure all lines end with a newline and the file ends with one if not empty
            processed_lines = []
            if lines:
                for line in lines:
                    stripped_line = line.strip()
                    if stripped_line: # Avoid adding newlines to empty/whitespace lines
                        processed_lines.append(stripped_line + "\n")
                # Ensure last line is a newline if content exists
                if processed_lines and not processed_lines[-1].endswith("\n"):
                     processed_lines[-1] += "\n"
            
            # Handle case where lines become empty (e.g. unblocking the last site)
            if not processed_lines and lines is not None: # lines was not None but resulted in no processed_lines
                pass # Write an empty file or a file with a comment
                # open(HOSTS_FILE_PATH, "w", encoding='utf-8').close() # To write an empty file
                # For safety, let's ensure we only write if there are lines, or if original was empty.
                # If processed_lines is empty, it means all relevant lines were removed.


            with open(HOSTS_FILE_PATH, "w", encoding='utf-8') as f:
                f.writelines(processed_lines)
            return True
        except PermissionError:
            messagebox.showerror("Permission Error", f"Could not write to {HOSTS_FILE_PATH}. Run with sudo.")
            return False
        except Exception as e:
            messagebox.showerror("Error", f"Could not write to {HOSTS_FILE_PATH}: {e}")
            return False

    def _load_block_list_from_file(self):
        self.blocked_websites.clear()
        if BLOCK_LIST_FILE_PATH.exists():
            try:
                with open(BLOCK_LIST_FILE_PATH, "r", encoding='utf-8') as f:
                    for line in f:
                        site = line.strip()
                        if site:
                            self.blocked_websites.add(site)
            except Exception as e:
                messagebox.showwarning("Load Error", f"Could not read {BLOCK_LIST_FILE_PATH}: {e}")
        self._update_listbox() # Removed redundant call from __init__

    def _save_block_list_to_file(self):
        try:
            with open(BLOCK_LIST_FILE_PATH, "w", encoding='utf-8') as f:
                for site in sorted(list(self.blocked_websites)):
                    f.write(site + "\n")
        except Exception as e:
            messagebox.showerror("Save Error", f"Could not write to {BLOCK_LIST_FILE_PATH}: {e}")

    def _update_listbox(self):
        self.listbox.delete(0, tk.END)
        for site in sorted(list(self.blocked_websites)):
            self.listbox.insert(tk.END, site)

    def _get_domains_to_manage(self, domain):
        domains = {domain.lower()}
        if domain.startswith("www."):
            domains.add(domain[4:])
        else:
            domains.add("www." + domain)
        return domains

    def _add_website(self):
        website = self.website_entry.get().strip()
        if not website:
            messagebox.showwarning("Input Error", "Please enter a website domain.")
            return

        normalized_website = website.lower().replace("http://", "").replace("https://", "").split('/')[0]
        if not normalized_website: # Handle case of "http://" being entered alone
            messagebox.showwarning("Input Error", "Invalid website domain entered.")
            return

        if normalized_website in self.blocked_websites:
            messagebox.showinfo("Already Blocked", f"{normalized_website} is already in the block list.")
            self.website_entry.delete(0, tk.END)
            return

        self.blocked_websites.add(normalized_website)
        self._save_block_list_to_file()
        self._update_listbox()
        self.website_entry.delete(0, tk.END)
        messagebox.showinfo("Success", f"{normalized_website} added to block list.")

    def _block_domains(self, domains_to_block_list):
        if not domains_to_block_list:
            return

        original_hosts_lines = self._read_hosts_file()
        if original_hosts_lines is None:
            return # Error already shown by _read_hosts_file

        # Create a comprehensive set of all managed domain variations for efficient lookup
        all_managed_variants_to_block = set()
        for domain_base in domains_to_block_list:
            all_managed_variants_to_block.update(self._get_domains_to_manage(domain_base))

        # Filter out existing blocking entries for the target domains
        # An entry is removed if it starts with REDIRECT_IP and its second field is one of the managed domains.
        filtered_lines = []
        modified_by_removal = False
        for line in original_hosts_lines:
            stripped_line = line.strip()
            parts = stripped_line.split(None, 2) # Split max 2 times on whitespace
            should_remove_line = False
            if len(parts) >= 2 and parts[0] == REDIRECT_IP:
                if parts[1] in all_managed_variants_to_block:
                    should_remove_line = True
                    modified_by_removal = True
            
            if not should_remove_line:
                filtered_lines.append(line) # Keep original line with its newline

        # Prepare the new lines to add (with comment)
        new_blocking_entries_to_add = []
        for managed_domain in sorted(list(all_managed_variants_to_block)): # Sorted for consistent hosts file
            new_blocking_entries_to_add.append(f"{REDIRECT_IP}\t{managed_domain}\t{POMODORO_COMMENT}\n")
            
        final_lines = filtered_lines + new_blocking_entries_to_add
        
        # Write if changes were made (either removals or additions)
        # A more robust check is to see if the content actually changed.
        # For simplicity, we'll write if we intended to add or explicitly removed.
        if modified_by_removal or new_blocking_entries_to_add:
            if self._write_hosts_file(final_lines):
                print(f"Hosts file updated to block: {', '.join(domains_to_block_list)}")
        else:
             print(f"No changes needed to hosts file for blocking: {', '.join(domains_to_block_list)}")


    def _unblock_domains(self, domains_to_unblock_list):
        if not domains_to_unblock_list:
            return

        original_hosts_lines = self._read_hosts_file()
        if original_hosts_lines is None:
            return

        all_managed_variants_to_unblock = set()
        for domain_base in domains_to_unblock_list:
            all_managed_variants_to_unblock.update(self._get_domains_to_manage(domain_base))

        new_lines = []
        modified = False
        for line in original_hosts_lines:
            keep_line = True
            stripped_line = line.strip()
            parts = stripped_line.split(None, 2) # Split max 2 times

            if len(parts) >= 2 and parts[0] == REDIRECT_IP:
                if parts[1] in all_managed_variants_to_unblock:
                    keep_line = False
                    modified = True
            
            if keep_line:
                new_lines.append(line) # Keep original line with its newline

        if modified:
            if self._write_hosts_file(new_lines):
                print(f"Hosts file updated to unblock: {', '.join(domains_to_unblock_list)}")
        else:
            print(f"No unblocking changes needed in hosts file for: {', '.join(domains_to_unblock_list)}")


    def _unblock_selected_website(self):
        selected_indices = self.listbox.curselection()
        if not selected_indices:
            messagebox.showwarning("Selection Error", "Please select a website to unblock.")
            return

        selected_website = self.listbox.get(selected_indices[0])
        self._unblock_domains([selected_website]) # This will handle www and non-www

        if selected_website in self.blocked_websites:
            self.blocked_websites.remove(selected_website)
        self._save_block_list_to_file()
        self._update_listbox()
        messagebox.showinfo("Success", f"{selected_website} has been unblocked.")

    def _ensure_all_blocked_sites_are_unblocked_on_startup(self):
        if BLOCK_LIST_FILE_PATH.exists():
            sites_from_file = []
            with open(BLOCK_LIST_FILE_PATH, "r", encoding='utf-8') as f:
                for line in f:
                    site = line.strip()
                    if site:
                        sites_from_file.append(site)
            if sites_from_file:
                print(f"Ensuring sites from list are unblocked on startup: {sites_from_file}")
                self._unblock_domains(sites_from_file)

    def _update_ui_for_timer_state(self):
        if self.timer_running:
            self.start_focus_button.config(state=tk.DISABLED)
            self.add_button.config(state=tk.DISABLED)
            self.unblock_button.config(state=tk.DISABLED)
        else:
            self.start_focus_button.config(state=tk.NORMAL)
            self.add_button.config(state=tk.NORMAL)
            self.unblock_button.config(state=tk.NORMAL)
            self.timer_label.config(text="Status: Idle")
            self.countdown_label.config(text="Time: 00:00")

    def _start_focus_session(self):
        if self.timer_running:
            messagebox.showwarning("Timer Active", "A session is already in progress.")
            return
        if not self.blocked_websites:
            if not messagebox.askyesno("No Websites Blocked",
                                       "Your block list is empty. Do you want to start a focus session anyway?"):
                return

        self.timer_running = True
        self.current_state = "Focus"
        self.timer_label.config(text="Status: Focus Time")
        self._update_ui_for_timer_state()
        
        self._block_domains(list(self.blocked_websites))

        self.remaining_seconds = 25 * 60 # 25 minutes
        # self.remaining_seconds = 5 # For testing
        self._tick_countdown()

    def _start_break_session(self):
        self.current_state = "Break"
        self.timer_label.config(text="Status: Break Time")
        # self._update_ui_for_timer_state() # UI remains disabled during break too
        
        # Websites remain unblocked during break
        self.remaining_seconds = 5 * 60 # 5 minutes
        # self.remaining_seconds = 3 # For testing
        self._tick_countdown()

    def _tick_countdown(self):
        if not self.timer_running or self.remaining_seconds < 0:
            self._reset_timer_state_actions() # Handle abrupt stop or completion
            return

        mins, secs = divmod(self.remaining_seconds, 60)
        time_format = f"{mins:02d}:{secs:02d}"
        self.countdown_label.config(text=f"Time: {time_format}")

        if self.remaining_seconds == 0:
            self._handle_session_completion()
        else:
            self.remaining_seconds -= 1
            self._timer_id = self.root.after(1000, self._tick_countdown) # Schedule next tick

    def _handle_session_completion(self):
        if self.current_state == "Focus":
            self.pomodoro_count += 1
            self.pomodoros_completed_label.config(text=f"Pomodoros Completed: {self.pomodoro_count}")
            messagebox.showinfo("Focus Ended", "Focus session complete! Time for a break.")
            self._unblock_domains(list(self.blocked_websites))
            self._start_break_session()
        elif self.current_state == "Break":
            messagebox.showinfo("Break Over", "Break time is over! Ready for another focus session?")
            self._reset_timer_state_actions() # This will re-enable UI
            self._update_ui_for_timer_state() # explicit call to ensure UI is correct

    def _reset_timer_state_actions(self):
        """Actions to take when timer stops or is reset, doesn't change UI itself."""
        self.timer_running = False
        self.current_state = "Idle"
        if self._timer_id:
            self.root.after_cancel(self._timer_id)
            self._timer_id = None
        
        # Unblock all sites from the list when timer is stopped/reset,
        # just in case it was stopped mid-focus.
        # _ensure_all_blocked_sites_are_unblocked_on_startup handles startup
        # on_closing handles app exit
        # This covers stopping a focus session prematurely.
        if self.blocked_websites:
             self._unblock_domains(list(self.blocked_websites))


    def _reset_pomodoro_counter(self):
        if messagebox.askyesno("Reset Counter", "Are you sure you want to reset the Pomodoro counter?"):
            self.pomodoro_count = 0
            self.pomodoros_completed_label.config(text=f"Pomodoros Completed: {self.pomodoro_count}")

    def on_closing(self):
        if self.timer_running:
            self.timer_running = False # Signal countdown to stop
            if self._timer_id:
                self.root.after_cancel(self._timer_id)
                self._timer_id = None
        
        print("Application closing. Ensuring all sites from list are unblocked.")
        # Important: Unblock sites based on the persistent list, not just self.blocked_websites
        # as the app might have just started and not fully loaded everything if closed quickly.
        # _ensure_all_blocked_sites_are_unblocked_on_startup already handles this for startup
        # But for closing, using the current state of self.blocked_websites is intended.
        if self.blocked_websites:
             self._unblock_domains(list(self.blocked_websites))
        self.root.destroy()


if __name__ == "__main__":
    main_root = tk.Tk()
    # Check for admin privileges early, even before creating the full app object
    # This avoids creating UI elements if not admin, though PomodoroWebsiteBlocker handles it too.
    is_admin_check = False
    try:
        is_admin_check = (os.geteuid() == 0)
    except AttributeError: # Windows or other non-POSIX
        is_admin_check = False # Default to false if can't check

    if not is_admin_check:
        # Show a preliminary message box if Tkinter is available enough for it
        try:
            messagebox.showerror(
                "Admin Privileges Required",
                "This application must be run with sudo privileges to modify the hosts file."
            )
        except tk.TclError: # If main_root isn't fully initialized for messagebox
            print("Error: Admin Privileges Required. This application must be run with sudo privileges.", file=sys.stderr)
        main_root.destroy() # Destroy the implicitly created root window
        sys.exit(1) # Exit early

    app = PomodoroWebsiteBlocker(main_root)
    # The app's __init__ also has a check and will destroy root if it fails.
    # This double check is fine. We only proceed if app.root still exists.
    if hasattr(app, 'root') and app.root.winfo_exists():
        main_root.protocol("WM_DELETE_WINDOW", app.on_closing)
        main_root.mainloop()
    else:
        # This case might be hit if the app's internal admin check caused root destruction.
        # Or if the early admin check destroyed it and somehow app object was still made.
        print("Application could not start, likely due to permission issues already handled.")