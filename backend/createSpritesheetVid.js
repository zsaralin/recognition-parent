const sharp = require('sharp');
const path = require("path");
const { promises: fs } = require("fs");
const { extractFirstImageAndGenerateDescriptor } = require("./spriteFR");
const ffmpeg = require('fluent-ffmpeg');

// Set the sprite size here (either 100 or 500)
const SPRITE_SIZE = 200;

async function createSpritesheetFromVideo(videoPath) {
    try {
        const duration = await getVideoDuration(videoPath);
        if (duration < 5) {
            console.error('Video is shorter than 5 seconds.');
            return null;
        }

        const frames = await extractFramesFromVideo(videoPath, 10); // Extract frames at 20 fps

        if (!Array.isArray(frames) || frames.length === 0) {
            console.error('No frames extracted from video.');
            return null;
        }

        console.log('Extracted frames:', frames);

        // Create bounding boxes for each frame (for simplicity, assume full frame)
        const bboxes = frames.map(() => [8, 0, SPRITE_SIZE, SPRITE_SIZE]); // Center crop to SPRITE_SIZE x SPRITE_SIZE

        const spritesheetPath = await createSpritesheet(frames, bboxes);

        // Clean up the temporary frames directory
        await fs.rm(path.resolve(__dirname, 'temp_frames'), { recursive: true, force: true });
        console.log('Temporary frames directory deleted.');

        return spritesheetPath;
    } catch (error) {
        console.error('Error creating spritesheet from video:', error);
        return null;
    }
}

async function getVideoDuration(videoPath) {
    return new Promise((resolve, reject) => {
        ffmpeg.ffprobe(videoPath, (err, metadata) => {
            if (err) {
                reject(err);
            } else {
                resolve(metadata.format.duration);
            }
        });
    });
}

async function extractFramesFromVideo(videoPath, fps) {
    return new Promise(async (resolve, reject) => {
        const frames = [];
        const outputDir = './temp_frames';

        // Ensure the output directory exists and is cleared at the start
        try {
            await fs.rm(outputDir, { recursive: true, force: true });
            console.log('Temporary frames directory cleared.');
        } catch (error) {
            console.error('Error clearing temporary frames directory:', error);
        }

        fs.mkdir(outputDir, { recursive: true })
            .then(() => {
                console.log(`Output directory created at: ${outputDir}`);

                ffmpeg(videoPath)
                    .output(path.join(outputDir, 'frame-%04d.png'))
                    .outputOptions(['-vf', `fps=${fps}`])
                    .on('start', (commandLine) => {
                        // console.log('FFmpeg process started:', commandLine);
                    })
                    .on('progress', (progress) => {
                        // console.log('FFmpeg progress:', progress);
                    })
                    .on('end', async () => {
                        console.log('FFmpeg process completed');
                        try {
                            const files = await fs.readdir(outputDir);
                            for (const file of files) {
                                const framePath = path.join(outputDir, file);
                                frames.push(framePath);
                            }
                            if (frames.length === 0) {
                                reject(new Error('No frames extracted.'));
                            } else {
                                resolve(frames);
                            }
                        } catch (error) {
                            reject(error);
                        }
                    })
                    .on('error', (err) => {
                        console.error('FFmpeg error:', err);
                        reject(err);
                    })
                    .run();
            })
            .catch(error => {
                console.error('Error creating output directory:', error);
                reject(error);
            });
    });
}

async function createSpritesheet(frames, bboxes) {
    try {
        if (!Array.isArray(frames)) {
            throw new TypeError('Frames should be an array');
        }

        // Fixed width to hold exactly 19 sprites per row
        const spritesPerRow = 19;
        const spritesheetWidth = SPRITE_SIZE * spritesPerRow;

        // Calculate the number of rows needed and the corresponding height
        const rows = Math.ceil(frames.length / spritesPerRow);
        const spritesheetHeight = rows * SPRITE_SIZE;

        console.log(`Creating spritesheet with dimensions: ${spritesheetWidth}x${spritesheetHeight}`);

        let spritesheet = sharp({
            create: {
                width: spritesheetWidth,
                height: spritesheetHeight,
                channels: 3,
                background: { r: 255, g: 255, b: 255 } // White background
            }
        }).png();

        const imagePromises = frames.map(async (frame, index) => {
            const [x, y, w, h] = bboxes[index];

            try {
                const metadata = await sharp(frame).metadata();

                // Ensure the bounding box is square, using width as height
                const size = Math.max(w, h);
                const cx = x + w / 2;
                const cy = y + h / 2;

                // Calculate the new top-left corner to keep the bounding box centered
                const left = Math.max(0, Math.min(cx - size / 2, metadata.width - size));
                const top = Math.max(0, Math.min(cy - size / 2, metadata.height - size));
                const extractWidth = Math.min(size, metadata.width - left);
                const extractHeight = Math.min(size, metadata.height - top);

                return sharp(frame)
                    .extract({ left: Math.round(left), top: Math.round(top), width: Math.round(extractWidth), height: Math.round(extractHeight) })
                    .resize(SPRITE_SIZE, SPRITE_SIZE)
                    .toBuffer()
                    .then(resizedBuffer => {
                        const xPos = (index % spritesPerRow) * SPRITE_SIZE;
                        const yPos = Math.floor(index / spritesPerRow) * SPRITE_SIZE;
                        return {
                            input: resizedBuffer,
                            top: yPos,
                            left: xPos
                        };
                    });
            } catch (error) {
                console.error(`Error processing image ${index + 1}:`, error);
                return null;
            }
        });

        const compositeInputs = await Promise.all(imagePromises);

        // Filter out any null entries due to errors
        const validCompositeInputs = compositeInputs.filter(input => input !== null);

        if (validCompositeInputs.length === 0) {
            console.log('No valid frames to create spritesheet');
            return null;
        }

        spritesheet = await spritesheet.composite(validCompositeInputs).toBuffer();

        console.log('Saving the spritesheet');
        const filePath = await saveSpritesheet(spritesheet, frames.length);
        if (filePath) {
            console.log(`Spritesheet saved successfully at ${filePath}`);
        } else {
            console.log('Failed to save spritesheet');
        }
        return filePath;
    } catch (error) {
        console.error('Error creating spritesheet:', error);
        return null;
    }
}

