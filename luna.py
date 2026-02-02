import speech_recognition as sr
import pyttsx3
import os
import subprocess
import webbrowser
import psutil
import shutil
import pyautogui
import requests
import time
from datetime import datetime
import pytz
import google.generativeai as genai
import sys

try:
    import win32com.client  
except Exception:
    win32com = None
import smtplib
from email.message import EmailMessage

# --- 1. API KEY AND GLOBAL INITIALIZATIONS ---

# CRITICAL FIX: Use the stable, currently recommended model name
MODEL_NAME = 'gemini-2.5-flash' 

try:
    GOOGLE_API_KEY = os.environ.get('GOOGLE_API_KEY')
    if not GOOGLE_API_KEY:
        raise ValueError("Google API key not found. Please set the GOOGLE_API_KEY environment variable.")
    genai.configure(api_key=GOOGLE_API_KEY)
except ValueError as e:
    print(e)
    sys.exit(1) # Use sys.exit(1) for clean failure

try:
    engine = pyttsx3.init('sapi5')
except Exception:
    engine = pyttsx3.init()
recognizer = sr.Recognizer()
recognizer.pause_threshold = 0.6
recognizer.dynamic_energy_threshold = True
recognizer.energy_threshold = 300
try:
    engine.setProperty('rate', 180)
    engine.setProperty('volume', 1.0)
except Exception:
    pass

# --- 2. DEFINE ALL SKILL FUNCTIONS FIRST ---

def speak(text):
    """Converts text to speech."""
    global engine
    print(f"LUNA: {text}")
    try:
        engine.stop()
        engine.say(str(text))
        engine.runAndWait()
    except Exception:
        # Try to re-init engine once if speaking fails
        try:
            try:
                engine = pyttsx3.init('sapi5')
            except Exception:
                engine = pyttsx3.init()
            try:
                engine.setProperty('rate', 180)
                engine.setProperty('volume', 1.0)
            except Exception:
                pass
            engine.say(str(text))
            engine.runAndWait()
        except Exception:
            pass

def calibrate_microphone(duration: float = 1.0):
    """Calibrates ambient noise once to speed up subsequent recognition."""
    try:
        with sr.Microphone() as source:
            recognizer.adjust_for_ambient_noise(source, duration=duration)
    except Exception:
        pass

def get_desktop_path():
    """Finds the correct desktop path, checking for OneDrive."""
    # Path for OneDrive-managed desktop
    onedrive_desktop = os.path.join(os.environ['USERPROFILE'], 'OneDrive', 'Desktop')
    # Standard desktop path
    standard_desktop = os.path.join(os.environ['USERPROFILE'], 'Desktop')

    if os.path.exists(onedrive_desktop):
        return onedrive_desktop
    else:
        return standard_desktop

# --- NEW UTILITY FUNCTION: REFRESH ---
def refresh_desktop():
    """Forces the operating system to refresh the desktop view (F5 on Windows)."""
    try:
        pyautogui.press('f5')
        time.sleep(0.1) 
    except Exception as e:
        print(f"Warning: Could not force desktop refresh. Error: {e}")

# --- NEW FUNCTION: CREATE FOLDER ---
def create_folder(folder_name: str):
    """Creates a new folder (directory) on the desktop."""
    try:
        if not folder_name:
            speak("You need to provide a folder name.")
            return "Failure: No folder name provided."

        desktop_path = get_desktop_path()
        folder_path = os.path.join(desktop_path, folder_name)

        os.makedirs(folder_path, exist_ok=True)
        speak(f"I've created the folder {folder_name} on your desktop.")
        refresh_desktop()
        return f"Folder '{folder_name}' created successfully on the desktop."

    except Exception as e:
        speak(f"Sorry, I couldn't create the folder. Error: {e}")
        return f"Failure: Could not create folder. Error: {e}"

