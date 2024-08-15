import sys
import asyncio
from PyQt5.QtWidgets import QApplication
from PyQt5.QtCore import QTimer
from image_app import ImageApp
from image_store import image_store
import config
import os

async def main():
    # Step 1: Preload images
    if config.demo:
        base_dir = "..\\databases\\database0"
    else:
        base_dir = "../databases/database0"

    app = QApplication(sys.argv)
    await asyncio.get_event_loop().run_in_executor(None, image_store.preload_images, app, base_dir)

    # Step 2: Create the Qt Application and the main window
    window = ImageApp()

    # Step 3: Set up a timer for graceful shutdown
    shutdown_timer = QTimer()
    shutdown_timer.setSingleShot(True)
    shutdown_timer.timeout.connect(lambda: force_quit(app))

    # Step 4: Execute the application event loop
    exit_code = app.exec_()

    # Step 5: Start the graceful shutdown process
    print("Initiating graceful shutdown...")
    shutdown_timer.start(5000)  # 5 second timeout for graceful shutdown

    # Attempt graceful shutdown
    await graceful_shutdown(window)

    # If we reach here, graceful shutdown was successful
    shutdown_timer.stop()
    print("Graceful shutdown completed.")

    sys.exit(exit_code)

async def graceful_shutdown(window):
    print("Shutting down application, ensuring all processes are closed.")

    # Stop video processor
    if hasattr(window, 'video_processor') and window.video_processor is not None:
        print("Stopping video processor...")
        window.video_processor.stop()
        await asyncio.get_event_loop().run_in_executor(None, window.video_processor.wait)

    # Stop image loader thread
    if hasattr(window, 'image_loader_thread') and window.image_loader_thread.isRunning():
        print("Stopping image loader thread...")
        window.image_loader_thread.quit()
        await asyncio.get_event_loop().run_in_executor(None, window.image_loader_thread.wait)

    # Close overlay
    if hasattr(window, 'overlay') and window.overlay is not None:
        print("Closing overlay...")
        window.overlay.close()

    # Stop all other threads in NewFaces
    if hasattr(window, 'new_faces'):
        print("Stopping NewFaces threads...")
        window.new_faces.stop_all_threads()

    print("All processes closed.")

def force_quit(app):
    print("Force quitting the application...")
    app.quit()
    os._exit(1)

if __name__ == "__main__":
    asyncio.run(main())