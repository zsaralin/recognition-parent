import sys
import asyncio
from PyQt5.QtWidgets import QApplication
from image_app import ImageApp
from backend_communicator import preload_images  # Assume this is the module where preload_images function is defined

async def main():
    # Step 1: Preload images
    preloaded_images = await preload_images()

    # Step 2: Create the Qt Application and the main window
    app = QApplication(sys.argv)
    window = ImageApp(preloaded_images)  # Pass preloaded images to the ImageApp

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