# --- NEW FUNCTION: OPEN FOLDER OR DRIVE ---
def open_folder_or_drive(path: str):
    """Opens a specific folder path, desktop folder, or a drive (e.g., C:)."""
    try:
        path = (path or '').strip()
        
        if not path:
            speak("Please tell me which folder or drive to open.")
            return "Failure: No path or drive specified."

        target_path = path

        # Resolve paths/drives
        if 'desktop' in path.lower() or path.lower() == 'my desktop':
            target_path = get_desktop_path()
        elif (len(path) == 1 and path.isalpha()) or (len(path) == 2 and path.upper().endswith(':')):
            # It's a drive letter (C or C:)
            target_path = f"{path.upper().replace(':', '')}:\\"
        elif not os.path.exists(path):
            # Assume it's a folder on the desktop if not an absolute path
            target_path = os.path.join(get_desktop_path(), path)

        if os.path.exists(target_path):
            subprocess.Popen(['explorer', target_path])
            speak(f"Opening {path} in File Explorer.")
            return f"Successfully opened {path}."
        else:
            speak(f"I couldn't find the folder or drive: {path}.")
            return f"Failure: Path or drive '{path}' not found."

    except Exception as e:
        speak(f"Sorry, I couldn't open that folder or drive. Error: {e}")
        return f"Failure: Could not open folder or drive. Error: {e}"


# --- MODIFIED FUNCTIONS: FILE MANAGEMENT (ADDED REFRESH AND RETURNS) ---

def create_file(filename: str):
    """Creates a file on the desktop, adding .txt if no extension is given."""
    try:
        if not filename:
            speak("You need to provide a filename.")
            return "Failure: No filename provided."
        if '.' not in filename:
            filename += ".txt"
        
        desktop_path = get_desktop_path()
        filepath = os.path.join(desktop_path, filename)
        
        with open(filepath, 'w', encoding='utf-8') as f:
            f.write(f"File '{filename}' created by Luna.")
        speak(f"I've created the file {filename} on your desktop.")
        refresh_desktop()
        return f"File '{filename}' created."
    except Exception as e:
        speak(f"Sorry, I couldn't create the file. Error: {e}")
        return f"Failure: Could not create file. Error: {e}"

def delete_file(filename: str):
    """Deletes a file from the desktop."""
    try:
        if not filename:
            speak("You need to provide a filename to delete.")
            return "Failure: No filename provided."
        desktop_path = get_desktop_path()
        filepath = os.path.join(desktop_path, filename)
        if not os.path.exists(filepath):
            speak(f"I couldn't find {filename} on your desktop.")
            return f"Failure: File '{filename}' not found."
        os.remove(filepath)
        speak(f"Deleted {filename} from your desktop.")
        refresh_desktop()
        return f"File '{filename}' deleted."
    except Exception as e:
        speak(f"Sorry, I couldn't delete the file. Error: {e}")
        return f"Failure: Could not delete file. Error: {e}"

def move_file(filename: str, destination_folder: str):
    """Moves a desktop file into a folder on the desktop (creates folder if needed)."""
    try:
        if not filename or not destination_folder:
            speak("Please provide both a filename and a destination folder.")
            return "Failure: Missing filename or destination folder."
        desktop_path = get_desktop_path()
        source = os.path.join(desktop_path, filename)
        if not os.path.exists(source):
            speak(f"I couldn't find {filename} on your desktop.")
            return f"Failure: File '{filename}' not found."
        dest_dir = os.path.join(desktop_path, destination_folder)
        os.makedirs(dest_dir, exist_ok=True)
        dest = os.path.join(dest_dir, os.path.basename(source))
        shutil.move(source, dest)
        speak(f"Moved {filename} to {destination_folder}.")
        refresh_desktop()
        return f"Moved file '{filename}' to folder '{destination_folder}'."
    except Exception as e:
        speak(f"Sorry, I couldn't move the file. Error: {e}")
        return f"Failure: Could not move file. Error: {e}"

def sort_desktop_files():
    """Sorts desktop files into folders by extension."""
    try:
        desktop_path = get_desktop_path()
        files_moved = 0
        for entry in os.listdir(desktop_path):
            source = os.path.join(desktop_path, entry)
            if os.path.isdir(source):
                continue
            _, ext = os.path.splitext(entry)
            folder = ext[1:].lower() if ext else 'no_extension'
            target_dir = os.path.join(desktop_path, folder)
            os.makedirs(target_dir, exist_ok=True)
            shutil.move(source, os.path.join(target_dir, entry))
            files_moved += 1

        speak("I've sorted files on your desktop by type.")
        refresh_desktop()
        return f"Successfully sorted {files_moved} files on the desktop."
    except Exception as e:
        speak(f"Sorry, I couldn't sort the desktop. Error: {e}")
        return f"Failure: Could not sort desktop. Error: {e}"

