import logging
import os
import subprocess as s
import sys
import time

from logging.handlers import RotatingFileHandler
from threading import Event, Thread
from tkinter import Tk
from tkinter.ttk import Frame, Label, Style

import keyboard
import psutil
import pystray
import voicemeeterlib as vml

from PIL import Image, ImageTk
from voicemeeterlib import error as vmr_error
from voicemeeterlib.remote import Remote

class Overlay:
    """
    Creates an overlay window using tkinter
    Uses the "-topmost" property to always stay on top of other Windows
    """

    start_time = time.time()
    mute = False
    restart = False
    img = None

    last_mute = 0
    last_restart = 0

    def __init__(self, tk_root: Tk, restart_event: Event):
        
        self.root = tk_root
        self.restart_event = restart_event

        self.font_size = 12
        self.img_size = int(self.font_size * 1.8)

        self.style = Style()
        self.style.configure("TLabel", font=('Segoe UI', self.font_size), foreground='gray15')

        self.img = ImageTk.PhotoImage(Image.open(MUTE_IMG).resize((self.img_size, self.img_size),Image.Resampling.LANCZOS))

        child_info = self.root.winfo_children()

        if child_info == []:
            self.init()
        else:
            for child in child_info:
                child.destroy()

        self.mute_frame = Frame(self.root)
        self.restart_frame = Frame(self.root)

        self.mic_mute_draw()
        self.restart_draw()

        self.mute_frame.grid(row=0, column=0)
        self.restart_frame.grid(row=0, column=0)
        init_time = time.time()
        self.last_mute = init_time
        self.last_restart = init_time

        self.root.after(200, self.update_ui)

    
    def vm_event(self, eve):
        if eve == "restart":
            if self.mute_frame.winfo_ismapped():
                self.mute_frame.grid_forget()
            self.restart_frame.grid(row=0, column=0)
        elif eve == "mute":
            if self.restart_frame.winfo_ismapped():
                self.restart_frame.grid_forget()
            self.mute_frame.grid(row=0, column=0)
        self.root.deiconify()


    def update_ui(self):
        """
        Toggles the visibility of the overlay window
        Need to handle:
        - Muted and restarting
            - Muted after restart -> cancel restart window, show mute
            - Restart after mute -> pause mute window, timeout restart window after 5 seconds
        - Muted - show mute window
        - Restarting - show restart window
        - No event -> withdraw window
        """

        if self.mute and self.restart:
            if self.last_restart < self.last_mute:
                self.restart_event.set()
                self.vm_event("mute")
            else:
                self.vm_event("restart")
        elif self.restart:
            self.vm_event("restart")
        elif self.mute:
            self.vm_event("mute")
        else:
            self.root.withdraw()

        self.root.after(100, self.update_ui)


    def mic_mute_draw(self):
        text = "Microphone Muted"

        # Set Up Mute Image
        mute_img = Label(
            self.mute_frame,
            image=self.img,
            style="TLabel",
            anchor="e"
        )
        mute_img.grid(row=0, column=1, pady=8)

        # Set Up Spacers
        spacer1 = Label(
            self.mute_frame,
            text="",
            style="TLabel",
            anchor="center"
        )
        spacer2 = Label(
            self.mute_frame,
            text="",
            style="TLabel",
            anchor="center"
        )
        spacer3 = Label(
            self.mute_frame,
            text="",
            style="TLabel",
            anchor="center"
        )
        spacer1.grid(row=0, column=0, padx=3)
        spacer2.grid(row=0, column=2, padx=1)
        spacer3.grid(row=0, column=4, padx=4)

        # Set up Mute Label
        mute_label = Label(
            self.mute_frame,
            text=text,
            style="TLabel",
            anchor="w"
        )
        mute_label.grid(row=0, column=3, pady=6)

        LOG.info("Mic overlay drawn.")


    def restart_draw(self):
        text = "Restarting audio engine..."

        # Set up restart 
        restart_label = Label(
            self.restart_frame,
            text=text,
            style="TLabel",
            anchor="w"
        )
        restart_label.grid(row=0, column=1, pady=6)

        # Set up spacers
        spacer1 = Label(
            self.restart_frame,
            text="",
            style="TLabel",
            anchor="center"
        )
        spacer2 = Label(
            self.restart_frame,
            text="",
            style="TLabel",
            anchor="center"
        )
        spacer1.grid(row=0, column=0, padx=4)
        spacer2.grid(row=0, column=2, padx=4)

        LOG.info("Restart overlay drawn.")


    def init(self):
        # Define Window Geometry
        self.root.overrideredirect(True)
        self.root.geometry("+10+10")
        self.root.wm_attributes("-topmost", True)
        self.root.wm_attributes("-disabled", True)
        self.root.wm_attributes("-alpha", "0.8")
        self.root.wm_attributes("-toolwindow", True)

        LOG.info("Overlay window initialised.")


