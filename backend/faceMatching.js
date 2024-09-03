const path = require('path');
const fs = require('fs').promises;

async function findSimilarImages(descriptor, numVids) {
    const baseDir = path.resolve('../databases/database0'); // Use absolute path for reliability
    const entries = await fs.readdir(baseDir, { withFileTypes: true });

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
                        .filter(file => path.extname(file).toLowerCase() === '.png') // Filter for PNG files
                        .map(file => {
                            const numImages = parseInt(file.split('.')[0], 10);
                            return {
                                path: entry.name,
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

    // Calculate the actual number of images to use
    const actualNumVids = Math.min(images.length, numVids);

    // Set `mostSimilar` to the first half of the available images, sorted from smallest to largest distance
    let mostSimilar = images.slice(0, Math.ceil(actualNumVids / 2));

    // Set `leastSimilar` to the last half of the available images, sorted from largest to smallest distance
    let leastSimilar = images.slice(-Math.floor(actualNumVids / 2)).reverse();

    // If more images are needed, fill up with duplicates
    const remainingMost = Math.ceil(numVids / 2) - mostSimilar.length;
    const remainingLeast = Math.floor(numVids / 2) - leastSimilar.length;

    if (remainingMost > 0) {
        mostSimilar = mostSimilar.concat(distributeDuplicates(mostSimilar, remainingMost, false));
    }
    if (remainingLeast > 0) {
        leastSimilar = leastSimilar.concat(distributeDuplicates(leastSimilar, remainingLeast, true));
    }

    // Sort the final lists by distance to ensure order
    mostSimilar.sort((a, b) => a.distance - b.distance);
    leastSimilar.sort((a, b) => b.distance - a.distance);  // Reverse order for leastSimilar

    return { mostSimilar: mostSimilar, leastSimilar: leastSimilar };
}

function removeDuplicates(mainArray, otherArray) {
    return mainArray.filter(item1 => !otherArray.some(item2 => item1.path === item2.path));
}

function distributeDuplicates(imageArray, numberOfDuplicates, reverseOrder = false) {
    const duplicates = [];
    const baseIncrement = 0.0001; // Small enough to maintain order
    const increment = reverseOrder ? -baseIncrement : baseIncrement;

    for (let i = 0; i < numberOfDuplicates; i++) {
        const imageIndex = i % imageArray.length;
        const image = imageArray[imageIndex];
        if (image) { // Ensure the image is defined before proceeding
            duplicates.push({
                path: image.path,               // Retain the original path
                numImages: image.numImages,     // Retain the original number of images
                distance: image.distance //+ (i * increment), // Adjust the distance slightly to maintain order
            });
        }
    }
    return duplicates;
}

function euclideanDistance(descriptor1, descriptor2) {
    let sum = 0;
    for (let i = 0; i < descriptor1.length; i++) {
        sum += Math.pow(descriptor1[i] - descriptor2[i], 2);
    }
    return Math.sqrt(sum);
}

module.exports = { findSimilarImages };
