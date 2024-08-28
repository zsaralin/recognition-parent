// const fs = require('fs').promises;
// const path = require('path');
// const sharp = require('sharp');
// const { extractFirstImageAndGenerateDescriptor } = require('./spriteFR');
// const DriveCapacity = require('./driveCapacity');
//
// const frameWidth = 200;
// const framesPerRow = 19;
// const spritesheetWidth = frameWidth * framesPerRow + 20;
//
// async function createAndSaveSpritesheet(frames, checkDriveCapacity) {
//     try {
//         if (checkDriveCapacity) {
//             const localRecordingsFolder = path.resolve(__dirname, '../databases/database0');
//             const limit = 80;
//             const driveCapacity = new DriveCapacity(localRecordingsFolder, limit);
//             const isFull = await driveCapacity.checkCapacity(limit);
//             if (isFull) {
//                 return { error: "Drive capacity exceeded, cannot save new spritesheet." };
//             }
//         }
//
//         const rows = Math.ceil(frames.length / framesPerRow);
//         const spritesheetHeight = rows * frameWidth;
//
//         let spritesheet = sharp({
//             create: {
//                 width: spritesheetWidth,
//                 height: spritesheetHeight,
//                 channels: 3,
//                 background: { r: 255, g: 255, b: 255 }
//             }
//         }).png();
//
//         const imagePromises = frames.map(async (frame, index) => {
//             try {
//                 return sharp(frame)
//                     .resize(frameWidth, frameWidth)
//                     .toBuffer()
//                     .then(resizedBuffer => {
//                         const xPos = (index % framesPerRow) * frameWidth;
//                         const yPos = Math.floor(index / framesPerRow) * frameWidth;
//                         return {
//                             input: resizedBuffer,
//                             top: yPos,
//                             left: xPos
//                         };
//                     });
//             } catch (error) {
//                 return null;
//             }
//         });
//
//         const compositeInputs = await Promise.all(imagePromises);
//         const validCompositeInputs = compositeInputs.filter(input => input !== null);
//
//         if (validCompositeInputs.length === 0) {
//             return { error: 'No valid frames to create spritesheet' };
//         }
//
//         spritesheet = await spritesheet.composite(validCompositeInputs).toBuffer();
//         return await saveSpritesheet(spritesheet, frames.length);
//
//     } catch (error) {
//         return { error: error.message };
//     }
// }
//
// async function saveSpritesheet(spritesheet, totalFrames) {
//     if (totalFrames === 0) {
//         return { error: 'No frames to save, skipping folder creation' };
//     }
//
//     const now = new Date();
//     const folderName = `X#${now.getFullYear()}-${String(now.getMonth() + 1).padStart(2, '0')}-${String(now.getDate()).padStart(2, '0')}-${String(now.getHours()).padStart(2, '0')}-${String(now.getMinutes()).padStart(2, '0')}-${String(now.getSeconds()).padStart(2, '0')}-${String(now.getMilliseconds()).padStart(3, '0')}`;
//     const spritesheetFolderPath = path.resolve(__dirname, '../databases/database0', folderName, 'spritesheet');
//
//     await fs.mkdir(spritesheetFolderPath, { recursive: true });
//
//     const fileName = `${totalFrames}.${frameWidth}.${frameWidth}.jpg`;
//     const filePath = path.join(spritesheetFolderPath, fileName);
//
//     await sharp(spritesheet).jpeg().toFile(filePath);
//
//     const descriptorGenerated = await extractFirstImageAndGenerateDescriptor(filePath, frameWidth);
//     if (descriptorGenerated) {
//         return { folderName, fileName };
//     } else {
//         await fs.rm(spritesheetFolderPath, { recursive: true, force: true });
//         return { error: `Descriptor not generated. Cleaned up ${spritesheetFolderPath}` };
//     }
// }
//
// // Read frames and checkDriveCapacity from the process arguments
// (async () => {
//     const tempFilePath = process.argv[2];
//     const { frames, checkDriveCapacity } = JSON.parse(await fs.readFile(tempFilePath, 'utf-8'));
//
//     const result = await createAndSaveSpritesheet(frames, checkDriveCapacity);
//     console.log(JSON.stringify(result));
// })().catch(error => {
//     console.error(JSON.stringify({ error: error.message }));
// });
