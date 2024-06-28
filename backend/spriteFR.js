const canvas = require('canvas');
const { getDescriptor } = require('./getDescriptor');
const fs = require('fs').promises;
const path = require('path');

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
            ctx.clearRect(0, 0, imageSize, imageSize);
            ctx.drawImage(img, x, y, imageSize, imageSize, 0, 0, imageSize, imageSize);
            const dataURL = tempCanvas.toDataURL();
            const descriptor = await getDescriptor(dataURL);
            if (descriptor) {
                descriptors.push(descriptor);
            }
        }
    }

    if (descriptors.length > 0) {
        const avgDescriptor = computeAverageDescriptor(descriptors);
        await saveDescriptor(spritePath, avgDescriptor);
        return true;
    } else {
        console.log('No descriptors found');
        return false;
    }
}

async function saveDescriptor(spritePath, descriptor) {
    const spriteDir = path.dirname(spritePath);
    const parentDir = path.resolve(spriteDir, '..');
    const outputPath = path.join(parentDir, 'descriptor.json');
    const descriptorArray = Array.from(descriptor);
    const descriptorJson = JSON.stringify({ descriptor: descriptorArray }, null, 2);
    await fs.writeFile(outputPath, descriptorJson);
    console.log(`Descriptor saved to ${outputPath}`);
}

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

module.exports = { extractFirstImageAndGenerateDescriptor };