# --- UNMODIFIED FUNCTIONS (Return values already added in previous step) ---
def open_application(app_name: str):
    """Opens a common Windows application by name."""
    try:
        app_name_lower = (app_name or '').lower()
        app_map = {
            'notepad': 'notepad.exe',
            'calculator': 'calc.exe',
            'paint': 'mspaint.exe',
            'command prompt': 'cmd.exe',
            'cmd': 'cmd.exe',
            'powershell': 'powershell.exe',
            'explorer': 'explorer.exe',
            'wordpad': 'write.exe',
            'control panel': 'control.exe',
            'task manager': 'taskmgr.exe',
        }
        exe = app_map.get(app_name_lower)
        if exe:
            subprocess.Popen([exe])
            speak(f"Opening {app_name}.")
            return f"Application '{app_name}' opened."
        # Try start if not in map
        subprocess.Popen(["start", app_name], shell=True)
        speak(f"Trying to open {app_name}.")
        return f"Attempted to open application '{app_name}' using start command."
    except Exception as e:
        speak(f"Sorry, I couldn't open {app_name}. Error: {e}")
        return f"Failure: Could not open application. Error: {e}"

def open_website(url_or_query: str):
    """Opens a URL or searches the web if plain text."""
    try:
        query = (url_or_query or '').strip()
        if not query:
            speak("Please tell me what website to open.")
            return "Failure: No URL or query provided."
        if query.startswith('http://') or query.startswith('https://') or '.' in query:
            webbrowser.open(query if query.startswith('http') else f"https://{query}")
            speak("Opening in your browser.")
            return f"Opened website: {query}"
        else:
            webbrowser.open(f"https://www.google.com/search?q={query}")
            speak("Searching the web.")
            return f"Searched web for: {query}"
    except Exception as e:
        speak(f"Sorry, I couldn't open the website. Error: {e}")
        return f"Failure: Could not open website. Error: {e}"

def search_web(query: str):
    try:
        if not query:
            speak("Please tell me what to search for.")
            return "Failure: No search query provided."
        webbrowser.open(f"https://www.google.com/search?q={query}")
        speak(f"Here are results for {query}.")
        return f"Web search initiated for: {query}"
    except Exception as e:
        speak(f"Sorry, I couldn't perform the search. Error: {e}")
        return f"Failure: Could not perform search. Error: {e}"

def send_email(to: str, subject: str, body: str):
    """Sends an email via SMTP using env vars or Outlook fallback."""
    try:
        to = (to or '').strip()
        if not to:
            speak("Please provide a recipient email address.")
            return "Failure: No recipient address provided."
        
        host = os.environ.get('SMTP_HOST')
        port = int(os.environ.get('SMTP_PORT') or 587)
        user = os.environ.get('SMTP_USER')
        password = os.environ.get('SMTP_PASS')
        starttls = os.environ.get('SMTP_STARTTLS', '1') == '1'

        if host and user and password:
            msg = EmailMessage()
            msg['From'] = user
            msg['To'] = to
            msg['Subject'] = subject or ''
            msg.set_content(body or '')

            with smtplib.SMTP(host, port, timeout=30) as server:
                if starttls:
                    server.starttls()
                server.login(user, password)
                server.send_message(msg)
            speak("Email sent via SMTP.")
            return "Email sent successfully via SMTP."

        if win32com is not None:
            try:
                outlook = win32com.Dispatch('Outlook.Application')
                mail = outlook.CreateItem(0)
                mail.To = to
                mail.Subject = subject or ''
                mail.Body = body or ''
                mail.Send()
                speak("Email sent via Outlook.")
                return "Email sent successfully via Outlook."
            except Exception:
                pass

        speak("Email configuration not found. Set SMTP env vars or Outlook.")
        return "Failure: Email configuration not found."
    except Exception as e:
        speak(f"Sorry, I couldn't send the email. Error: {e}")
        return f"Failure: Could not send email. Error: {e}"

def get_system_info():
    """Speaks RAM usage and disk usage for system drive."""
    try:
        memory = psutil.virtual_memory()
        total_gb = memory.total / (1024 ** 3)
        used_gb = (memory.total - memory.available) / (1024 ** 3)
        percent_mem = memory.percent

        drive = os.environ.get('SystemDrive', 'C:')
        disk = psutil.disk_usage(drive + '\\')
        disk_total_gb = disk.total / (1024 ** 3)
        disk_used_gb = disk.used / (1024 ** 3)
        disk_percent = disk.percent

        reply = (
            f"Memory used {used_gb:.1f} of {total_gb:.1f} gigabytes, {percent_mem:.0f} percent. "
            f"Disk {drive} used {disk_used_gb:.1f} of {disk_total_gb:.1f} gigabytes, {disk_percent:.0f} percent."
        )
        speak(reply)
        return reply
    except Exception as e:
        speak(f"Sorry, I couldn't get system info. Error: {e}")
        return f"Failure: Could not get system info. Error: {e}"

