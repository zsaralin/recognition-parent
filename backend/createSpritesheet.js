const sharp = require('sharp');
const { join, resolve, relative } = require("path");
const { promises: fs } = require("fs");
const { extractFirstImageAndGenerateDescriptor } = require("./spriteFR");
const DriveCapacity = require('./driveCapacity');

const checkDriveCapacity = false; // Set this to disable the drive capacity check
const frameWidth = 200; // Set frame width as a constant, used for both width and height
const spritesheetWidth = frameWidth * 19 + 20; // Calculate spritesheet width based on frame width
const framesPerRow = 19;
let min_time_between_spriteshdeets = 1000*60; // 2 minutes in milliseconds

function setTimeBetweenSpritesheets(newValue) {
    min_time_between_spriteshdeets = newValue;
}
let lastSpritesheetCreationTime = 0;

async function createSpritesheet(frames) {
    const currentTime = Date.now();

    if (currentTime - lastSpritesheetCreationTime < min_time_between_spriteshdeets) {
        console.log(`Spritesheet creation skipped: must wait ${min_time_between_spriteshdeets / (1000*16)} minutes between creations.`);
        return null;
    }

    if (checkDriveCapacity) {
        const localRecordingsFolder = resolve(__dirname, '../databases/database0');
        const limit = 80; // Disk usage percentage limit
        const driveCapacity = new DriveCapacity(localRecordingsFolder, limit);
        const isFull = await driveCapacity.checkCapacity(limit);
        if (isFull) {
            console.log("Drive capacity exceeded, cannot save new spritesheet.");
            return null;
        }
    }

    console.log(`Number of frames to process: ${frames.length}`);
    const rows = Math.ceil(frames.length / framesPerRow);
    const spritesheetHeight = rows * frameWidth // Use frameWidth for height calculation

    let spritesheet = sharp({
        create: {
            width: spritesheetWidth,
            height: spritesheetHeight,
            channels: 3,
            background: { r: 255, g: 255, b: 255 }
        }
    }).png();

    const imagePromises = frames.map(async (frame, index) => {
        try {
            return sharp(frame)
                .resize(frameWidth, frameWidth) // Use frameWidth for both width and height
                .toBuffer()
                .then(resizedBuffer => {
                    const xPos = (index % framesPerRow) * frameWidth;
                    const yPos = Math.floor(index / framesPerRow) * frameWidth; // Use frameWidth for height offset calculation
                    return {
                        input: resizedBuffer,
                        top: yPos,
                        left: xPos
                    };
                });
        } catch (error) {
            console.error(`Error processing image ${index + 1}:`, error);
            return null;
        }
    });

    const compositeInputs = await Promise.all(imagePromises);
    const validCompositeInputs = compositeInputs.filter(input => input !== null);
    if (validCompositeInputs.length === 0) {
        console.log('No valid frames to create spritesheet');
        return null;
    }

    spritesheet = await spritesheet.composite(validCompositeInputs).toBuffer();
    console.log('Saving the spritesheet');
    const  [folderName, fileName] = await saveSpritesheet(spritesheet, frames.length);
    if (fileName) {
        console.log('Spritesheet saved successfully');
        lastSpritesheetCreationTime = Date.now();
    } else {
        console.log('Failed to save spritesheet');
    }
    return  [folderName, fileName];
}

async function saveSpritesheet(spritesheet, totalFrames) {
    if (totalFrames === 0) {
        console.log('No frames to save, skipping folder creation');
        return null;
    }

    const now = new Date();
    const folderName = `X#${now.getFullYear()}-${String(now.getMonth() + 1).padStart(2, '0')}-${String(now.getDate()).padStart(2, '0')}-${String(now.getHours()).padStart(2, '0')}-${String(now.getMinutes()).padStart(2, '0')}-${String(now.getSeconds()).padStart(2, '0')}-${String(now.getMilliseconds()).padStart(3, '0')}`;
    const spritesheetFolderPath = resolve(__dirname, '../databases/database0', folderName, 'spritesheet');

    await fs.mkdir(spritesheetFolderPath, { recursive: true });

    const fileName = `${totalFrames}.${frameWidth}.${frameWidth}.jpg`; // Include frameWidth in filename for both dimensions
    const filePath = join(spritesheetFolderPath, fileName);

    await sharp(spritesheet).jpeg().toFile(filePath);

    const descriptorGenerated = await extractFirstImageAndGenerateDescriptor(filePath, frameWidth);
    if (descriptorGenerated) {
        return [folderName, fileName];
    } else {
        console.log(`No descriptor found. Attempting to clean up ${spritesheetFolderPath}`);
        await fs.rm(spritesheetFolderPath, { recursive: true, force: true });
        console.log(`Cleaned up ${spritesheetFolderPath}`);

        try {
            await fs.access(spritesheetFolderPath);
            console.log(`Directory ${spritesheetFolderPath} still exists.`);
        } catch (err) {
            console.log(`Directory ${spritesheetFolderPath} successfully removed.`);
        }
    }
    return null;
}

module.exports = {createSpritesheet, setTimeBetweenSpritesheets};
