const UVCControl = require('uvc-control');
let camera =
    new UVCControl(0x0BDA, 0x3035, {
    processingUnitId: 0x02,
    camNum : 0,})


function setCameraControl(controlName, value, callback) {
    camera.set(controlName, value, function(err) {
        if (err) {
            console.error(`Error setting ${controlName}:`, err);
        } else {
        }
        if(callback) callback(err);
    });
}

module.exports = { setCameraControl };