class VPotato:

    def __init__(self, vm: Remote, ui: Overlay, restart_event: Event):
        self.vm = vm
        self.ui = ui
        self.restart_event = restart_event

        self.vm.observer.add(self)

        LOG.info("Voicemeeter API initialised.")

        keyboard.add_hotkey(MUTE_HOTKEY, lambda: keyboard.call_later(self.toggle_mute), timeout=0.5)
        keyboard.add_hotkey(RESTART_HOTKEY, lambda: keyboard.call_later(self.restart_audio), timeout=5.0)

        LOG.info("Hotkeys registered.")


    def toggle_mute(self):
        mute = self.vm.bus[5].mute
        self.vm.bus[5].mute = not mute
        if not (self.vm.bus[5].mute == mute):
            mute = not mute

        if self.mute != self.ui.mute:
            self.ui.last_mute = time.time()
            self.ui.mute = not mute
            Thread(target=self.ui.update_ui).start()

        DISPLAY_EVENT.set()

        LOG.debug(f"Microphone {'muted' if self.mute else 'unmuted'}.")


    def restart_audio(self):
        req_time = time.time()
        if (not (req_time - self.ui.last_restart < 3)) or (req_time - self.ui.start_time < 3):
            self.vm.command.restart()
            self.ui.restart = True
            self.ui.last_restart = time.time()
            Thread(target=self.ui.update_ui).start()

            DISPLAY_EVENT.set()

            self.restart_event.wait(3)
            self.ui.restart = False
            self.restart_event.clear()

        LOG.info("Voicemeeter audio engine restarted.")


    def check_mute(self):
        self.mute = self.vm.bus[5].mute

        if self.mute != self.ui.mute:
            self.ui.last_mute = time.time()
            self.ui.mute = self.mute
            Thread(target=self.ui.update_ui).start()

        if self.mute:
            DISPLAY_EVENT.set()


    def on_update(self, event):
        if event == "pdirty":
            self.check_mute()
    


def main():
    try:
        global taskkill
        with vml.api("potato", pdirty=True) as vm:
            restart_event = Event()
            ui = Overlay(TK_ROOT, restart_event)
            vp = VPotato(vm, ui, restart_event)

            vp.check_mute()

            LOG.info("Waiting if mute is active, any hotkey is pressed or program is exited...")
            DISPLAY_EVENT.wait()

            if taskkill:
                LOG.info("Taskkill flag detected. Exiting program...")
                raise SystemExit

            LOG.info("All good! Activating overlay.")

            TK_ROOT.mainloop()
        
        LOG.debug("Exiting main function...")

    except vmr_error.CAPIError:
        LOG.error("Voicemeeter API error. Restarting connection...")
        vm.end_thread()
        vm.logout()
        keyboard.unhook_all()
        main()


def log_init():
    log_pid = None
    past_pid = None
    pid = os.getppid()
    
    if not os.path.exists("logs"):
        os.makedirs("logs")

    if not os.path.exists("logs/hotkeys.pid"):
        with open("logs/hotkeys.pid", "w") as f:
            f.write("")
    
    if not os.path.exists("logs/hotkeys.log"):
        with open("logs/hotkeys.log", "w") as f:
            f.write("First Log\n\n")

    with open("logs/hotkeys.log", "r") as f:
        log_pid = f.readline().split(' ')[-1].strip()
        log_pid = int(log_pid) if log_pid.isnumeric() else log_pid

    with open("logs/hotkeys.pid", "r") as f:
        past_pid = f.read()
        past_pid = int(past_pid) if past_pid.isnumeric() else None
        kill_process(past_pid) if past_pid == log_pid else None
        

    handler = RotatingFileHandler(filename="logs/hotkeys.log", backupCount=5)
    formatter = logging.Formatter("%(asctime)s - %(levelname)s - %(message)s")
    level = logging.DEBUG

    handler.setLevel(level)
    handler.setFormatter(formatter)
    handler.doRollover()
    LOG.addHandler(handler)
    LOG.setLevel(level)

    with open("logs/hotkeys.pid", "w") as f:
        f.write(str(pid))
    
    LOG.info(f"Hotkeys PID: {pid}")
    LOG.debug(f"Logged PID: {log_pid} - Assumed Previous PID: {past_pid}")


def exit():
    global taskkill 
    taskkill = True
    
    DISPLAY_EVENT.set()
    keyboard.unhook_all()
    TK_ROOT.quit()
    
    with open("logs/hotkeys.pid", "w") as f:
        f.write("")

    icon.stop()


def kill_process(pid):
    try:
        p = psutil.Process(pid)
        name = p.name()
        if name != os.path.basename(sys.executable):
            return
        ps = s.Popen(f'taskkill /F /T /PID {format(pid)}', shell=True)
        ps.wait()
        time.sleep(3)
    except psutil.NoSuchProcess:
        LOG.info("PID matches, but no such process found. Continuing...")


if __name__ == "__main__":

    logging.basicConfig(level=logging.DEBUG)

    TK_ROOT = Tk()
    LOG = logging.getLogger(__name__)
    DISPLAY_EVENT = Event()

    MUTE_HOTKEY = "windows+shift+num 0"
    RESTART_HOTKEY = "windows+shift+pause"

    MUTE_IMG = os.path.abspath(os.path.join(os.path.dirname(__file__), 'img/mute.png'))
    TRAY_IMG = os.path.abspath(os.path.join(os.path.dirname(__file__), 'img/tray.png'))

    taskkill = False

    try:
        log_init()

        menu = pystray.Menu(pystray.MenuItem("Exit", exit))
        icon = pystray.Icon("VB HotKeys", Image.open(TRAY_IMG), "VB Hotkeys", menu=menu)
        icon.run_detached()

        main()

    except KeyboardInterrupt:
        LOG.info("Exiting...")
        exit()
        raise SystemExit
