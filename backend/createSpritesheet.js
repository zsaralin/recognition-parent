const sharp = require('sharp');
const { join, resolve } = require("path");
const { promises: fs } = require("fs");
const { extractFirstImageAndGenerateDescriptor } = require("./spriteFR");

async function createSpritesheet(frames, bboxes) {
    const spritesheetWidth = 1920;
    const spritesheetHeight = 1200;

    console.log(`Creating a blank white image of size ${spritesheetWidth}x${spritesheetHeight}`);

    let spritesheet = sharp({
        create: {
            width: spritesheetWidth,
            height: spritesheetHeight,
            channels: 3,
            background: { r: 255, g: 255, b: 255 }
        }
    }).png();

    console.log(`Compositing ${frames.length} images onto the spritesheet`);

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
                    console.log(`Placing image ${index + 1} at position (${xPos}, ${yPos})`);
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

    console.log('Starting the compositing process');
    spritesheet = await spritesheet.composite(validCompositeInputs).toBuffer();
    console.log('Spritesheet compositing complete');

    console.log('Saving the spritesheet');
    await saveSpritesheet(spritesheet, frames.length);
    console.log('Spritesheet saved successfully');
}

async function saveSpritesheet(spritesheet, totalFrames) {
    try {
        const now = new Date();
        const folderName = `X#${now.getFullYear()}-${String(now.getMonth() + 1).padStart(2, '0')}-${String(now.getDate()).padStart(2, '0')}-${String(now.getHours()).padStart(2, '0')}-${String(now.getMinutes()).padStart(2, '0')}-${String(now.getSeconds()).padStart(2, '0')}-${String(now.getMilliseconds()).padStart(3, '0')}`;
        const spritesheetFolderPath = resolve(__dirname, '../database0', folderName, 'spritesheet');

        console.log(`Creating directory: ${spritesheetFolderPath}`);
        await fs.mkdir(spritesheetFolderPath, { recursive: true });

        const fileName = `${totalFrames}.100.100.jpg`;
        const filePath = join(spritesheetFolderPath, fileName);

        console.log(`Saving spritesheet as ${fileName}`);
        await sharp(spritesheet).jpeg().toFile(filePath);

        console.log(`Extracting first image and generating descriptor for ${fileName}`);
        const descriptorGenerated = await extractFirstImageAndGenerateDescriptor(filePath);

        if (descriptorGenerated) {
            console.log(`Spritesheet and descriptor saved at: ${filePath}`);
            return filePath;
        } else {
            // Clean up the created directories if no descriptor was generated
            await fs.rm(spritesheetFolderPath, { recursive: true, force: true });
            console.log(`No descriptor found. Cleaned up ${spritesheetFolderPath}`);
        }
    } catch (error) {
        console.error('Error saving spritesheet:', error);
    }
}

module.exports = createSpritesheet;
