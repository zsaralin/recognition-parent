const { parentPort } = require('worker_threads');
const sharp = require('sharp');
const path = require('path');
const fs = require('fs').promises;
const { extractFirstImageAndGenerateDescriptor } = require('./spriteFR');
const DriveCapacity = require('./driveCapacity');

const FRAME_WIDTH = 200;
const FRAMES_PER_ROW = 19;
const SPRITESHEET_PADDING = 0; // Adjust as needed

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

    const localRecordingsFolder = path.resolve(__dirname, '../databases/database0');

    if (checkDriveCapacity) {
        const limit = 80; // Percentage threshold
        const driveCapacity = new DriveCapacity(localRecordingsFolder, limit);
        const isFull = await driveCapacity.checkCapacity();
        if (isFull) {
            // Delete the 10 oldest subfolders in database0
            await deleteOldestSubfolders(localRecordingsFolder, 10);
        }
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

                const x = (index % FRAMES_PER_ROW) * FRAME_WIDTH;
                const y = Math.floor(index / FRAMES_PER_ROW) * FRAME_WIDTH;
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

    const saveResult = await saveSpritesheet(spritesheetBuffer, validImages.length, localRecordingsFolder);
    return saveResult;
}

async function deleteOldestSubfolders(directory, count) {
    const subfolders = await fs.readdir(directory, { withFileTypes: true });
    const foldersWithStats = await Promise.all(
        subfolders
            .filter(dirent => dirent.isDirectory())
            .map(async dirent => {
                const fullPath = path.join(directory, dirent.name);
                const stats = await fs.stat(fullPath);
                return { path: fullPath, mtime: stats.mtime };
            })
    );

    const sortedFolders = foldersWithStats.sort((a, b) => a.mtime - b.mtime);
    const foldersToDelete = sortedFolders.slice(0, count);

    for (const folder of foldersToDelete) {
        try {
            await fs.rm(folder.path, { recursive: true, force: true });
            console.log(`Deleted folder: ${folder.path}`);
        } catch (error) {
            console.error(`Failed to delete folder ${folder.path}:`, error);
        }
    }
}

async function saveSpritesheet(spritesheetBuffer, totalFrames, localRecordingsFolder) {
    const now = new Date();
    const folderName = `X#${now.getFullYear()}-${String(now.getMonth() + 1).padStart(2, '0')}-${String(now.getDate()).padStart(2, '0')}-${String(now.getHours()).padStart(2, '0')}-${String(now.getMinutes()).padStart(2, '0')}-${String(now.getSeconds()).padStart(2, '0')}-${String(now.getMilliseconds()).padStart(3, '0')}`;
    const spritesheetFolderPath = path.resolve(localRecordingsFolder, folderName, 'spritesheet');

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
