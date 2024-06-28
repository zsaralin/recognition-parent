const sharp = require('sharp');

async function createSpritesheet(images) {
    const spritesheetWidth = 1920;
    const spritesheetHeight = 1200;

    let spritesheet = sharp({
        create: {
            width: spritesheetWidth,
            height: spritesheetHeight,
            channels: 3,
            background: { r: 255, g: 255, b: 255 }
        }
    }).png();

    const imagePromises = images.map((image, index) => {
        const x = (index % 19) * 100;
        const y = Math.floor(index / 19) * 100;
        return {
            input: Buffer.from(image, 'base64'),
            top: y,
            left: x
        };
    });

    spritesheet = await spritesheet.composite(imagePromises).toBuffer();
    await saveSpritesheet(spritesheet, images.length);
}

async function saveSpritesheet(spritesheet, totalFrames) {
    const timestamp = new Date().toISOString().replace(/[:.]/g, '-');
    const folderName = `X#${timestamp}`;
    const spritesheetFolderPath = path.join(__dirname, 'database0', folderName, 'spritesheet');

    await fs.mkdir(spritesheetFolderPath, { recursive: true });

    const fileName = `${totalFrames}.100.100.jpg`;
    const filePath = path.join(spritesheetFolderPath, fileName);

    await sharp(spritesheet).jpeg().toFile(filePath);

    await extractFirstImageAndGenerateDescriptor(filePath);

    return filePath;
}


module.exports = createSpritesheet;
