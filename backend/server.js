const path = require('path');
const cors = require('cors');
const express = require('express');
const bodyParser = require('body-parser');
const { getDescriptor } = require('./getDescriptor.js');
const { findSimilarImages } = require("./faceMatching.js");
const multer = require('multer');
const {preloadImages} = require('./preloadImages.js')
const {addFrame, clearFrames, noFaceDetected, setMaxFrames, setMinFrames} = require("./framesHandler.js");
// const {setCameraControl} = require("./uvcControl");
const {setTimeBetweenSpritesheets,} = require("./createSpritesheet.js");
const {getRandomImages} = require("./randomImages.js");

const app = express();
app.use(cors());
const port = 3000;
let numVids;

// Middleware to parse JSON bodies
app.use(bodyParser.json({ limit: '50mb' }));

app.post('/grid-info', (req, res) => {
    try {
        const { numVideos } = req.body;
        numVids = numVideos;
        res.json({ message: 'Grid info received successfully' });
    } catch (error) {
        console.error('Error processing grid info:', error);
        res.status(500).json({ error: 'Internal server error' });
    }
});

// Route to receive imageDataURL and return the descriptor
app.post('/get-matches', async (req, res) => {
    try {
        const { image, numVids } = req.body;
        console.log(numVids);

        if (!numVids) {
            return res.status(400).json({ error: 'Number of videos in grid not provided' });
        }

        if (!image) {
            return res.status(400).json({ error: 'No image data provided' });
        }

        const descriptor = await getDescriptor(image);
        if (!descriptor) {
            return res.status(404).json({ error: 'No face detected' });
        }

        const { mostSimilar, leastSimilar } = await findSimilarImages(descriptor, numVids, path.join('database'));
        res.json({ mostSimilar, leastSimilar });
    } catch (error) {
        console.error('Unexpected error processing image:', error);
        res.status(500).json({ error: 'Internal server error' });
    }
});

app.post('/get-random-matches', async (req, res) => {
    try {
        const { numVids } = req.body;

        if (!numVids) {
            return res.status(400).json({ error: 'Number of videos in grid not provided' });
        }

        // Assuming images/videos are stored in 'public/database'
        const databaseDir = path.join(__dirname, 'public', 'database');

        // Get random files from the directory
        const { mostSimilar, leastSimilar } = await getRandomImages(numVids);

        res.json({ mostSimilar, leastSimilar });
    } catch (error) {
        console.error('Unexpected error fetching random matches:', error);
        res.status(500).json({ error: 'Internal server error' });
    }
});

// New route to preload images
app.get('/preload-images', async (req, res) => {
    try {
        const baseDir = path.resolve('../database0'); // Use the appropriate path to your base directory
        const imagePaths = await preloadImages(baseDir);
        res.json({ images: imagePaths });
    } catch (error) {
        console.error('Error preloading images:', error);
        res.status(500).json({ error: 'Internal server error' });
    }
});

app.listen(port, () => {
    console.log(`Server is running on http://localhost:${port}`);
});

app.post('/addFrame', async (req, res) => {
    const { frame, bbox } = req.body;

    try {
        await addFrame(frame, bbox);
        res.status(200).json({ success: true, message: 'Frame added' });
    } catch (error) {
        console.error('Error adding frame:', error);
        res.status(500).json({ success: false, error: error.message });
    }
});

app.post('/noFaceDetected', async (req, res) => {
    try {
        const response = await noFaceDetected();
        res.json(response);
    } catch (error) {
        res.status(500).json({ success: false, message: 'Error creating spritesheet', error });
    }
});

app.post('/set-camera-control', (req, res) => {
    const { controlName, value } = req.body;
    if (!controlName || value === undefined) {
        return res.status(400).send('Missing control name or value');
    }

    setCameraControl(controlName, value, (err) => {
        if (err) {
            console.error(`Error setting ${controlName}:`, err);
            return res.status(500).send(`Error setting ${controlName}`);
        } else {
            return res.send(`${controlName} set to ${value}`);
        }
    });
});

// Single API endpoint to update various settings directly in the route
app.post('/update-setting', (req, res) => {
    const { setting, value } = req.body;

    try {
        // Update the setting based on key-value pair directly within the route
        switch (setting) {
            case 'maxFrames':
                setMaxFrames(value*19);
                break;
            case 'minFrames':
                setMinFrames(value);
                break;
            case 'minTimeBetweenFrames':
                setTimeBetweenSpritesheets(value* 60 * 1000);
                break;
            default:
                throw new Error(`Setting ${setting} is not recognized`);
        }

        // Send a success response
        res.json({ success: true, message: `${setting} updated successfully to ${value}` });
    } catch (error) {
        // Handle any errors that occur during the setting update
        res.status(400).json({ success: false, message: error.message });
    }
});