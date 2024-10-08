const path = require('path');
const cors = require('cors');
const express = require('express');
const bodyParser = require('body-parser');
const { getDescriptor } = require('./getDescriptor.js');
const { findSimilarImages } = require("./faceMatching.js");
const createSpritesheet = require("./createSpritesheet");
const multer = require('multer');
const {preloadImages} = require('./preloadImages.js')

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
const upload = multer({ storage: multer.memoryStorage() });
app.post('/create-spritesheet', upload.array('frames'), async (req, res) => {
    try {
        console.log('Received request');

        // Ensure req.files is defined and is an array
        if (!req.files || !Array.isArray(req.files)) {
            console.log('Invalid or missing files');
            return res.status(400).json({ error: 'Files not provided or invalid' });
        }

        const frames = req.files.map(file => file.buffer);

        // Ensure req.body.bboxes is defined and is a valid JSON string
        let bboxes;
        try {
            bboxes = JSON.parse(req.body.bboxes);
        } catch (e) {
            console.log('Invalid bboxes JSON');
            return res.status(400).json({ error: 'Invalid bboxes JSON' });
        }

        // Additional check to ensure bboxes is an array
        if (!Array.isArray(bboxes)) {
            console.log('Invalid bboxes array');
            return res.status(400).json({ error: 'Bboxes is not an array' });
        }

        if (frames.length !== bboxes.length) {
            console.log('Frames and bboxes array length mismatch');
            return res.status(400).json({ error: 'Frames and bboxes array length mismatch' });
        }

        console.log('Starting createSpritesheet');

        // Process the spritesheet asynchronously
        await createSpritesheet(frames, bboxes, res);

    } catch (error) {
        console.error('Unexpected error creating spritesheet:', error);
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

