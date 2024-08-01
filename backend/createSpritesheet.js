const sharp = require('sharp');
const { join, resolve, relative } = require("path");
const { promises: fs } = require("fs");
const { extractFirstImageAndGenerateDescriptor } = require("./spriteFR");

async function createSpritesheet(frames, bboxes) {
    try {
        console.log(frames.length)
        const spritesheetWidth = 1920;
        const spritesheetHeight = 10000;

        let spritesheet = sharp({
            create: {
                width: spritesheetWidth,
                height: spritesheetHeight,
                channels: 3,
                background: { r: 255, g: 255, b: 255 }
            }
        }).png();

        const imagePromises = frames.map(async (frame, index) => {
            const [x, y, w, h] = bboxes[index];

            try {
                const metadata = await sharp(frame).metadata();

                // Ensure the bounding box is square, using width as height
                const size = Math.max(w, h);
                const cx = x + w / 2;
                const cy = y + h / 2;

                // Calculate the new top-left corner to keep the bounding box centered
                const left = Math.max(0, Math.min(cx - size / 2, metadata.width - size));
                const top = Math.max(0, Math.min(cy - size / 2, metadata.height - size));
                const extractWidth = Math.min(size, metadata.width - left);
                const extractHeight = Math.min(size, metadata.height - top);

                return sharp(frame)
                    .extract({ left: Math.round(left), top: Math.round(top), width: Math.round(extractWidth), height: Math.round(extractHeight) })
                    .resize(100, 100)
                    .toBuffer()
                    .then(resizedBuffer => {
                        const xPos = (index % 19) * 100;
                        const yPos = Math.floor(index / 19) * 100;
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
        const spritesheetFolderPath = resolve(__dirname, '../database0', folderName, 'spritesheet');

        await fs.mkdir(spritesheetFolderPath, { recursive: true });

        const fileName = `${totalFrames}.100.100.jpg`;
        const filePath = join(spritesheetFolderPath, fileName);

        await sharp(spritesheet).jpeg().toFile(filePath);

        const descriptorGenerated = await extractFirstImageAndGenerateDescriptor(filePath);

        if (descriptorGenerated) {
            console.log(`Spritesheet and descriptor saved at: ${filePath}`);
            // Return the relative path instead of the absolute path
            const relativePath = relative(resolve(__dirname, '../database0'), filePath);
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
