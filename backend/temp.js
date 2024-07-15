const fs = require('fs').promises;
const path = require('path');

async function processFolders(rootDirectory) {
    const directories = await fs.readdir(rootDirectory, { withFileTypes: true });
    for (const directory of directories) {
        if (directory.isDirectory()) {
            const dirPath = path.join(rootDirectory, directory.name);
            await checkAndDeleteSubfolder(dirPath);
        }
    }
    console.log('Processing complete.');
}

async function checkAndDeleteSubfolder(directoryPath) {
    try {
        const files = await fs.readdir(directoryPath, { withFileTypes: true });
        const containsDescriptor = files.some(file => file.isFile() && file.name === 'descriptor.json');

        if (!containsDescriptor) {
            await fs.rm(directoryPath, { recursive: true, force: true });
            console.log(`Deleted ${directoryPath} as it does not contain descriptor.json`);
        } else {
            console.log(`${directoryPath} contains descriptor.json`);
        }
    } catch (error) {
        console.error(`Failed to process ${directoryPath}:`, error);
    }
}

// Example usage
const rootDirectory = '../database0'; // Replace with your root directory path
processFolders(rootDirectory)
    .then(() => console.log('Processing complete.'))
    .catch((error) => console.error('Error processing sprite sheets:', error));