const { createCanvas, loadImage } = require('canvas');
const fs = require('fs-extra');
const path = require('path');

async function processSpriteSheets(rootDirectory) {
    const directories = await fs.readdir(rootDirectory, { withFileTypes: true });
    for (const directory of directories) {
        if (directory.isDirectory()) {
            const dirPath = path.join(rootDirectory, directory.name, "spritesheet");
            await moveInfoJsonOutside(dirPath);
        }
    }
}

async function moveInfoJsonOutside(directoryPath) {
    try {
        const sourcePath = path.join(directoryPath, 'info.json');
        const destPath = path.join(directoryPath, '..', 'info.json');
        await fs.move(sourcePath, destPath, { overwrite: true });
        console.log(`Moved info.json from ${sourcePath} to ${destPath}`);
    } catch (error) {
        if (error.code === 'ENOENT') {
            console.log(`info.json not found in ${directoryPath}`);
        } else {
            console.error(`Failed to move info.json from ${directoryPath}:`, error);
        }
    }
}

const databasePath = path.join('../database0/');
