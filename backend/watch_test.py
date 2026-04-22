import watchfiles
import threading
import time

print("Watching for file changes...")
stop_event = threading.Event()

def stop_after():
    time.sleep(10)
    stop_event.set()

threading.Thread(target=stop_after, daemon=True).start()

for changes in watchfiles.watch('.', stop_event=stop_event):
    for change, path in changes:
        print(change.name, path)

print("Done watching.")
