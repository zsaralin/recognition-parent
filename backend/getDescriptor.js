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

    // Dynamically calculate input sizes based on image size, ensuring multiples of 32
    const smallestDimension = Math.min(tensor.shape[0], tensor.shape[1]);
    const baseSize = Math.floor(smallestDimension / 32) * 32; // Nearest smaller multiple of 32
    const inputSizes = [baseSize, baseSize - 64, baseSize + 32, baseSize + 32].filter(size => size > 0); // Create a range of four sizes

    let detections = null;
    for (const size of inputSizes) {
        detections = await faceapi.detectAllFaces(tensor, new faceapi.TinyFaceDetectorOptions({ inputSize: size }))
            .withFaceLandmarks()
            .withFaceDescriptors();
        if (detections && detections.length > 0) {
            preferredInputSize = size; // Update the preferred input size
            console.log(`Face detected with input size: ${size}`);
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
