const {createSpritesheet} = require("./createSpritesheet.js");

let frames = [];
let bboxes = [];
let maxFrames = 60 * 19; // Set your desired maximum number of frames
let minFrames = 16;
let spritesheetCreated = false;

function setMaxFrames(newMax) {
    maxFrames = newMax;
}

function setMinFrames(newMin) {
    minFrames = newMin;
}
async function addFrame(frame, bbox) {
    if (!frame || !bbox) {
        throw new Error('Frame and bbox are required');
    }

    const buffer = dataUrlToBuffer(frame);

    if (frames.length < maxFrames) {
        frames.push(buffer);
        bboxes.push(bbox);
    }

    if (frames.length >= maxFrames && !spritesheetCreated) {
        try {
            spritesheetCreated = true;
            const result = await createSpritesheet(frames, bboxes);
            if (result)
            {
                const {folderName, fileName} = result; // Use object destructuring instead
                return {success: !!folderName, subfolder: folderName, filePath: fileName};
            }
        } catch (error) {
            console.error('Error creating spritesheet:', error);
            throw error;
        }
    }
}

async function noFaceDetected() {
    if (frames.length > minFrames) {
        try {
            // Create copies of frames and bboxes before clearing them
            let oldFrames = [...frames];
            let oldBboxes = [...bboxes];

            // Remove the first four and last four frames and bboxes
            if (oldFrames.length > 8) {
                oldFrames = oldFrames.slice(4, oldFrames.length - 4);
            } else {
                oldFrames = [];
            }

            if (oldBboxes.length > 8) {
                oldBboxes = oldBboxes.slice(4, oldBboxes.length - 4);
            } else {
                oldBboxes = [];
            }

            // Clear frames and bboxes
            clearFrames();

            // Use the modified arrays to create the spritesheet
            const result = await createSpritesheet(oldFrames, oldBboxes);
            if (result) {
                const { folderName, fileName } = result; // Use object destructuring instead
                return { success: !!folderName, subfolder: folderName, filePath: fileName };
                // Proceed with using subfolder and filePath
            } else {
                console.error("Failed to create spritesheet.");
            }
        } catch (error) {
            console.error('Error creating spritesheet:', error);
            throw error;
        }
    } else {
        clearFrames();
        return { success: false, message: 'Not enough frames to create spritesheet. Frames count: ' + frames.length };
    }
}


function clearFrames() {
    frames = [];
    bboxes = [];
    spritesheetCreated = false;
}

function dataUrlToBuffer(dataUrl) {
    const matches = dataUrl.match(/^data:(.+);base64,(.+)$/);
    if (!matches) {
        throw new Error('Invalid data URL');
    }

    const base64Data = matches[2];
    const buffer = Buffer.from(base64Data, 'base64');

    return buffer;
}

module.exports = {
    addFrame,
    noFaceDetected,
    clearFrames,
    setMaxFrames,
    setMinFrames
};
