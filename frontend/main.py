import sys
import asyncio
from PyQt5.QtWidgets import QApplication
from image_app import ImageApp
from image_store import image_store  # Import the global instance
import config

async def main():
    # Step 1: Preload images
    if config.demo:
        base_dir = "..\\databases\\database0"  # Use the demo directory
    else:
        base_dir = "../databases/database0"  # Adjust this path as necessary

    app = QApplication(sys.argv)
    await asyncio.get_event_loop().run_in_executor(None, image_store.preload_images, app, base_dir)

    # Step 2: Create the Qt Application and the main window
    window = ImageApp()  # No need to pass preloaded images, they are in the ImageStore

    # Step 3: Execute the application event loop
    exit_code = app.exec_()

    # Step 4: Ensure all threads are stopped properly before exiting
    print("Shutting down application, ensuring all processes are closed.")
    if hasattr(window, 'video_processor'):
        window.video_processor.stop()
        window.video_processor.wait()

    if hasattr(window, 'image_loader_thread') and window.image_loader_thread.isRunning():
        window.image_loader_thread.quit()
        window.image_loader_thread.wait()

    if hasattr(window, 'overlay') and window.overlay is not None:
        window.overlay.close()

    sys.exit(exit_code)

if __name__ == "__main__":
    asyncio.run(main())