def get_time(city: str):
    """Gets the current time for a specified city."""
    city_to_timezone = {
        'dubai': 'Asia/Dubai', 'london': 'Europe/London', 'paris': 'Europe/Paris',
        'new york': 'America/New_York', 'tokyo': 'Asia/Tokyo', 'sydney': 'Australia/Sydney',
        'india': 'Asia/Kolkata'
    }
    try:
        timezone_str = city_to_timezone.get(city.lower())
        if timezone_str:
            city_timezone = pytz.timezone(timezone_str)
            city_time = datetime.now(city_timezone)
            formatted_time = city_time.strftime("%I:%M %p")
            reply = f"The current time in {city.title()} is {formatted_time}."
            speak(reply)
            return reply
        else:
            local_time = datetime.now().strftime("%I:%M %p")
            reply = f"I don't know the timezone for {city}. Your local time is {local_time}."
            speak(reply)
            return reply
    except Exception as e:
        speak(f"Sorry, I couldn't retrieve the time. Error: {e}")
        return f"Failure: {e}"

def get_temperature(city: str):
    """Finds the current temperature for a specified city using the OpenWeatherMap API."""
    try:
        api_key = os.environ.get('OPENWEATHER_API_KEY')
        if not api_key:
            speak("OpenWeatherMap API key not found. Please set the environment variable.")
            return "Failure: API key for weather is not set."

        # API endpoint URL
        url = f"https://api.openweathermap.org/data/2.5/weather?q={city}&appid={api_key}&units=metric"
        
        # Make the request
        response = requests.get(url, timeout=5)
        response.raise_for_status() # Raise an exception for bad status codes (4xx or 5xx)

        # Parse the JSON data
        weather_data = response.json()
        
        if weather_data.get("cod") != 200:
             speak(f"Sorry, I couldn't find the weather for {city}.")
             return f"Failure: City {city} not found."

        main_data = weather_data.get("main", {})
        weather_desc = weather_data.get("weather", [{}])[0].get("description", "no description")
        
        temp = main_data.get("temp")
        feels_like = main_data.get("feels_like")

        if temp is None:
            speak(f"Sorry, I couldn't retrieve the temperature for {city}.")
            return "Failure: Temperature data not available."

        # Format the response
        reply = (f"The current temperature in {city} is {temp:.0f}°C, "
                 f"and it feels like {feels_like:.0f}°C with {weather_desc}.")
        speak(reply)
        return reply

    except requests.exceptions.HTTPError as http_err:
        if response.status_code == 401:
            speak("The weather API key is invalid. Please check it.")
            return "Failure: Invalid API key."
        elif response.status_code == 404:
            speak(f"I couldn't find the city {city}. Please check the spelling.")
            return "Failure: City not found."
        else:
            speak(f"Sorry, an HTTP error occurred while fetching the weather. Error: {http_err}")
            return f"Failure: HTTP error {http_err}"
    except Exception as e:
        speak(f"Sorry, I ran into an error trying to get the temperature. Error: {e}")
        return f"Failure: {e}"

# ... (All your other existing functions like get_system_info, send_email, etc. remain here) ...

# --- 3. CONFIGURE MODELS AND TOOLS (AFTER FUNCTIONS ARE DEFINED) ---

# Model for general conversation with a concise voice-friendly persona
CHAT_SYSTEM_PROMPT = (
    "You are Luna, a helpful desktop voice assistant. Answer clearly and concisely "
    "for spoken output. Prefer short, direct answers (1-3 sentences) unless asked "
    "to explain in detail."
)
# MODEL CHANGE APPLIED HERE
chat_model = genai.GenerativeModel(MODEL_NAME, system_instruction=CHAT_SYSTEM_PROMPT)
chat_session = chat_model.start_chat(history=[])

