const path = require('path');
const fs = require('fs').promises;

async function findSimilarImages(descriptor, numVids) {
    console.log(numVids)
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
                        .filter(file => path.extname(file).toLowerCase() === '.png' ||path.extname(file).toLowerCase() === '.jpg' ) // Filter for JPG files
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

    // Select the top `numVids/2` most similar images
    let mostSimilar = images.slice(0, Math.ceil(numVids / 2));
    console.log(images.length)
    // Select the top `numVids/2` least similar images
    let leastSimilar = images.slice(-Math.floor(numVids / 2)).reverse();

    let finalMostSimilar = [...mostSimilar];
    let finalLeastSimilar = [...leastSimilar];

    // Calculate how many more images are needed
    const remainingImagesCount = numVids - (finalMostSimilar.length + finalLeastSimilar.length);

    if (remainingImagesCount > 0) {
        // Determine how many duplicates for each (most similar and least similar)
        const duplicatesForMost = Math.floor(remainingImagesCount / 2);
        const duplicatesForLeast = remainingImagesCount - duplicatesForMost; // Remaining goes to least similar

        // Distribute duplicates among available most similar images
        const mostSimilarDuplicates = distributeDuplicates(mostSimilar, duplicatesForMost);

        // Distribute duplicates among available least similar images
        const leastSimilarDuplicates = distributeDuplicates(leastSimilar, duplicatesForLeast);

        finalMostSimilar = finalMostSimilar.concat(mostSimilarDuplicates);
        finalLeastSimilar = finalLeastSimilar.concat(leastSimilarDuplicates);
    }

    // Ensure that the total number of images is exactly numVids
    finalMostSimilar = finalMostSimilar.slice(0, Math.ceil(numVids / 2));
    finalLeastSimilar = finalLeastSimilar.slice(0, Math.floor(numVids / 2));
    console.log(leastSimilar)
    console.log(mostSimilar)

    return { mostSimilar: finalMostSimilar, leastSimilar: finalLeastSimilar };
}

function distributeDuplicates(imageArray, numberOfDuplicates) {
    const duplicates = [];
    for (let i = 0; i < numberOfDuplicates; i++) {
        const imageIndex = i % imageArray.length;
        duplicates.push({
            ...imageArray[imageIndex],
            distance: generateRandomDistance(imageArray[imageIndex].distance),
        });
    }
    return duplicates;
}

function generateRandomDistance(baseDistance) {
    const variation = (Math.random() - 0.5) * 0.2; // +/- 10% variation
    return baseDistance * (1 + variation);
}

function euclideanDistance(descriptor1, descriptor2) {
    let sum = 0;
    for (let i = 0; i < descriptor1.length; i++) {
        sum += Math.pow(descriptor1[i] - descriptor2[i], 2);
    }
    return Math.sqrt(sum);
}

module.exports = { findSimilarImages };
