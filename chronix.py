#!/usr/bin/env python3

"""
Chronix Pomodoro Timer - integrated version with settings and stats
"""

import os
import sys
import json
import datetime

import gi
gi.require_version("Gtk", "3.0")
gi.require_version("Gst", "1.0")
gi.require_version("Notify", "0.7")
from gi.repository import Gtk, GLib, Gst, Notify

import matplotlib
matplotlib.use("GTK3Agg")
from matplotlib.backends.backend_gtk3agg import FigureCanvasGTK3Agg as FigureCanvas
from matplotlib.figure import Figure

# Initialize GStreamer and notifications
Gst.init(None)
Notify.init("Chronix")

# Determine XDG config directory for settings
if 'XDG_CONFIG_HOME' in os.environ:
    config_home = os.environ['XDG_CONFIG_HOME']
else:
    config_home = os.path.join(os.environ['HOME'], '.config')
chronix_dir = os.path.join(config_home, 'chronix')
os.makedirs(chronix_dir, exist_ok=True)
settings_file = os.path.join(chronix_dir, 'settings.json')
stats_file = os.path.join(chronix_dir, 'stats.json')

# Default assets in ./assets relative to script
script_dir = os.path.dirname(os.path.realpath(__file__))
assets_dir = os.path.join(script_dir, 'assets')
if not os.path.isdir(assets_dir):
    assets_dir = script_dir
default_focus_sound = os.path.join(assets_dir, 'focus_end.wav')
default_break_sound = os.path.join(assets_dir, 'break_end.wav')
default_icon = os.path.join(assets_dir, '/assets/icon.png')

# Load or initialize settings
default_settings = {
    "focus_duration": 25,
    "short_break": 5,
    "long_break": 15,
    "sessions_before_long_break": 4,
    "auto_start": False,
    "notification_enabled": True,
    "dark_theme": False,
    "volume": 50,
    "sound": "bell",
    "alarm_focus": "",
    "alarm_short": "",
    "alarm_long": "",
    # Add any other default keys here that your app uses
}
def load_settings():
    try:
        with open("settings.json", "r") as f:
            settings = json.load(f)
    except FileNotFoundError:
        settings = {}

    # Ensure all defaults are present
    for key, value in default_settings  .items():
        settings.setdefault(key, value)

    return settings
if os.path.isfile(settings_file):
    try:
        with open(settings_file) as f:
            settings = json.load(f)
    except Exception as e:
        print("Error loading settings, using defaults:", e)
        settings = default_settings.copy()
else:
    settings = default_settings.copy()

# Load or initialize stats (minutes of focus per day)
if os.path.isfile(stats_file):
    try:
        with open(stats_file) as f:
            stats = json.load(f)
    except Exception as e:
        print("Error loading stats, starting fresh:", e)
        stats = {}
else:
    stats = {}

# Helper to save settings and stats to JSON
def save_settings():
    try:
        with open(settings_file, 'w') as f:
            json.dump(settings, f, indent=2)
    except Exception as e:
        print("Error saving settings:", e)

def save_stats():
    try:
        with open(stats_file, 'w') as f:
            json.dump(stats, f, indent=2)
    except Exception as e:
        print("Error saving stats:", e)

