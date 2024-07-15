const path = require('path');
const fs = require('fs').promises;

async function getAllImagePaths(baseDir) {
    const entries = await fs.readdir(baseDir, { withFileTypes: true });
    let imagePaths = [];

    const promises = entries.map(async (entry) => {
        const fullPath = path.join(baseDir, entry.name);
        if (entry.isDirectory()) {
            const subDirImagePaths = await getAllImagePaths(fullPath);
            imagePaths = imagePaths.concat(subDirImagePaths);
        } else if (entry.isFile() && isImageFile(entry.name)) {
            imagePaths.push(fullPath);
        }
    });

    await Promise.all(promises);
    return imagePaths;
}

function isImageFile(fileName) {
    const validExtensions = ['.jpg', '.jpeg', '.png', '.gif', '.bmp', '.webp'];
    return validExtensions.includes(path.extname(fileName).toLowerCase());
}

async function preloadImages(baseDir) {
    console.time('preloadImages'); // Start the timer

    try {
        const imagePaths = await getAllImagePaths(baseDir);
        console.log(`Total images found: ${imagePaths.length}`);
        console.timeEnd('preloadImages'); // End the timer and log the duration
        return imagePaths;
    } catch (error) {
        console.error('Error preloading images:', error);
        return [];
    }
}

module.exports = { preloadImages };
