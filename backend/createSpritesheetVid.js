const sharp = require('sharp');
const { join, resolve, relative } = require("path");
const { promises: fs } = require("fs");
const { extractFirstImageAndGenerateDescriptor } = require("./spriteFR");
const ffmpeg = require('fluent-ffmpeg');

async function createSpritesheetFromVideo(videoPath) {
    try {
        const duration = await getVideoDuration(videoPath);
        if (duration < 5) {
            console.error('Video is shorter than 5 seconds.');
            return null;
        }

        const frames = await extractFramesFromVideo(videoPath, 20); // Extract frames at 20 fps

        if (!Array.isArray(frames) || frames.length === 0) {
            console.error('No frames extracted from video.');
            return null;
        }

        console.log('Extracted frames:', frames);

        // Create bounding boxes for each frame (for simplicity, assume full frame)
        const bboxes = frames.map(() => [8, 0, 64, 64]); // Center crop to 64x64

        const spritesheetPath = await createSpritesheet(frames, bboxes);

        // Clean up the temporary frames directory
        await fs.rm(resolve(__dirname, 'temp_frames'), { recursive: true, force: true });
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
            await fs.rm(outputDir, {recursive: true, force: true});
            console.log('Temporary frames directory cleared.');
        } catch (error) {
            console.error('Error clearing temporary frames directory:', error);
        }
        // Ensure the output directory exists
        fs.mkdir(outputDir, {recursive: true})
            .then(() => {
                console.log(`Output directory created at: ${outputDir}`);

                ffmpeg(videoPath)
                    .output(join(outputDir, 'frame-%04d.png'))
                    .outputOptions(['-vf', `fps=${fps}`])
                    .on('start', (commandLine) => {
                        console.log('FFmpeg process started:', commandLine);
                    })
                    .on('progress', (progress) => {
                        console.log('FFmpeg progress:', progress);
                    })
                    .on('end', async () => {
                        console.log('FFmpeg process completed');
                        try {
                            const files = await fs.readdir(outputDir);
                            for (const file of files) {
                                const framePath = join(outputDir, file);
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

        console.log(frames.length);
        const spritesheetWidth = 1920;
        const maxSpritesheetHeight = 10000;
        const rows = Math.ceil(frames.length / 19);
        const spritesheetHeight = Math.min(rows * 100, maxSpritesheetHeight);

        console.log(`Creating spritesheet with height: ${spritesheetHeight}`);

        let spritesheet = sharp({
            create: {
                width: spritesheetWidth,
                height: spritesheetHeight,
                channels: 3,
                background: { r: 255, g: 255, b: 255 }
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
                    .resize(100, 100)
                    .toBuffer()
                    .then(resizedBuffer => {
                        const xPos = (index % 19) * 100;
                        const yPos = Math.floor(index / 19) * 100;
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
            console.log('Spritesheet saved successfully');
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
        const spritesheetFolderPath = resolve(__dirname, '../database0', folderName, 'spritesheet');

        await fs.mkdir(spritesheetFolderPath, { recursive: true });

        const fileName = `${totalFrames}.100.100.jpg`;
        const filePath = join(spritesheetFolderPath, fileName);

        await sharp(spritesheet).jpeg().toFile(filePath);

        const descriptorGenerated = await extractFirstImageAndGenerateDescriptor(filePath);

        if (descriptorGenerated) {
            console.log(`Spritesheet and descriptor saved at: ${filePath}`);
            // Return the relative path instead of the absolute path
            const relativePath = relative(resolve(__dirname, '../database0'), filePath);
            console.log(`Relative path saved: ${relativePath}`);
            return relativePath;
        } else {
            console.log(`No descriptor found. Attempting to clean up ${spritesheetFolderPath}`);
            await fs.rm(spritesheetFolderPath, { recursive: true, force: true });
            console.log(`Cleaned up ${spritesheetFolderPath}`);

            // Verify if the directory was actually removed
            try {
                await fs.access(spritesheetFolderPath);
                console.log(`Directory ${spritesheetFolderPath} still exists.`);
            } catch (err) {
                console.log(`Directory ${spritesheetFolderPath} successfully removed.`);
            }
        }
    } catch (error) {
        console.error('Error saving spritesheet:', error);
    }
    return null;
}

// Process all .mov files in the specified directory
const movDir = resolve(__dirname, '../movs');

fs.readdir(movDir)
    .then(async files => {
        const movFiles = files.filter(file => file.endsWith('.mov'));
        for (const [index, file] of movFiles.entries()) {
            try {
                const filePath = await createSpritesheetFromVideo(join(movDir, file));
                if (filePath) {
                    console.log(`Spritesheet created for ${index + 1}: ${filePath}`);
                } else {
                    console.log(`Failed to create spritesheet for ${index + 1}`);
                }
            } catch (error) {
                console.error(`Error processing file ${file}:`, error);
            }
        }
    })
    .catch(error => {
        console.error('Error processing .mov files:', error);
    });

module.exports = createSpritesheetFromVideo;
