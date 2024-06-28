import sys
from PyQt5.QtWidgets import QApplication
from image_app import ImageApp

if __name__ == "__main__":
    app = QApplication(sys.argv)
    window = ImageApp()
    window.show()
    exit_code = app.exec_()  # Capture the exit code when the app closes

    # Ensure all threads are stopped properly before exiting
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
