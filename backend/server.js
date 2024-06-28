const path = require('path');
const cors = require('cors');
const express = require('express');
const bodyParser = require('body-parser');
const { getDescriptor } = require('./getDescriptor.js');
const { findSimilarImages } = require("./faceMatching.js");
const createSpritesheet = require("./createSpritesheet");

const app = express();
app.use(cors())

const port = 3000;
let numVids;

// Middleware to parse JSON bodies
app.use(bodyParser.json({ limit: '50mb' }));

app.post('/grid-info', (req, res) => {
    try {
        const { numVideos } = req.body;
        numVids = numVideos
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
        console.log(numVids)

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

        const { mostSimilar, leastSimilar } = await findSimilarImages(descriptor, numVids, path.join( 'database'));
        res.json({ mostSimilar, leastSimilar });
    } catch (error) {
        console.error('Unexpected error processing image:', error);
        res.status(500).json({ error: 'Internal server error' });
    }
});

app.post('/create-spritesheet', async (req, res) => {
    try {
        const { frames } = req.body;

        if (!frames || !Array.isArray(frames)) {
            return res.status(400).json({ error: 'Frames array not provided or invalid' });
        }

        await createSpritesheet(frames);

        res.set({
            'Content-Type': 'image/png'
        });

    } catch (error) {
        console.error('Unexpected error creating spritesheet:', error);
        res.status(500).json({ error: 'Internal server error' });
    }
});

app.listen(port, () => {
    console.log(`Server is running on http://localhost:${port}`);
});