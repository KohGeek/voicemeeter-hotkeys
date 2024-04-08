import logging
import os
import time

from logging.handlers import RotatingFileHandler
from threading import Event, Thread
from tkinter import Tk
from tkinter.ttk import Frame, Label, Style

import keyboard
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
        self.last_mute = time.time()
        self.last_restart = time.time()

        self.root.after(200, self.update_ui)


    def update_ui(self):
        """
        Toggles the visibility of the overlay window
        """
        if self.restart:
            if self.last_restart < self.last_mute and self.mute:
                self.restart_event.set()
            if self.mute_frame.winfo_ismapped():
                self.mute_frame.grid_forget()
            self.restart_frame.grid(row=0, column=0)
            self.root.deiconify()
        elif self.mute:
            if self.restart_frame.winfo_ismapped():
                self.restart_frame.grid_forget()
            self.mute_frame.grid(row=0, column=0)
            self.root.deiconify()
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
        mute = not mute
        
        if self.mute != self.ui.mute:
            self.ui.last_mute = time.time()
            self.ui.mute = not mute
            Thread(target=self.ui.update_ui).start()

        DISPLAY_EVENT.set()

        LOG.debug(f"Microphone {'muted' if self.mute else 'unmuted'}.")


    def restart_audio(self):
        self.vm.command.restart()
        self.ui.restart = True
        self.ui.last_restart = time.time()
        Thread(target=self.ui.update_ui).start()
        self.restart_event.wait(5)
        self.ui.restart = False
        self.restart_event.clear()

        DISPLAY_EVENT.set()

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
        with vml.api("potato", pdirty=True) as vm:
            restart_event = Event()
            ui = Overlay(TK_ROOT, restart_event)
            vp = VPotato(vm, ui, restart_event)

            vp.check_mute()

            LOG.info("Waiting if mute is active or any hotkey is pressed...")
            DISPLAY_EVENT.wait()

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
    if not os.path.exists("logs"):
        os.makedirs("logs")

    handler = RotatingFileHandler(filename="logs/hotkeys.log", backupCount=5)
    formatter = logging.Formatter("%(asctime)s - %(levelname)s - %(message)s")
    level = logging.DEBUG

    handler.setLevel(level)
    handler.setFormatter(formatter)
    handler.doRollover()
    LOG.addHandler(handler)
    LOG.setLevel(level)


def exit():
    icon.stop()
    keyboard.unhook_all()
    TK_ROOT.quit()


if __name__ == "__main__":

    logging.basicConfig(level=logging.DEBUG)

    TK_ROOT = Tk()
    LOG = logging.getLogger(__name__)
    DISPLAY_EVENT = Event()

    MUTE_HOTKEY = "windows+shift+num 0"
    RESTART_HOTKEY = "windows+shift+pause"

    log_init()

    MUTE_IMG = os.path.abspath(os.path.join(os.path.dirname(__file__), 'img/mute.png'))
    TRAY_IMG = os.path.abspath(os.path.join(os.path.dirname(__file__), 'img/tray.png'))

    menu = pystray.Menu(pystray.MenuItem("Exit", exit))
    icon = pystray.Icon("VB HotKeys", Image.open(TRAY_IMG), "VB Hotkeys", menu=menu)
    icon.run_detached()

    try:
        main()
    except KeyboardInterrupt:
        exit()
        LOG.info("Exiting...")
        raise SystemExit
