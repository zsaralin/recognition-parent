const fs = require('fs').promises;
const path = require('path');
const { exec } = require('child_process');

class DriveCapacity {
    constructor(localRecordingsFolder, limit) {
        this.localRecordingsFolder = localRecordingsFolder;
        this.limit = limit;
    }

    async deleteExcess() {
        const diskFull = await this.checkCapacity(this.limit);
        if (diskFull) {
            console.log("Disk is full");
            console.log(`Local recordings folder: ${this.localRecordingsFolder}`);

            let files = await fs.readdir(this.localRecordingsFolder);
            files = files.map(file => path.join(this.localRecordingsFolder, file));
            files = await Promise.all(files.map(async file => ({ file, time: await this.getFileCreationTime(file) })));
            files.sort((a, b) => a.time - b.time);

            const nImages = files.length;
            const imagesToRemove = Math.floor(nImages / 6);
            console.log(`Number of images found: ${nImages}, images to remove: ${imagesToRemove}`);

            if (nImages > imagesToRemove) {
                for (let i = 0; i < imagesToRemove; i++) {
                    const filePath = files[i].file;
                    console.log(`Deleting ${filePath}`);
                    await fs.rm(filePath, { recursive: true, force: true });
                }
            }
        }
    }

    async checkCapacity(maxUsed) {
        // const usage = await this.myExec('df -H /');
        // const usedPercentage = this.extractUsedPercentage(usage);
        // const tooFull = usedPercentage >= maxUsed;
        // console.log(`Used capacity % = ${usedPercentage}, too full = ${tooFull}`);
        // return tooFull;
        return false;
    }

    extractUsedPercentage(usage) {
        const lines = usage.split('\n');
        const header = lines[0].split(/\s+/);
        const index = header.indexOf('Capacity');  // Change '%' to 'Capacity' for macOS
        if (index === -1) throw new Error("Could not find 'Capacity' in df output");
        const usedPercentage = parseInt(lines[1].split(/\s+/)[index].replace('%', ''), 10);
        return usedPercentage;
    }

    myExec(cmd) {
        return new Promise((resolve, reject) => {
            exec(cmd, (error, stdout, stderr) => {
                if (error) {
                    console.error(`exec error: ${error}`);
                    return reject(error);
                }
                resolve(stdout);
            });
        });
    }

    async getFileCreationTime(filePath) {
        const stats = await fs.stat(filePath);
        return stats.birthtimeMs;
    }
}

module.exports = DriveCapacity;
