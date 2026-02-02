# luna_gui.py
import customtkinter as ctk
import threading
import sys
import speech_recognition as sr
import pyttsx3
import time
from luna import calibrate_microphone, listen_for_command, process_command, speak

# Appearance Settings
ctk.set_appearance_mode("dark")
ctk.set_default_color_theme("blue")

class AssistantApp(ctk.CTk):
    def __init__(self):
        super().__init__()

        self.title("Luna AI Assistant")
        self.geometry("800x600")
        self.protocol("WM_DELETE_WINDOW", self.on_closing)

        # Configure grid layout
        self.grid_columnconfigure(0, weight=1)
        self.grid_rowconfigure(0, weight=1)

        # Log display text box
        self.log_textbox = ctk.CTkTextbox(self, state="disabled", wrap="word", font=("Arial", 14))
        self.log_textbox.grid(row=0, column=0, padx=20, pady=(20, 10), sticky="nsew")

        # Activate button
        self.activate_button = ctk.CTkButton(self, text="Activate Luna", command=self.on_activate_button_click, font=("Arial", 16), height=50)
        self.activate_button.grid(row=1, column=0, padx=20, pady=(10, 20), sticky="ew")
        
        # Initialize the backend and link it to our GUI's log function
        self.log_message("Luna is online. Click the button to give a command.")

    def on_activate_button_click(self):
        """ Starts the assistant's listening cycle in a new thread to keep the GUI responsive. """
        self.activate_button.configure(state="disabled", text="Listening...")
        thread = threading.Thread(target=self.run_assistant_thread)
        thread.daemon = True
        thread.start()

    def run_assistant_thread(self):
        """ The function that runs in the background to handle assistant logic. """
        # Run a single listen -> process cycle
        try:
            speak("Listening...")
            calibrate_microphone(0.8)
            command = listen_for_command()
            if command:
                process_command(command)
        except Exception:
            pass
        self.after(0, self.reset_button) # Schedule button reset on the main thread

    def reset_button(self):
        """ Safely resets the activate button from the main thread. """
        self.activate_button.configure(state="normal", text="Activate Luna")
        
    def log_message(self, message):
        """ Thread-safe method to append a message to the log text box. """
        self.after(0, self._update_log_textbox, message)

    def _update_log_textbox(self, message):
        """ Internal method that performs the actual GUI update on the main thread. """
        self.log_textbox.configure(state="normal")
        self.log_textbox.insert("end", message + "\n\n")
        self.log_textbox.configure(state="disabled")
        self.log_textbox.see("end") # Auto-scroll to the bottom

    def on_closing(self):
        """ Handles the window closing event. """
        self.destroy()
        sys.exit()

if __name__ == "__main__":
    app = AssistantApp()
    app.mainloop()