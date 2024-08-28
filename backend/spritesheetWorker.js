const { parentPort } = require('worker_threads');
const sharp = require('sharp');
const path = require('path');
const fs = require('fs').promises;
const { extractFirstImageAndGenerateDescriptor } = require('./spriteFR');
const DriveCapacity = require('./driveCapacity');

const FRAME_WIDTH = 200;
const FRAMES_PER_ROW = 19;
const SPRITESHEET_PADDING = 20; // Adjust as needed

parentPort.on('message', async (data) => {
    const { frames, checkDriveCapacity } = data;
    try {
        const result = await createAndSaveSpritesheet(frames, checkDriveCapacity);
        parentPort.postMessage(result);
    } catch (error) {
        parentPort.postMessage({ error: error.message });
    }
});

async function createAndSaveSpritesheet(frames, checkDriveCapacity) {
    if (!Array.isArray(frames) || frames.length === 0) {
        throw new Error('Invalid frames data provided.');
    }

    if (checkDriveCapacity) {
        // const localRecordingsFolder = path.resolve(__dirname, '../databases/database0');
        // const limit = 80; // Percentage threshold
        // const driveCapacity = new DriveCapacity(localRecordingsFolder, limit);
        // const isFull = await driveCapacity.checkCapacity();
        // if (isFull) {
        //     throw new Error('Drive capacity exceeded, cannot save new spritesheet.');
        // }
    }

    const rows = Math.ceil(frames.length / FRAMES_PER_ROW);
    const spritesheetWidth = FRAME_WIDTH * FRAMES_PER_ROW + SPRITESHEET_PADDING;
    const spritesheetHeight = FRAME_WIDTH * rows + SPRITESHEET_PADDING;

    const baseImage = sharp({
        create: {
            width: spritesheetWidth,
            height: spritesheetHeight,
            channels: 3,
            background: { r: 255, g: 255, b: 255, alpha: 1 },
        },
    });

    const compositeImages = await Promise.all(
        frames.map(async (frame, index) => {
            try {
                const buffer = await sharp(frame)
                    .resize(FRAME_WIDTH, FRAME_WIDTH)
                    .toBuffer();

                const x = (index % FRAMES_PER_ROW) * FRAME_WIDTH + SPRITESHEET_PADDING / 2;
                const y = Math.floor(index / FRAMES_PER_ROW) * FRAME_WIDTH + SPRITESHEET_PADDING / 2;

                return { input: buffer, top: y, left: x };
            } catch (error) {
                console.error(`Error processing frame at index ${index}:`, error);
                return null;
            }
        })
    );

    const validImages = compositeImages.filter(Boolean);

    if (validImages.length === 0) {
        throw new Error('No valid frames to create spritesheet.');
    }

    const spritesheetBuffer = await baseImage.composite(validImages).jpeg().toBuffer();

    const saveResult = await saveSpritesheet(spritesheetBuffer, validImages.length);
    return saveResult;
}

async function saveSpritesheet(spritesheetBuffer, totalFrames) {
    const now = new Date();
    const timestamp = now.toISOString().replace(/[:.]/g, '-');
    const folderName = `X#${timestamp}`;
    const spritesheetFolderPath = path.resolve(__dirname, '../databases/database0', folderName, 'spritesheet');

    await fs.mkdir(spritesheetFolderPath, { recursive: true });

    const fileName = `${totalFrames}.${FRAME_WIDTH}.${FRAME_WIDTH}.jpg`;
    const filePath = path.join(spritesheetFolderPath, fileName);

    await fs.writeFile(filePath, spritesheetBuffer);

    const descriptorGenerated = await extractFirstImageAndGenerateDescriptor(filePath, FRAME_WIDTH);
    if (!descriptorGenerated) {
        await fs.rm(spritesheetFolderPath, { recursive: true, force: true });
        throw new Error(`Descriptor not generated. Cleaned up ${spritesheetFolderPath}`);
    }

    return { folderName, fileName };
}
