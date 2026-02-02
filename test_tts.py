import pyttsx3

print("Attempting to initialize the text-to-speech engine...")

try:
    engine = pyttsx3.init()
    print("Engine initialized successfully.")

    print("Checking for available voices on your system...")
    voices = engine.getProperty('voices')
    
    if not voices:
        print("\n--- CRITICAL ERROR ---")
        print("No text-to-speech voices were found on your system.")
        print("The 'pyttsx3' library cannot function without them.")
    else:
        print(f"Successfully found {len(voices)} voices.")
        print("The engine appears to be configured correctly.")

        # Final test: make it speak
        engine.say("If you can hear this, the test was successful.")
        print("\nSpeaking a test sentence now...")
        engine.runAndWait()
        print("Test complete.")

except Exception as e:
    print(f"\n--- An error occurred during the test ---")
    print(f"Error details: {e}")