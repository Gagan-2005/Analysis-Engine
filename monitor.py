import time
from pathlib import Path

target = Path(r"C:\Users\Meghna Gagan\OneDrive\Desktop\Analysis-Engine\workspace\repositories\Iot-Team-imtiyaz")

def monitor():
    print("Monitoring directory:", target)
    was_empty = not target.exists() or not list(target.iterdir())
    while True:
        try:
            if not target.exists():
                print(f"[{time.strftime('%H:%M:%S')}] Directory does not exist!")
            else:
                files = list(target.iterdir())
                if not files:
                    if not was_empty:
                        print(f"[{time.strftime('%H:%M:%S')}] Directory is now EMPTY! It had files before.")
                        was_empty = True
                else:
                    if was_empty:
                        print(f"[{time.strftime('%H:%M:%S')}] Directory now has files: {len(files)} items.")
                        was_empty = False
        except Exception as e:
            print(f"[{time.strftime('%H:%M:%S')}] Error: {e}")
        time.sleep(1)

if __name__ == "__main__":
    monitor()
