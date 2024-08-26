const fs = require('fs').promises;
const path = require('path');

async function getRandomImages(numVids) {
    const baseDir = path.resolve('../databases/database0');
    const entries = await fs.readdir(baseDir, { withFileTypes: true });
    let directories = entries.filter(entry => entry.isDirectory()).map(dir => dir.name);

    let selectedImages = [];
    while (selectedImages.length < numVids && directories.length > 0) {
        const randomDirIndex = Math.floor(Math.random() * directories.length);
        const selectedDir = directories[randomDirIndex];
        directories.splice(randomDirIndex, 1);  // Remove the selected directory from the list

        const imagesDir = path.join(baseDir, selectedDir, 'spritesheet');
        try {
            const imageFiles = await fs.readdir(imagesDir);
            const jpgFiles = imageFiles.filter(file => path.extname(file).toLowerCase() === '.jpg');

            if (jpgFiles.length > 0) {
                shuffleArray(jpgFiles);
                const selectedFile = jpgFiles[0];
                selectedImages.push({
                    path: selectedDir,  // Use only the directory name, not the full path
                    numImages: parseInt(selectedFile.split('.')[0], 10),
                    distance: Math.random()
                });
            }
        } catch (error) {
            console.error(`Error accessing images in ${imagesDir}:`, error);
        }
    }
    return {
        mostSimilar: selectedImages.slice(0, Math.ceil(numVids / 2)),
        leastSimilar: selectedImages.slice(-Math.ceil(numVids / 2)).reverse()
    };
}

function shuffleArray(array) {
    for (let i = array.length - 1; i > 0; i--) {
        const j = Math.floor(Math.random() * (i + 1));
        [array[i], array[j]] = [array[j], array[i]]; // Shuffle the array
    }
}

module.exports = { getRandomImages };