# Define the tools (our Python functions) for the model
tools = [
    # --- NEW TOOLS ADDED ---
    { "name": "create_folder", "description": "Creates a new folder (directory) on the desktop.", "parameters": { "type": "OBJECT", "properties": { "folder_name": { "type": "STRING", "description": "The name of the new folder." } }, "required": ["folder_name"] } },
    { "name": "open_folder_or_drive", "description": "Opens a specific folder path, or a drive (like C: or D:) in File Explorer.", "parameters": { "type": "OBJECT", "properties": { "path": { "type": "STRING", "description": "The name of the folder, or the drive letter (e.g., 'C drive')." } }, "required": ["path"] } },
    # ----------------------
    { "name": "create_file", "description": "Creates a new file on the desktop.", "parameters": { "type": "OBJECT", "properties": { "filename": { "type": "STRING", "description": "The name of the file." } }, "required": ["filename"] } },
    { "name": "delete_file", "description": "Deletes a file from the desktop.", "parameters": { "type": "OBJECT", "properties": { "filename": { "type": "STRING" } }, "required": ["filename"] } },
    { "name": "move_file", "description": "Moves a desktop file to a folder on desktop.", "parameters": { "type": "OBJECT", "properties": { "filename": { "type": "STRING" }, "destination_folder": { "type": "STRING" } }, "required": ["filename", "destination_folder"] } },
    { "name": "sort_desktop_files", "description": "Sorts desktop files into folders by extension.", "parameters": { "type": "OBJECT", "properties": {} } },
    { "name": "open_application", "description": "Opens a Windows application by name.", "parameters": { "type": "OBJECT", "properties": { "app_name": { "type": "STRING" } }, "required": ["app_name"] } },
    { "name": "open_website", "description": "Opens a website or URL.", "parameters": { "type": "OBJECT", "properties": { "url_or_query": { "type": "STRING" } }, "required": ["url_or_query"] } },
    { "name": "search_web", "description": "Searches the web.", "parameters": { "type": "OBJECT", "properties": { "query": { "type": "STRING" } }, "required": ["query"] } },
    { "name": "send_email", "description": "Sends an email via SMTP or Outlook.", "parameters": { "type": "OBJECT", "properties": { "to": { "type": "STRING" }, "subject": { "type": "STRING" }, "body": { "type": "STRING" } }, "required": ["to"] } },
    { "name": "get_system_info", "description": "Reports RAM and disk usage.", "parameters": { "type": "OBJECT", "properties": {} } },
    { "name": "get_time", "description": "Finds the current time in a city.", "parameters": { "type": "OBJECT", "properties": { "city": { "type": "STRING", "description": "The city name." } }, "required": ["city"] } },
    { "name": "get_temperature", "description": "Gets current temperature for a city (OpenWeatherMap)", "parameters": { "type": "OBJECT", "properties": { "city": { "type": "STRING", "description": "The city name." } }, "required": ["city"] } }
]

# MODEL CHANGE APPLIED HERE
tool_model = genai.GenerativeModel(MODEL_NAME, tools=tools)

# Map tool names to the actual Python functions
available_tools = {
    # --- NEW MAPPINGS ADDED ---
    "create_folder": create_folder,
    "open_folder_or_drive": open_folder_or_drive,
    # --------------------------
    "create_file": create_file,
    "delete_file": delete_file,
    "move_file": move_file,
    "sort_desktop_files": sort_desktop_files,
    "open_application": open_application,
    "open_website": open_website,
    "search_web": search_web,
    "send_email": send_email,
    "get_system_info": get_system_info,
    "get_time": get_time,
    "get_temperature":get_temperature,
}

# --- 4. MAIN LOGIC AND EXECUTION LOOP ---
def speak(text_to_speak):
    """
    Converts text to speech with a fallback to re-initialize the engine
    in case of a conflict with the microphone.
    """
    global engine
    print(f"LUNA: {text_to_speak}")
    try:
        engine.say(str(text_to_speak))
        engine.runAndWait()
    except Exception as e:
        print(f"--- TTS Error: {e}. Attempting to reset engine. ---")
        # --- Fallback Routine ---
        try:
            # Re-initialize the engine
            engine = pyttsx3.init()
            engine.setProperty('rate', 180)
            engine.setProperty('volume', 1.0)
            
            # Retry speaking
            engine.say(str(text_to_speak))
            engine.runAndWait()
        except Exception as e2:
            print(f"--- TTS Fallback Failed: {e2} ---")
            
def listen_for_command():
    """Listens for a command and converts it to text."""
    with sr.Microphone() as source:
        print("Listening for your command...")
        audio = recognizer.listen(source, timeout=10, phrase_time_limit=10)
    try:
        command = recognizer.recognize_google(audio).lower()
        print(f"You said: {command}")
        return command
    except sr.UnknownValueError:
        speak("Sorry, I did not understand that.")
        return None
    except sr.RequestError:
        speak("Sorry, my speech service is down.")
        return None

