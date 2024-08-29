const { Worker } = require('worker_threads');
const path = require('path');

let min_time_between_spritesheets = 1 * 60 * 1000; // 2 minutes in milliseconds
let lastSpritesheetCreationTime = 0;
let isWorkerBusy = false;
let checkDriveCapacity = true;

// Initialize the worker once
const worker = new Worker(path.resolve(__dirname, 'spritesheetWorker.js'));

// Handle worker errors
worker.on('error', (err) => {
    console.error('Worker encountered an error:', err);
    isWorkerBusy = false; // Reset the busy flag in case of error
});

// Handle unexpected worker exit
worker.on('exit', (code) => {
    if (code !== 0) {
        console.error(`Worker stopped unexpectedly with exit code ${code}`);
    }
    isWorkerBusy = false; // Reset the busy flag
});

function setTimeBetweenSpritesheets(newValue) {
    min_time_between_spritesheets = newValue;
}

async function createSpritesheet(frames) {
    const currentTime = Date.now();

    // Check if enough time has passed since the last spritesheet creation
    if (currentTime - lastSpritesheetCreationTime < min_time_between_spritesheets) {
        console.log(
            `Spritesheet creation skipped: must wait ${min_time_between_spritesheets / (1000 * 60)} minutes between creations.`
        );
        return null;
    }

    // Check if the worker is busy
    if (isWorkerBusy) {
        console.log('Spritesheet creation skipped: worker is currently busy processing another task.');
        return null;
    }

    isWorkerBusy = true; // Mark the worker as busy

    return new Promise((resolve, reject) => {
        const timeout = setTimeout(() => {
            console.error('Worker timed out while processing the task.');
            isWorkerBusy = false;
            resolve(null);
        }, 10 * 60 * 1000); // Set a timeout of 10 minutes

        worker.once('message', (result) => {
            clearTimeout(timeout);
            isWorkerBusy = false; // Mark the worker as idle

            if (result.error) {
                console.error('Error in spritesheet creation:', result.error);
                resolve(null);
            } else {
                console.log('Spritesheet saved successfully');
                console.log('Deleted the following folders:', result.deletedFolders); // Log deleted folders
                lastSpritesheetCreationTime = Date.now();
                resolve(result); // Return the result containing folderName, fileName, and deletedFolders
            }
        });

        worker.postMessage({ frames, checkDriveCapacity });
    });
}

module.exports = { createSpritesheet, setTimeBetweenSpritesheets };