class ChronixTimer(Gtk.Window):
    def __init__(self):
        Gtk.Window.__init__(self, title="Chronix Pomodoro Timer")
        self.set_border_width(10)
        self.set_default_size(400, 300)

        self.focus_count = 0
        self.current_session = "Focus"
        self.remaining = 0
        self.timer_id = None

        # Create Notebook for tabs
        self.notebook = Gtk.Notebook()
        self.add(self.notebook)

        # Timer tab
        self.timer_box = Gtk.VBox(spacing=6)
        self.notebook.append_page(self.timer_box, Gtk.Label(label="Timer"))

        # Stats tab
        self.stats_box = Gtk.VBox(spacing=6)
        self.notebook.append_page(self.stats_box, Gtk.Label(label="Stats"))

        # Settings tab
        self.settings_box = Gtk.VBox(spacing=6)
        self.notebook.append_page(self.settings_box, Gtk.Label(label="Settings"))

        # Build UI in each tab
        self.build_timer_tab()
        self.build_stats_tab()
        self.build_settings_tab()

        # Tray icon
        self.status_icon = None
        self.build_tray_icon()
        self.connect("delete-event", self.on_delete_event)

        # Initial stats chart
        self.update_stats_chart()

    # ========== Timer Tab ==========
    def build_timer_tab(self):
        # Session label (Focus/Break)
        self.session_label = Gtk.Label()
        self.timer_box.pack_start(self.session_label, False, False, 0)
        # Time remaining
        self.time_label = Gtk.Label()
        self.timer_box.pack_start(self.time_label, False, False, 0)
        # Start/Stop button
        self.start_button = Gtk.Button(label="Start")
        self.start_button.connect("clicked", self.on_start_stop)
        self.timer_box.pack_start(self.start_button, False, False, 0)
        # Reset button
        self.reset_button = Gtk.Button(label="Reset")
        self.reset_button.connect("clicked", self.on_reset)
        self.timer_box.pack_start(self.reset_button, False, False, 0)
        # Initialize labels
        self.update_session_label()

    def update_session_label(self):
        text = f"{self.current_session} Session"
        self.session_label.set_text(text)
        # Display default time for the current session
        duration = settings["focus_duration"] * 60 if self.current_session == "Focus" else \
                   settings["short_break"] * 60 if self.current_session == "Short Break" else \
                   settings["long_break"] * 60
        self.update_time_label(duration)

    def update_time_label(self, secs):
        mins = secs // 60
        secs = secs % 60
        self.time_label.set_text(f"{mins:02d}:{secs:02d}")

    def on_start_stop(self, widget):
        if self.timer_id is None:
            # Start timer countdown
            if self.remaining == 0:
                # Set remaining time for new session
                self.remaining = settings["focus_duration"]*60 if self.current_session == "Focus" else \
                                 settings["short_break"]*60 if self.current_session == "Short Break" else \
                                 settings["long_break"]*60
            self.timer_id = GLib.timeout_add_seconds(1, self.on_tick)
            self.start_button.set_label("Stop")
        else:
            # Pause timer
            GLib.source_remove(self.timer_id)
            self.timer_id = None
            self.start_button.set_label("Start")

    def on_reset(self, widget):
        # Reset to initial focus session
        if self.timer_id:
            GLib.source_remove(self.timer_id)
            self.timer_id = None
        self.current_session = "Focus"
        self.focus_count = 0
        self.remaining = 0
        self.update_session_label()
        self.start_button.set_label("Start")

    def on_tick(self):
        if self.remaining > 0:
            self.remaining -= 1
            self.update_time_label(self.remaining)
            return True
        else:
            # End of current session
            self.on_session_end()
            return False

    def on_session_end(self):
        # Handle end of focus or break
        if self.current_session == "Focus":
            self.focus_count += 1
            # Decide next session type (long break every 4th focus)
            if self.focus_count % 4 == 0:
                next_session = "Long Break"
            else:
                next_session = "Short Break"
            # Update stats
            today = datetime.date.today().isoformat()
            stats[today] = stats.get(today, 0) + settings["focus_duration"]
            save_stats()
            # Notify and sound
            notification = Notify.Notification.new("Focus session ended", "Time for a break!", None)
            notification.show()
            self.play_sound(settings.get("focus_sound", default_focus_sound))
        else:
            # End of a break
            next_session = "Focus"
            notification = Notify.Notification.new("Break ended", "Time to focus!", None)
            notification.show()
            self.play_sound(settings.get("break_sound", default_break_sound))

        # Switch session
        self.current_session = next_session
        self.remaining = 0
        self.update_session_label()
        self.start_button.set_label("Start")
        # Auto-start next if enabled
        if settings.get("auto_start", False):
            self.on_start_stop(None)
        # Update stats chart
        self.update_stats_chart()

    def play_sound(self, sound_file):
        if not sound_file:
            return
        try:
            uri = Gst.filename_to_uri(sound_file)
            player = Gst.ElementFactory.make("playbin", "player")
            player.set_property("uri", uri)
            player.set_state(Gst.State.PLAYING)
        except Exception as e:
            print("Error playing sound:", e)

    # ========== Stats Tab ==========
    def build_stats_tab(self):
        # Matplotlib figure for stats
        self.figure = Figure(figsize=(4,3))
        self.ax = self.figure.add_subplot(111)
        self.canvas = FigureCanvas(self.figure)
        sw = Gtk.ScrolledWindow()
        sw.add_with_viewport(self.canvas)
        self.stats_box.pack_start(sw, True, True, 0)

    def update_stats_chart(self):
        # Draw bar chart for last 7 days of focus minutes
        self.ax.clear()
        today = datetime.date.today()
        dates = []
        values = []
        for i in range(6, -1, -1):
            day = today - datetime.timedelta(days=i)
            dates.append(day.strftime("%a"))
            values.append(stats.get(day.isoformat(), 0))
        self.ax.bar(range(len(dates)), values, color='blue')
        self.ax.set_xticks(range(len(dates)))
        self.ax.set_xticklabels(dates)
        self.ax.set_ylabel("Focus minutes")
        self.figure.tight_layout()
        self.canvas.draw()

    # ========== Settings Tab ==========
    def build_settings_tab(self):
        # Focus duration
        hbox = Gtk.HBox(spacing=6)
        self.settings_box.pack_start(hbox, False, False, 0)
        label = Gtk.Label(label="Focus duration (minutes):")
        hbox.pack_start(label, False, False, 0)
        adj_focus = Gtk.Adjustment(settings.get("focus_duration", 25), 1, 120, 1, 10, 0)
        self.spin_focus = Gtk.SpinButton(adjustment=adj_focus, climb_rate=1, digits=0)
        self.spin_focus.connect("value-changed", self.on_focus_changed)
        hbox.pack_start(self.spin_focus, False, False, 0)

        # Short break duration
        hbox2 = Gtk.HBox(spacing=6)
        self.settings_box.pack_start(hbox2, False, False, 0)
        label2 = Gtk.Label(label="Short break (minutes):")
        hbox2.pack_start(label2, False, False, 0)
        adj_short = Gtk.Adjustment(settings.get("short_break", 5), 1, 60, 1, 5, 0)        
        self.spin_short = Gtk.SpinButton(adjustment=adj_short, climb_rate=1, digits=0)
        self.spin_short.connect("value-changed", self.on_short_changed)
        hbox2.pack_start(self.spin_short, False, False, 0)

        # Long break duration
        hbox3 = Gtk.HBox(spacing=6)
        self.settings_box.pack_start(hbox3, False, False, 0)
        label3 = Gtk.Label(label="Long break (minutes):")
        hbox3.pack_start(label3, False, False, 0)
        adj_long = Gtk.Adjustment(settings.get("long_break", 15), 1, 60, 1, 5, 0)
        self.spin_long = Gtk.SpinButton(adjustment=adj_long, climb_rate=1, digits=0)
        self.spin_long.connect("value-changed", self.on_long_changed)
        hbox3.pack_start(self.spin_long, False, False, 0)

        # Auto-start switch
        hbox4 = Gtk.HBox(spacing=6)
        self.settings_box.pack_start(hbox4, False, False, 0)
        label4 = Gtk.Label(label="Auto-start next session:")
        hbox4.pack_start(label4, False, False, 0)
        self.switch_autostart = Gtk.Switch()
        self.switch_autostart.set_active(settings.get("auto_start", False))
        self.switch_autostart.connect("state-set", self.on_autostart_toggled)
        hbox4.pack_start(self.switch_autostart, False, False, 0)

        # Focus end sound chooser
        hbox5 = Gtk.HBox(spacing=6)
        self.settings_box.pack_start(hbox5, False, False, 0)
        label5 = Gtk.Label(label="Focus end sound:")
        hbox5.pack_start(label5, False, False, 0)
        self.filebtn_focus = Gtk.FileChooserButton(title="Select focus end sound", action=Gtk.FileChooserAction.OPEN)
        self.filebtn_focus.set_filename(settings.get("focus_sound", default_focus_sound))
        self.filebtn_focus.connect("file-set", self.on_focus_sound_selected)
        hbox5.pack_start(self.filebtn_focus, True, True, 0)

        # Break end sound chooser
        hbox6 = Gtk.HBox(spacing=6)
        self.settings_box.pack_start(hbox6, False, False, 0)
        label6 = Gtk.Label(label="Break end sound:")
        hbox6.pack_start(label6, False, False, 0)
        self.filebtn_break = Gtk.FileChooserButton(title="Select break end sound", action=Gtk.FileChooserAction.OPEN)
        self.filebtn_break.set_filename(settings.get("break_sound", default_break_sound))
        self.filebtn_break.connect("file-set", self.on_break_sound_selected)
        hbox6.pack_start(self.filebtn_break, True, True, 0)

    # Callbacks for settings changes
    def on_focus_changed(self, widget):
        settings["focus_duration"] = widget.get_value_as_int()
        save_settings()

    def on_short_changed(self, widget):
        settings["short_break"] = widget.get_value_as_int()
        save_settings()

    def on_long_changed(self, widget):
        settings["long_break"] = widget.get_value_as_int()
        save_settings()

    def on_autostart_toggled(self, widget, state):
        settings["auto_start"] = bool(state)
        save_settings()

    def on_focus_sound_selected(self, widget):
        filename = widget.get_filename()
        settings["focus_sound"] = filename
        save_settings()

    def on_break_sound_selected(self, widget):
        filename = widget.get_filename()
        settings["break_sound"] = filename
        save_settings()

    # ========== System Tray Icon ==========
    def build_tray_icon(self):
        try:
            self.status_icon = Gtk.StatusIcon()
            icon_path = default_icon if os.path.isfile(default_icon) else ""
            self.status_icon.set_from_file(icon_path)
            self.status_icon.connect('activate', self.on_tray_left_click)
            self.status_icon.connect('popup-menu', self.on_tray_right_click)
        except Exception as e:
            print("Could not create tray icon:", e)

    def on_tray_left_click(self, icon):
        # Toggle window visibility
        if self.get_visible():
            self.hide()
        else:
            self.show_all()

    def on_tray_right_click(self, icon, button, time):
        menu = Gtk.Menu()
        show_item = Gtk.MenuItem(label="Show/Hide")
        quit_item = Gtk.MenuItem(label="Quit")
        show_item.connect("activate", lambda _: self.on_tray_left_click(icon))
        quit_item.connect("activate", Gtk.main_quit)
        menu.append(show_item)
        menu.append(quit_item)
        show_item.show()
        quit_item.show()
        menu.popup(None, None, None, None, button, time)

    def on_delete_event(self, widget, event):
        # Minimize to tray instead of quitting
        self.hide()
        return True

if __name__ == "__main__":
    win = ChronixTimer()
    win.show_all()
    Gtk.main()
