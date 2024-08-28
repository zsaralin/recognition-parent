const UVCControl = require('uvc-control');

function setCameraControl(vendorId, productId, controlName, value, callback) {
    // Initialize the camera
    let camera = new UVCControl(vendorId, productId, {
        processingUnitId: 0x02,
        camNum: 0,
    });

    function setControl(name, val, cb) {
        camera.set(name, val, function(err) {
            if (err) {
                console.error(`Error setting ${name}:`, err);
            }
            if (cb) cb(err);
        });
    }

    // Setting the control based on the name
    if (controlName === 'absoluteExposureTime') {
        // Set autoExposureMode to 1 (manual) before setting absoluteExposureTime
        setControl('autoExposureMode', 1, function(err) {
            if (err) {
                return callback(err);
            }
            // Now set absoluteExposureTime
            setControl(controlName, value, function(err) {
                if (err) {
                    return callback(err);
                }
                releaseCamera();
                if (callback) callback(null);
            });
        });
    } else {
        // Set other controls directly
        setControl(controlName, value, function(err) {
            if (err) {
                return callback(err);
            }
            releaseCamera();
            if (callback) callback(null);
        });
    }

    // Release the camera after setting the control
    function releaseCamera() {
        camera = null;  // Dereference the camera object
        console.log("Camera released.");
    }
}

module.exports = { setCameraControl };
