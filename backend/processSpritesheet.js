const { createCanvas, loadImage } = require('canvas');
const fs = require('fs-extra');
const path = require('path');
const DriveCapacity = require('./driveCapacity');

// Initialize DriveCapacity instance
const localRecordingsFolder = './database0';  // Use forward slashes for Unix-like systems
const limit = 80; // Set your limit for the disk usage percentage
const driveCapacity = new DriveCapacity(localRecordingsFolder, limit);

async function processSpriteSheets(rootDirectory) {
    const directories = await fs.readdir(rootDirectory, { withFileTypes: true });
    for (const directory of directories) {
        if (directory.isDirectory()) {
            const dirPath = path.join(rootDirectory, directory.name, "spritesheet");
            await extractAndSaveImagesFromSprite(dirPath);
        }
    }
}

async function extractAndSaveImagesFromSprite(directoryPath) {
    try {
        const files = await fs.readdir(directoryPath);
        console.log(`Processing directory: ${directoryPath}`);
        const jpgFiles = files.filter(file => file.endsWith('.jpg'));

        if (jpgFiles.length !== 1) {
            console.log(`Unexpected number of JPG files in ${directoryPath}. Expected exactly one JPG file.`);
            return;
        }

        const spriteSheetFileName = jpgFiles[0];
        const spriteSheetPath = path.join(directoryPath, spriteSheetFileName);
        console.log(`Sprite Sheet Path: ${spriteSheetPath}`);

        const image = await loadImage(spriteSheetPath);
        const imageSize = 100; // Assuming each sprite's height and width is 100 pixels
        const numColumns = Math.floor(image.width / imageSize);
        const numRows = Math.floor(image.height / imageSize);
        const canvas = createCanvas(imageSize, imageSize);
        const ctx = canvas.getContext('2d');

        let numImages = 0; // Initialize the counter for images processed
        let stopProcessing = false;

        for (let y = 0; y < numRows * imageSize && !stopProcessing; y += imageSize) {
            for (let x = 0; x < numColumns * imageSize && !stopProcessing; x += imageSize) {
                ctx.clearRect(0, 0, imageSize, imageSize);
                ctx.drawImage(image, x, y, imageSize, imageSize, 0, 0, imageSize, imageSize);

                if (isPredominantlyWhite(ctx, imageSize)) {
                    console.log(`Predominantly white image detected at position (${x}, ${y}). Stopping further processing.`);
                    stopProcessing = true;
                    break; // Stop processing on first white image
                }

                numImages++; // Increment the counter instead of saving the file

                // Check and handle disk capacity
                await driveCapacity.deleteExcess();
            }
        }

        // After counting, save the number of images to a JSON file
        const infoPath = path.join(directoryPath, 'info.json');
        console.log(`Info JSON Path: ${infoPath}`);
        const infoData = JSON.stringify({ numImages: numImages });
        await fs.writeFile(infoPath, infoData);
        console.log(`Image count saved in info.json: ${numImages}`);

    } catch (error) {
        console.error(`Failed to process sprite sheet at ${directoryPath}:`, error);
    }
}

function isPredominantlyWhite(ctx, size) {
    const imageData = ctx.getImageData(0, 0, size);
    const data = imageData.data;
    const threshold = 250; // White color threshold
    let whiteCount = 0, totalCount = 0;

    for (let i = 0; i < data.length; i += 4) {
        if (data[i] > threshold && data[i + 1] > threshold && data[i + 2] > threshold) {
            whiteCount++;
        }
        totalCount++;
    }

    return (whiteCount / totalCount) > 0.75; // More than 75% of pixels are white
}

const databasePath = path.join('./database0');

processSpriteSheets(databasePath);
