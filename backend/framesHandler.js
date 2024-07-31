const createSpritesheet = require("./createSpritesheet.js");

let frames = [];
let bboxes = [];
const maxFrames = 100 * 19; // Set your desired maximum number of frames
const minFrames = 4;
let spritesheetCreated = false;

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
            const filePath = await createSpritesheet(frames, bboxes);
            return { success: !!filePath, filePath };
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

            // Clear frames and bboxes
            clearFrames();

            // Use the copied arrays to create the spritesheet
            const filePath = await createSpritesheet(oldFrames, oldBboxes);
            return { success: !!filePath, filePath };
        } catch (error) {
            console.error('Error creating spritesheet:', error);
            throw error;
        }
    } else {
        clearFrames();
        return { success: false, message: 'Not enough frames to create spritesheet + ' + frames.length };
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
    clearFrames
};
