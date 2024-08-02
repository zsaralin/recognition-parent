const sharp = require('sharp');
const { join, resolve, relative } = require("path");
const { promises: fs } = require("fs");
const { extractFirstImageAndGenerateDescriptor } = require("./spriteFR");
const DriveCapacity = require('./driveCapacity');

const checkDriveCapacity = false; // Set this to false to disable the drive capacity check

async function createSpritesheet(frames) {
    try {
        if (checkDriveCapacity) {
            const localRecordingsFolder = resolve(__dirname, '../databases/database0'); // Use forward slashes for Unix-like systems
            const limit = 80; // Set your limit for the disk usage percentage

            const driveCapacity = new DriveCapacity(localRecordingsFolder, limit);

            // Check if the drive is full before proceeding
            const isFull = await driveCapacity.checkCapacity(limit);
            if (isFull) {
                console.log("Drive capacity exceeded, cannot save new spritesheet.");
                return null;
            }
        }

        console.log(frames.length);
        const spritesheetWidth = 1920;
        const maxSpritesheetHeight = 10000;
        const framesPerRow = 19;
        const frameHeight = 100;

        // Calculate the required height for the spritesheet
        const rows = Math.ceil(frames.length / framesPerRow);
        const spritesheetHeight = Math.min(rows * frameHeight, maxSpritesheetHeight);

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
                    .resize(100, 100)
                    .toBuffer()
                    .then(resizedBuffer => {
                        const xPos = (index % framesPerRow) * 100;
                        const yPos = Math.floor(index / framesPerRow) * 100;
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

        // Filter out any null entries due to errors
        const validCompositeInputs = compositeInputs.filter(input => input !== null);

        if (validCompositeInputs.length === 0) {
            console.log('No valid frames to create spritesheet');
            return null;
        }

        spritesheet = await spritesheet.composite(validCompositeInputs).toBuffer();

        console.log('Saving the spritesheet');
        const filePath = await saveSpritesheet(spritesheet, frames.length);
        if (filePath) {
            console.log('Spritesheet saved successfully');
        } else {
            console.log('Failed to save spritesheet');
        }
        return filePath;
    } catch (error) {
        console.error('Error creating spritesheet:', error);
        return null;
    }
}

async function saveSpritesheet(spritesheet, totalFrames) {
    if (totalFrames === 0) {
        console.log('No frames to save, skipping folder creation');
        return null;
    }

    try {
        const now = new Date();
        const folderName = `X#${now.getFullYear()}-${String(now.getMonth() + 1).padStart(2, '0')}-${String(now.getDate()).padStart(2, '0')}-${String(now.getHours()).padStart(2, '0')}-${String(now.getMinutes()).padStart(2, '0')}-${String(now.getSeconds()).padStart(2, '0')}-${String(now.getMilliseconds()).padStart(3, '0')}`;
        const spritesheetFolderPath = resolve(__dirname, '../databases/database0', folderName, 'spritesheet');

        await fs.mkdir(spritesheetFolderPath, { recursive: true });

        const fileName = `${totalFrames}.100.100.jpg`;
        const filePath = join(spritesheetFolderPath, fileName);

        await sharp(spritesheet).jpeg().toFile(filePath);

        const descriptorGenerated = await extractFirstImageAndGenerateDescriptor(filePath);

        if (descriptorGenerated) {
            console.log(`Spritesheet and descriptor saved at: ${filePath}`);
            // Return the relative path instead of the absolute path
            const relativePath = relative(resolve(__dirname, '../databases/database0'), filePath);
            console.log(`Relative path saved: ${relativePath}`);
            return relativePath;
        } else {
            console.log(`No descriptor found. Attempting to clean up ${spritesheetFolderPath}`);
            await fs.rm(spritesheetFolderPath, { recursive: true, force: true });
            console.log(`Cleaned up ${spritesheetFolderPath}`);

            // Verify if the directory was actually removed
            try {
                await fs.access(spritesheetFolderPath);
                console.log(`Directory ${spritesheetFolderPath} still exists.`);
            } catch (err) {
                console.log(`Directory ${spritesheetFolderPath} successfully removed.`);
            }
        }
    } catch (error) {
        console.error('Error saving spritesheet:', error);
    }
    return null;
}

module.exports = createSpritesheet;