def handle_local_intents(command: str) -> bool:
    """Fast path for common commands without LLM. Returns True if handled."""
    cmd = command.lower().strip()
    try:
        # --- UPDATED OPEN LOGIC TO HANDLE FOLDERS/DRIVES ---
        if cmd.startswith("open "):
            name = cmd.replace("open ", "", 1).strip()
            
            # Check for drive letter (C, D:, C drive) or explicit path
            is_drive_or_path = (len(name) <= 2 and (name.isalpha() or ':' in name)) or os.path.exists(name) or 'desktop' in name
            
            if is_drive_or_path:
                open_folder_or_drive(name)
                return True
            
            # If it doesn't look like a drive/folder, check for website/application
            if "." in name or name.startswith("http"):
                open_website(name)
            else:
                open_application(name)
            return True
        # --------------------------------------------------
        
        if cmd.startswith("search ") or cmd.startswith("search web for "):
            query = cmd.replace("search web for ", "", 1).replace("search ", "", 1).strip()
            search_web(query)
            return True
            
        # --- NEW FAST PATH ADDED ---
        if cmd.startswith("create folder ") or cmd.startswith("make folder "):
            folder_name = cmd.replace("create folder ", "", 1).replace("make folder ", "", 1).strip()
            create_folder(folder_name)
            return True
        # ---------------------------
        
        if cmd.startswith("create file "):
            filename = cmd.replace("create file ", "", 1).strip()
            create_file(filename)
            return True
        if cmd.startswith("delete file "):
            filename = cmd.replace("delete file ", "", 1).strip()
            delete_file(filename)
            return True
        if cmd.startswith("move file ") and " to " in cmd:
            rest = cmd.replace("move file ", "", 1)
            parts = rest.split(" to ", 1)
            if len(parts) == 2:
                move_file(parts[0].strip(), parts[1].strip())
                return True
        if "sort desktop" in cmd or "sort my desktop" in cmd or "organize desktop" in cmd:
            sort_desktop_files()
            return True
        if "system info" in cmd or "system information" in cmd:
            get_system_info()
            return True
        if cmd.startswith("time in "):
            city = cmd.replace("time in ", "", 1).strip()
            get_time(city)
            return True
        if cmd in ("reset chat", "clear chat", "reset conversation"):
            global chat_session
            chat_session = chat_model.start_chat(history=[])
            speak("Chat history cleared.")
            return True
    except Exception:
        # Fallback to LLM if any local handler fails
        return False
    return False

def process_command(command):
    """
    Handles commands using the generative model's chat session and tools.
    """
    # Guard against empty commands
    if not command or not command.strip():
        return

    # Handle exit commands
    if "goodbye" in command or "exit" in command:
        speak("Goodbye!")
        sys.exit()

    try:
        # Send the user's command to the ongoing chat session
        response = chat_session.send_message(command)
        
        # Loop through the response parts to find and execute any function calls
        for part in response.candidates[0].content.parts:
            # Check if the model is trying to call a function
            if part.function_call:
                function_call = part.function_call
                tool_name = function_call.name
                tool_args = dict(function_call.args)
                
                print(f"-> Calling Tool: {tool_name}({tool_args})")
                
                # Find and execute the correct function from our available tools
                if tool_name in available_tools:
                    result = available_tools[tool_name](**tool_args)
                    
                    # Send the tool's result back to the model
                    response = chat_session.send_message(
                        genai.Part(function_response=genai.protos.FunctionResponse(
                            name=tool_name,
                            response={"result": str(result)} # Send result back as a string
                        ))
                    )

        # After any tool calls, if there is a final text response, speak it
        if response.text and response.text.strip():
            speak(response.text)

    except Exception as e:
        print(f"Error processing command: {e}")
        speak("Sorry, I ran into a little trouble with that request.")

        
def main():
    """The main loop that listens for the wake word."""
    wake_word = "luna"
    speak("Luna is online. Say the wake word to begin.")
    calibrate_microphone(1.0)
    while True:
        print("Listening for wake word...")
        with sr.Microphone() as source:
            try:
                audio = recognizer.listen(source, timeout=10, phrase_time_limit=7)
            except sr.WaitTimeoutError:
                continue
        try:
            transcription = recognizer.recognize_google(audio).lower()
            if wake_word in transcription:
                speak("Yes? How can I help?")
                command = listen_for_command()
                if command:
                    process_command(command)
        except sr.UnknownValueError:
            continue
        except sr.RequestError: 
            print("Could not request results; check your internet connection.")
            time.sleep(5)

if __name__ == "__main__":
    main()