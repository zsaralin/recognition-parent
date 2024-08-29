const UVCControl = require('uvc-control');

let camera = new UVCControl(0x0BDA, 0x3035, {
    processingUnitId: 0x02,
    camNum: 0,
});

let isManualExposureMode = false; // Track the current exposure mode

function setCameraControl(controlName, value, callback) {
    if (controlName === 'autoExposureMode') {
        const isAuto = value === 2; // 2 for automatic, 1 for manual
        camera.set(controlName, value, function(err) {
            if (err) {
                console.error(`Error setting exposure mode to ${isAuto ? 'automatic' : 'manual'}:`, err);
                if (callback) callback(err);
            } else {
                isManualExposureMode = !isAuto;
                console.log(`Exposure mode set to ${isAuto ? 'automatic' : 'manual'}.`);
                if (callback) callback(null);
            }
        });
    } else if (controlName === 'absoluteExposureTime') {
        if (!isManualExposureMode) {
            const error = new Error("Cannot set exposure time because the camera is not in manual mode.");
            console.error(error.message);
            if (callback) callback(error);
            return;
        }

        camera.set(controlName, value, function(err) {
            if (err) {
                console.error("Error setting absoluteExposureTime:", err);
                if (callback) callback(err);
            } else {
                console.log(`Exposure time set to ${value}.`);
                if (callback) callback(null);
            }
        });
    } else {
        // For other camera controls
        camera.set(controlName, value, function(err) {
            if (err) {
                console.error(`Error setting ${controlName}:`, err);
                if (callback) callback(err);
            } else {
                console.log(`${controlName} set to ${value}.`);
                if (callback) callback(null);
            }
        });
    }
}

module.exports = { setCameraControl };
