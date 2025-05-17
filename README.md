# ⏳ Chronix Pomodoro Timer

Chronix is a full-featured, GTK-based Pomodoro Timer built with Python. It includes productivity tracking, user-configurable settings, sound alerts, system tray integration, and a graph of your focus history.

## 🚀 Features

- Pomodoro technique timer with focus and break sessions
- Auto-start option for next session
- User-configurable durations (focus, short break, long break)
- Session tracking with daily stats visualization
- Sound notifications on session end
- Tray icon with quick control
- Settings persistence via JSON config
- Stats persistence and bar graph via Matplotlib

## 📦 Installation & Setup

### 1. Clone the repository

```bash
git clone https://github.com/yourusername/chronix.git
cd chronix
```
### 2. Set up Python virtual environment

```bash
python3 -m venv venv
source venv/bin/activate
```

### 3. Install required dependencies
Make sure you have GTK and GStreamer development packages installed (for Ubuntu/Debian):

### Debian/Ubuntu:
```bash
sudo apt update
sudo apt install python3-gi python3-gi-cairo gir1.2-gtk-3.0 gir1.2-notify-0.7 gir1.2-gst-plugins-base-1.0 gir1.2-gstreamer-1.0
```
### Fedora:
```bash
sudo dnf install python3-gobject gtk3 pygobject3 gstreamer1 gstreamer1-plugins-base
```

***If you face any issues with sound or GTK bindings, make sure GStreamer and GTK runtime libraries are installed correctly.***

Then install Python dependencies:

```bash
pip install matplotlib PyGObject
```

### 4. Run the application

```bash
python chronix.py
```
***Note: You must have a GUI environment to run GTK apps.***

🧩 Project Structure
chronix/
├── assets/               # Icons, sounds
├── chronix_v4.py         # Main application file
├── settings.json         # Auto-generated settings config
├── stats.json            # Auto-generated stats file
└── README.md

📊 Dependencies

    Python 3.x

    PyGObject (GTK+ 3 bindings)

    GStreamer (audio playback)

    Matplotlib (stats graph)

