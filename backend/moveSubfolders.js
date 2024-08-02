const fs = require('fs').promises;
const path = require('path');

async function moveFolders(baseDir, prefix) {
    const database0 = path.join(baseDir, 'database0');
    const database1 = path.join(baseDir, 'database1');

    try {
        // Create the database1 directory if it doesn't exist
        await fs.mkdir(database1, { recursive: true });

        // Read all items in the database0 directory
        const items = await fs.readdir(database0, { withFileTypes: true });

        for (const item of items) {
            if (item.isDirectory() && !item.name.startsWith(prefix)) {
                const oldPath = path.join(database0, item.name);
                const newPath = path.join(database1, item.name);

                // Move the directory
                await fs.rename(oldPath, newPath);
                console.log(`Moved folder: ${item.name}`);
            }
        }

        console.log('Move operation completed.');
    } catch (error) {
        console.error('Error moving folders:', error);
    }
}

// Example usage
const baseDir = path.resolve(__dirname, '..'); // Adjust the base directory path as needed
const prefix = 'X#2024-08-01'; // The prefix to exclude

moveFolders(baseDir, prefix);
