const UVCControl = require('uvc-control');

let camera = new UVCControl(0x0BDA, 0x3035, {
    processingUnitId: 0x02,
    camNum: 0,
});

function setCameraControl(controlName, value, callback) {
    function setControl(name, val, cb) {
        camera.set(name, val, function(err) {
            if (err) {
                console.error(`Error setting ${name}:`, err);
            }
            if (cb) cb(err);
        });
    }

    if (controlName === 'absoluteExposureTime') {
        // Set autoExposureMode to 1 (manual) before setting absoluteExposureTime
        setControl('autoExposureMode', 1, function(err) {
            if (err) {
                return callback(err);
            }
            // Now set absoluteExposureTime
            setControl(controlName, value, callback);
        });
    } else {
        // Set other controls directly
        setControl(controlName, value, callback);
    }
}

module.exports = { setCameraControl };
