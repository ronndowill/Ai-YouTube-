import os
from datetime import datetime

def show_status():
    print("================================")
    print("       TRENDCLIP AI")
    print("================================")
    print("Project is running!")
    print("Date:", datetime.now().strftime("%Y-%m-%d"))
    print("Video automation: In development")
    print("YouTube publishing: Not connected yet")
    print("================================")

if __name__ == "__main__":
    show_status()
