const path = require('path');
const fs = require('fs').promises;


async function findSimilarImages(descriptor, numVids) {
    const baseDir = path.resolve('../databases/database0'); // Use absolute path for reliability
    const entries = await fs.readdir(baseDir, { withFileTypes: true });
    console.log(`Number of entries in ${baseDir}: ${entries.length}`); // Log the number of entries

    let images = [];
    const promises = entries.map(async (entry) => {
        if (entry.isDirectory()) {
            const descriptorPath = path.join(baseDir, entry.name, 'descriptor.json');
            try {
                const descriptorData = await fs.readFile(descriptorPath, 'utf8');
                const imageDescriptor = JSON.parse(descriptorData).descriptor;

                if (Array.isArray(imageDescriptor) && imageDescriptor.length === descriptor.length) {
                    const distance = euclideanDistance(descriptor, imageDescriptor);
                    const imagesDir = path.join(baseDir, entry.name, 'spritesheet');
                    const imageFiles = await fs.readdir(imagesDir);
                    const imagePath = imageFiles
                        .filter(file => path.extname(file).toLowerCase() === '.jpg') // Filter for JPG files
                        .map(file => {
                            const numImages = parseInt(file.split('.')[0], 10);
                            return {
                                path: path.join('..', 'databases', 'database0', entry.name, 'spritesheet', file),
                                numImages: numImages,
                                distance: distance,
                            };
                        });
                    images = images.concat(imagePath);
                }
            } catch (error) {
                if (error.code !== 'ENOENT') {
                    console.error(`Error reading descriptor or processing files in ${descriptorPath}:`, error);
                }
            }
        }
    });

    await Promise.all(promises);

    // Sort images by distance
    images.sort((a, b) => a.distance - b.distance);

    // Select the top `numVids` most similar images
    const mostSimilar = images.slice(0, numVids);

    // Select the top `numVids` least similar images
    const leastSimilar = images.slice(-numVids).reverse();

    console.log(mostSimilar[0]);
    return { mostSimilar, leastSimilar };
}

function euclideanDistance(descriptor1, descriptor2) {
    let sum = 0;
    for (let i = 0; i < descriptor1.length; i++) {
        sum += Math.pow(descriptor1[i] - descriptor2[i], 2);
    }
    return Math.sqrt(sum);
}

module.exports = { findSimilarImages };
