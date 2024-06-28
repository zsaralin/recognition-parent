const canvas = require('canvas');
const {getDescriptor} = require("./getDescriptor");
const fs = require('fs').promises;
const path = require('path');
function computeAverageDescriptor(descriptors) {
    if (descriptors.length === 0) return null;

    const avgDescriptor = new Float32Array(descriptors[0].length);

    descriptors.forEach(descriptor => {
        for (let i = 0; i < descriptor.length; i++) {
            avgDescriptor[i] += descriptor[i];
        }
    });

    for (let i = 0; i < avgDescriptor.length; i++) {
        avgDescriptor[i] /= descriptors.length;
    }

    return avgDescriptor;
}

async function extractFirstImageAndGenerateDescriptor(spritePath) {
    const img = await canvas.loadImage(spritePath);
    const spriteWidth = img.width;
    const spriteHeight = img.height;
    const imageSize = 100;
    const imagesPerRow = 19;
    const tempCanvas = canvas.createCanvas(imageSize, imageSize);
    const ctx = tempCanvas.getContext('2d');
    const descriptors = [];

    for (let y = 0; y < spriteHeight; y += imageSize) {
        for (let x = 0; x < Math.min(spriteWidth, imagesPerRow * imageSize); x += imageSize) {
            // Extract the 100x100 pixels
            ctx.clearRect(0, 0, imageSize, imageSize);
            ctx.drawImage(img, x, y, imageSize, imageSize, 0, 0, imageSize, imageSize);

            // Convert the canvas to a data URL
            const dataURL = tempCanvas.toDataURL();

            // Generate the descriptor
            const descriptor = await getDescriptor(dataURL);
            if (descriptor) {
                descriptors.push(descriptor);
            }
        }
    }

    if (descriptors.length > 0) {
        const avgDescriptor = computeAverageDescriptor(descriptors);
        await saveDescriptor(spritePath, avgDescriptor);
    } else {
        console.log('No descriptors found');
    }

    return null;
}
async function saveDescriptor(spritePath, descriptor) {
    const spriteDir = path.dirname(spritePath); // Directory of the sprite image
    const parentDir = path.resolve(spriteDir, '..'); // Parent directory of the sprite directory
    const outputPath = path.join(parentDir, 'descriptor.json'); // Path for the descriptor.json

    const descriptorArray = Array.from(descriptor); // Convert Float32Array to a regular array
    const descriptorJson = JSON.stringify({ descriptor: descriptorArray }, null, 2); // Format the descriptor as JSON object with key 'descriptor'
    await fs.writeFile(outputPath, descriptorJson); // Save the JSON to the file
    console.log(`Descriptor saved to ${outputPath}`);
}

module.exports={extractFirstImageAndGenerateDescriptor}