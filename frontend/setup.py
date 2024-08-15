from setuptools import setup

APP = ['main.py']
OPTIONS = {
    'argv_emulation': True,
    'packages': ['PyQt5', 'cv2', 'requests', 'mediapipe', 'httpx'],
    'plist': {
        'NSCameraUsageDescription': 'This app requires access to the camera.'
    },
}

setup(
    app=APP,
    options={'py2app': OPTIONS},
    setup_requires=['py2app'],
)


# add to info.plist :
# <key>NSCameraUsageDescription</key>
# <string>This app requires access to the camera.</string>