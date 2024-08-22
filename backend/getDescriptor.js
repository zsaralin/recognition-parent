const tf = require('@tensorflow/tfjs-node');
const faceapi = require('@vladmandic/face-api');

let faceapiInitialized = false;
let preferredInputSize = null; // Store the preferred input size after successful detection

// Route to handle webcam capture requests
async function getDescriptor(imageDataURL) {
    // Load face-api.js models if not initialized
    if (!faceapiInitialized) {
        await initializeFaceAPI();
        faceapiInitialized = true;
    }

    // Process the image data and generate facial descriptors
    const tensor = await loadImageAsTensor(imageDataURL);

    const inputSizes = [96, 512, 416, 480, 608, 640]; // Multiples of 32
    let detections = null;

    if (preferredInputSize) {
        // If a preferred input size has been determined, use it
        detections = await faceapi.detectAllFaces(tensor, new faceapi.TinyFaceDetectorOptions({ inputSize: preferredInputSize }))
            .withFaceLandmarks()
            .withFaceDescriptors();
        if (detections && detections[0]) {
            console.log(`Face detected with preferred input size: ${preferredInputSize}`);
            return detections[0].descriptor;
        }
    }

    // Try different input sizes if no preferred size or face not detected with preferred size
    for (const size of inputSizes) {
        detections = await faceapi.detectAllFaces(tensor, new faceapi.TinyFaceDetectorOptions({ inputSize: size }))
            .withFaceLandmarks()
            .withFaceDescriptors();
        if (detections && detections[0]) {
            preferredInputSize = size; // Set this size as the preferred size for future detections
            return detections[0].descriptor;
        }
        console.log(`No face detected with input size: ${size}`);
    }

    return null;
}

// Function to load image data URL as TensorFlow.js tensor
async function loadImageAsTensor(imageDataURL) {
    const buffer = Buffer.from(imageDataURL.split(',')[1], 'base64');
    const tensor = tf.node.decodeImage(buffer, 3);
    return tensor;
}

const minConfidence = 0.5;
const maxResults = 1;
let optionsSSDMobileNet;
// Function to initialize face-api.js
async function initializeFaceAPI() {
    console.log("Setting TensorFlow backend...");
    await faceapi.tf.setBackend('tensorflow');
    await faceapi.tf.ready();
    console.log("TensorFlow backend is ready.");

    const modelPath = './models';
    console.log("Loading models from disk...");
    await Promise.all([
        faceapi.nets.tinyFaceDetector.loadFromDisk(modelPath),
        faceapi.nets.faceLandmark68Net.loadFromDisk(modelPath),
        faceapi.nets.faceRecognitionNet.loadFromDisk(modelPath),
    ]);
    console.log("Models loaded successfully.");

    optionsSSDMobileNet = new faceapi.SsdMobilenetv1Options({ minConfidence, maxResults });
}

module.exports = { getDescriptor };
