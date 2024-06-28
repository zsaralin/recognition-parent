const fs = require('fs').promises;
const path = require('path');
const {extractFirstImageAndGenerateDescriptor} = require("./spriteFR");
const {DATABASE_DIR} = require("./server.js");

async function generateDescriptorJSONS(directoryPath) {
    const entries = await fs.readdir(directoryPath, { withFileTypes: true });

    // Check if 'descriptor.json' exists in the directory
    if (await descriptorExists(directoryPath)) {
        console.log(`Skipping ${directoryPath}, descriptor.json already exists.`);
        return; // Skip this directory
    }

    for (const entry of entries) {
        const fullPath = path.join(directoryPath, entry.name);
        if (entry.isDirectory()) {
            // Recursively process subdirectories
            await generateDescriptorJSONS(fullPath);
        } else if (entry.isFile() && entry.name.endsWith('.jpg')) {
            // Process each sprite sheet image
            await extractFirstImageAndGenerateDescriptor(fullPath);
        }
    }
}

// Helper function to check if 'descriptor.json' exists in the directory
async function descriptorExists(directory) {
    const files = await fs.readdir(directory);
    return files.includes('descriptor.json');
}


generateDescriptorJSONS('../database/').then(() => {
    console.log('Processing completed.');
}).catch(error => {
    console.error('Error:', error);
});

// async function cleanUpDirectories(directoryPath) {
//     const entries = await fs.readdir(directoryPath, { withFileTypes: true });
//     let subfolders = [];
//
//     console.log(`Checking directory: ${directoryPath}`);
//
//     for (const entry of entries) {
//         const fullPath = path.join(directoryPath, entry.name);
//
//         if (entry.isDirectory()) {
//             // Check only this subdirectory, not recursively
//             const hasDescriptor = await checkDescriptorInFolder(fullPath);
//             if (!hasDescriptor) {
//                 subfolders.push(fullPath); // Collect subfolder for potential deletion
//                 console.log(`Marked for deletion: ${fullPath}`);
//             } else {
//                 console.log(`Descriptor found, preserving: ${fullPath}`);
//             }
//         }
//     }
//
//     // Delete subfolders that do not contain descriptor.json
//     for (const folder of subfolders) {
//         console.log(`Deleting: ${folder}`);
//         await fs.rm(folder, { recursive: true, force: true });
//     }
// }
//
// async function checkDescriptorInFolder(folderPath) {
//     try {
//         const files = await fs.readdir(folderPath);
//         console.log(`Files in ${folderPath}: ${files.join(', ')}`);
//         return files.includes('descriptor.json');
//     } catch (error) {
//         console.error(`Failed to read directory ${folderPath}: ${error}`);
//         return false;
//     }
// }
//
// // Usage
// cleanUpDirectories('../database/')
//     .then(() => {
//         console.log('Cleanup completed.');
//     })
//     .catch(error => {
//         console.error('Error:', error);
//     });