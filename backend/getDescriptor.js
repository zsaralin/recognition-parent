const tf = require('@tensorflow/tfjs-node');
const faceapi = require('@vladmandic/face-api');

let faceapiInitialized = false;

// Route to handle webcam capture requests
async function getDescriptor(imageDataURL) {
    // Load face-api.js models if not initialized
    if (!faceapiInitialized) {
        await initializeFaceAPI();
        faceapiInitialized = true;
    }

    // Process the image data and generate facial descriptors
    const tensor = await loadImageAsTensor(imageDataURL);
    const detections = await faceapi.detectAllFaces(tensor,  new faceapi.TinyFaceDetectorOptions(({ inputSize: 96 }))).withFaceLandmarks().withFaceDescriptors();
    if(detections && detections[0]) {
        return detections[0].descriptor;
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

        // faceapi.nets.ssdMobilenetv1.loadFromDisk(modelPath),
        // faceapi.nets.ageGenderNet.loadFromDisk(modelPath),
        faceapi.nets.faceLandmark68Net.loadFromDisk(modelPath),
        faceapi.nets.faceRecognitionNet.loadFromDisk(modelPath),
        // faceapi.nets.faceExpressionNet.loadFromDisk(modelPath),
    ]);
    console.log("Models loaded successfully.");

    optionsSSDMobileNet = new faceapi.SsdMobilenetv1Options({ minConfidence, maxResults });
    // console.log("SSD MobileNet options set:", optionsSSDMobileNet);
}

module.exports = {getDescriptor}