async function saveSpritesheet(spritesheet, totalFrames) {
    if (totalFrames === 0) {
        console.log('No frames to save, skipping folder creation');
        return null;
    }

    try {
        const now = new Date();
        const folderName = `X#${now.getFullYear()}-${String(now.getMonth() + 1).padStart(2, '0')}-${String(now.getDate()).padStart(2, '0')}-${String(now.getHours()).padStart(2, '0')}-${String(now.getMinutes()).padStart(2, '0')}-${String(now.getSeconds()).padStart(2, '0')}-${String(now.getMilliseconds()).padStart(3, '0')}`;
        const outerFolderPath = path.resolve(__dirname, '../database1', folderName);
        const spritesheetFolderPath = path.join(outerFolderPath, 'spritesheet');

        await fs.mkdir(spritesheetFolderPath, { recursive: true });

        const fileName = `${totalFrames}.${SPRITE_SIZE}.${SPRITE_SIZE}.jpg`;
        const filePath = path.join(spritesheetFolderPath, fileName);

        await sharp(spritesheet).jpeg().toFile(filePath);

        const descriptorGenerated = await extractFirstImageAndGenerateDescriptor(filePath, SPRITE_SIZE);

        if (descriptorGenerated) {
            console.log(`Spritesheet and descriptor saved at: ${filePath}`);
            const relativePath = path.relative(path.resolve(__dirname, '../database1'), filePath);
            console.log(`Relative path saved: ${relativePath}`);
            return relativePath;
        } else {
            console.log(`No descriptor found. Attempting to clean up ${outerFolderPath}`);

            // Attempt to clean up the outer directory
            await fs.rm(outerFolderPath, { recursive: true, force: true });
            console.log(`Cleaned up ${outerFolderPath}`);

            try {
                await fs.access(outerFolderPath);
                console.log(`Directory ${outerFolderPath} still exists.`);
            } catch (err) {
                console.log(`Directory ${outerFolderPath} successfully removed.`);
            }
        }
    } catch (error) {
        console.error('Error saving spritesheet:', error);
    }
    return null;
}

// Helper function to delete empty subfolders in 'database1'
async function deleteEmptySubfolders(directory) {
    const subfolders = await fs.readdir(directory, { withFileTypes: true });

    for (const subfolder of subfolders) {
        const subfolderPath = path.join(directory, subfolder.name);

        if (subfolder.isDirectory()) {
            const files = await fs.readdir(subfolderPath);

            if (files.length === 0) {
                console.log(`Deleting empty subfolder: ${subfolderPath}`);
                await fs.rmdir(subfolderPath);
            } else {
                // Recursively check subdirectories
                await deleteEmptySubfolders(subfolderPath);
            }
        }
    }
}

// Process all .mov files in the specified directory
const movDir = path.resolve(__dirname, '../videos/celeb-youtube');
const processedLogPath = path.resolve(__dirname, 'processed_videos.log');

// Helper function to check if a video has been processed
async function isProcessed(videoFilePath) {
    try {
        const data = await fs.readFile(processedLogPath, 'utf8');
        const processedVideos = data.split('\n').filter(Boolean);
        return processedVideos.includes(videoFilePath);
    } catch (error) {
        if (error.code === 'ENOENT') {
            // Log file doesn't exist, so no videos have been processed yet
            return false;
        } else {
            throw error;
        }
    }
}

// Helper function to log a processed video
async function logProcessed(videoFilePath) {
    await fs.appendFile(processedLogPath, `${videoFilePath}\n`, 'utf8');
}

fs.readdir(movDir)
    .then(async files => {
        const movFiles = files.filter(file => file.endsWith('.mp4'));

        for (const [index, file] of movFiles.entries()) {

            const videoFilePath = path.join(movDir, file);

            // Check if this video has already been processed
            const alreadyProcessed = await isProcessed(videoFilePath);
            if (alreadyProcessed) {
                console.log(`Skipping already processed video: ${videoFilePath}`);
                continue;
            }

            try {
                const filePath = await createSpritesheetFromVideo(videoFilePath);
                if (filePath) {
                    console.log(`Spritesheet created for ${index + 1}: ${filePath}`);
                    // Log the successfully processed video
                    await logProcessed(videoFilePath);
                } else {
                    console.log(`Failed to create spritesheet for ${index + 1}`);
                }
            } catch (error) {
                console.error(`Error processing file ${file}:`, error);
            }
        }

        // After processing, delete any empty subfolders in 'database1'
        // const databaseDir = path.resolve(__dirname, '../database1');
        // await deleteEmptySubfolders(databaseDir);
    })
    .catch(error => {
        console.error('Error processing .mov files:', error);
    });

module.exports = createSpritesheetFromVideo;
