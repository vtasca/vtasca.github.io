// Image Dithering Tool
class ImageDitheringTool {
    constructor() {
        this.canvas = null;
        this.ctx = null;
        this.originalImageData = null;
        this.currentImage = null;
        this.fullSizeCanvas = null;
        this.fullSizeCtx = null;
        this.fullSizeImageData = null;
        this.init();
    }

    async init() {
        this.setupCanvas();
        this.setupEventListeners();
    }

    setupCanvas() {
        // Create canvas elements for input and output
        const inputCanvas = document.getElementById('input-canvas');
        const outputCanvas = document.getElementById('output-canvas');
        
        if (inputCanvas) {
            this.inputCanvas = inputCanvas;
            this.inputCtx = inputCanvas.getContext('2d');
        }
        
        if (outputCanvas) {
            this.outputCanvas = outputCanvas;
            this.outputCtx = outputCanvas.getContext('2d');
        }

        // Create full-size canvas for processing and downloading
        this.fullSizeCanvas = document.createElement('canvas');
        this.fullSizeCtx = this.fullSizeCanvas.getContext('2d');
    }

    setupEventListeners() {
        const fileInput = document.getElementById('image-input');
        const ditherBtn = document.getElementById('dither-btn');
        const downloadBtn = document.getElementById('download-btn');
        const resetBtn = document.getElementById('reset-btn');
        const algorithmSelect = document.getElementById('algorithm-select');
        const colorCountSelect = document.getElementById('color-count-select');
        const contrastSlider = document.getElementById('contrast-slider');
        const brightnessSlider = document.getElementById('brightness-slider');

        if (fileInput) {
            fileInput.addEventListener('change', (e) => this.handleFileSelect(e));
        }

        if (ditherBtn) {
            ditherBtn.addEventListener('click', () => this.applyDithering());
        }

        if (downloadBtn) {
            downloadBtn.addEventListener('click', () => this.downloadImage());
        }

        if (resetBtn) {
            resetBtn.addEventListener('click', () => this.resetImage());
        }

        if (algorithmSelect) {
            algorithmSelect.addEventListener('change', () => this.updatePreview());
        }

        if (colorCountSelect) {
            colorCountSelect.addEventListener('change', () => this.updatePreview());
        }

        if (contrastSlider) {
            contrastSlider.addEventListener('input', (e) => {
                document.getElementById('contrast-value').textContent = e.target.value;
                this.updatePreview();
            });
        }

        if (brightnessSlider) {
            brightnessSlider.addEventListener('input', (e) => {
                document.getElementById('brightness-value').textContent = e.target.value;
                this.updatePreview();
            });
        }
    }

    handleFileSelect(event) {
        const file = event.target.files[0];
        if (!file) return;

        if (!file.type.startsWith('image/')) {
            this.showError('Please select a valid image file.');
            return;
        }

        const reader = new FileReader();
        reader.onload = (e) => {
            this.loadImage(e.target.result);
        };
        reader.readAsDataURL(file);
    }

    loadImage(src) {
        const img = new Image();
        img.onload = () => {
            this.currentImage = img;
            this.displayOriginalImage(img);
            this.updatePreview();
        };
        img.onerror = () => {
            this.showError('Failed to load image.');
        };
        img.src = src;
    }

    displayOriginalImage(img) {
        if (!this.inputCanvas || !this.inputCtx) return;

        // Calculate dimensions to fit in canvas while maintaining aspect ratio
        const maxWidth = 400;
        const maxHeight = 300;
        let { width, height } = this.calculateDimensions(img.width, img.height, maxWidth, maxHeight);

        // Set preview canvas dimensions
        this.inputCanvas.width = width;
        this.inputCanvas.height = height;
        this.outputCanvas.width = width;
        this.outputCanvas.height = height;

        // Draw preview image
        this.inputCtx.drawImage(img, 0, 0, width, height);
        this.originalImageData = this.inputCtx.getImageData(0, 0, width, height);

        // Set full-size canvas to original image dimensions
        this.fullSizeCanvas.width = img.width;
        this.fullSizeCanvas.height = img.height;
        this.fullSizeCtx.drawImage(img, 0, 0);
        this.fullSizeImageData = this.fullSizeCtx.getImageData(0, 0, img.width, img.height);
    }

    calculateDimensions(imgWidth, imgHeight, maxWidth, maxHeight) {
        const ratio = Math.min(maxWidth / imgWidth, maxHeight / imgHeight);
        return {
            width: Math.floor(imgWidth * ratio),
            height: Math.floor(imgHeight * ratio)
        };
    }

    updatePreview() {
        if (!this.originalImageData || !this.fullSizeImageData) return;

        const algorithm = document.getElementById('algorithm-select')?.value || 'floyd-steinberg';
        const colorCount = parseInt(document.getElementById('color-count-select')?.value || '4');
        const contrast = parseFloat(document.getElementById('contrast-slider')?.value || '1.0');
        const brightness = parseFloat(document.getElementById('brightness-slider')?.value || '0.0');

        const options = { algorithm, colorCount, contrast, brightness };

        // Process full-size image for download
        const fullSizeProcessedData = this.processImage(this.fullSizeImageData, options);
        
        // Store the full-size processed data for download
        this.fullSizeProcessedData = fullSizeProcessedData;

        // Process preview image for display
        const previewProcessedData = this.processImage(this.originalImageData, options);
        this.displayProcessedImage(previewProcessedData);
    }

    applyDithering() {
        this.updatePreview();
        this.showSuccess('Dithering applied successfully!');
    }

    processImage(imageData, options) {
        const { width, height, data } = imageData;
        const newData = new ImageData(width, height);
        const newPixels = newData.data;

        // First, apply contrast and brightness adjustments
        for (let i = 0; i < data.length; i += 4) {
            let r = data[i];
            let g = data[i + 1];
            let b = data[i + 2];

            // Apply contrast
            r = Math.max(0, Math.min(255, (r - 128) * options.contrast + 128));
            g = Math.max(0, Math.min(255, (g - 128) * options.contrast + 128));
            b = Math.max(0, Math.min(255, (b - 128) * options.contrast + 128));

            // Apply brightness
            r = Math.max(0, Math.min(255, r + options.brightness));
            g = Math.max(0, Math.min(255, g + options.brightness));
            b = Math.max(0, Math.min(255, b + options.brightness));

            newPixels[i] = r;
            newPixels[i + 1] = g;
            newPixels[i + 2] = b;
            newPixels[i + 3] = data[i + 3]; // Alpha
        }

        // Then apply dithering
        return this.applyDitheringAlgorithm(newData, options);
    }

    applyDitheringAlgorithm(imageData, options) {
        const { width, height, data } = imageData;
        const newData = new ImageData(width, height);
        const newPixels = newData.data;

        // Copy original data
        for (let i = 0; i < data.length; i++) {
            newPixels[i] = data[i];
        }

        // Generate palette
        const palette = this.generatePalette(options.colorCount);

        switch (options.algorithm) {
            case 'floyd-steinberg':
                return this.floydSteinbergDither(newData, palette);
            case 'ordered':
                return this.orderedDither(newData, palette);
            case 'atkinson':
                return this.atkinsonDither(newData, palette);
            case 'bayer':
                return this.bayerDither(newData, palette);
            default:
                return this.floydSteinbergDither(newData, palette);
        }
    }

    generatePalette(colorCount) {
        const palette = [];
        const step = 255 / (colorCount - 1);

        for (let i = 0; i < colorCount; i++) {
            const value = Math.round(i * step);
            palette.push([value, value, value]);
        }

        return palette;
    }

    findClosestColor(r, g, b, palette) {
        let minDistance = Infinity;
        let closestColor = palette[0];

        for (const color of palette) {
            const distance = Math.sqrt(
                Math.pow(r - color[0], 2) +
                Math.pow(g - color[1], 2) +
                Math.pow(b - color[2], 2)
            );

            if (distance < minDistance) {
                minDistance = distance;
                closestColor = color;
            }
        }

        return closestColor;
    }

    floydSteinbergDither(imageData, palette) {
        const { width, height, data } = imageData;

        for (let y = 0; y < height; y++) {
            for (let x = 0; x < width; x++) {
                const idx = (y * width + x) * 4;
                const r = data[idx];
                const g = data[idx + 1];
                const b = data[idx + 2];

                const closestColor = this.findClosestColor(r, g, b, palette);
                const errorR = r - closestColor[0];
                const errorG = g - closestColor[1];
                const errorB = b - closestColor[2];

                data[idx] = closestColor[0];
                data[idx + 1] = closestColor[1];
                data[idx + 2] = closestColor[2];

                // Distribute error to neighboring pixels
                this.distributeError(data, x, y, width, height, errorR, errorG, errorB, [
                    [1, 0, 7/16],
                    [-1, 1, 3/16],
                    [0, 1, 5/16],
                    [1, 1, 1/16]
                ]);
            }
        }

        return imageData;
    }

    orderedDither(imageData, palette) {
        const { width, height, data } = imageData;
        const thresholdMap = [
            [0, 8, 2, 10],
            [12, 4, 14, 6],
            [3, 11, 1, 9],
            [15, 7, 13, 5]
        ];

        for (let y = 0; y < height; y++) {
            for (let x = 0; x < width; x++) {
                const idx = (y * width + x) * 4;
                const r = data[idx];
                const g = data[idx + 1];
                const b = data[idx + 2];

                const threshold = thresholdMap[y % 4][x % 4] * 16;
                const adjustedR = r + threshold;
                const adjustedG = g + threshold;
                const adjustedB = b + threshold;

                const closestColor = this.findClosestColor(adjustedR, adjustedG, adjustedB, palette);

                data[idx] = closestColor[0];
                data[idx + 1] = closestColor[1];
                data[idx + 2] = closestColor[2];
            }
        }

        return imageData;
    }

    atkinsonDither(imageData, palette) {
        const { width, height, data } = imageData;

        for (let y = 0; y < height; y++) {
            for (let x = 0; x < width; x++) {
                const idx = (y * width + x) * 4;
                const r = data[idx];
                const g = data[idx + 1];
                const b = data[idx + 2];

                const closestColor = this.findClosestColor(r, g, b, palette);
                const errorR = r - closestColor[0];
                const errorG = g - closestColor[1];
                const errorB = b - closestColor[2];

                data[idx] = closestColor[0];
                data[idx + 1] = closestColor[1];
                data[idx + 2] = closestColor[2];

                // Atkinson dithering pattern
                this.distributeError(data, x, y, width, height, errorR, errorG, errorB, [
                    [1, 0, 1/8],
                    [2, 0, 1/8],
                    [-1, 1, 1/8],
                    [0, 1, 1/8],
                    [1, 1, 1/8],
                    [0, 2, 1/8]
                ]);
            }
        }

        return imageData;
    }

    bayerDither(imageData, palette) {
        const { width, height, data } = imageData;
        const bayerMatrix = [
            [0, 8, 2, 10],
            [12, 4, 14, 6],
            [3, 11, 1, 9],
            [15, 7, 13, 5]
        ];

        for (let y = 0; y < height; y++) {
            for (let x = 0; x < width; x++) {
                const idx = (y * width + x) * 4;
                const r = data[idx];
                const g = data[idx + 1];
                const b = data[idx + 2];

                const threshold = bayerMatrix[y % 4][x % 4] * 16;
                const adjustedR = r + threshold;
                const adjustedG = g + threshold;
                const adjustedB = b + threshold;

                const closestColor = this.findClosestColor(adjustedR, adjustedG, adjustedB, palette);

                data[idx] = closestColor[0];
                data[idx + 1] = closestColor[1];
                data[idx + 2] = closestColor[2];
            }
        }

        return imageData;
    }

    distributeError(data, x, y, width, height, errorR, errorG, errorB, pattern) {
        for (const [dx, dy, factor] of pattern) {
            const nx = x + dx;
            const ny = y + dy;

            if (nx >= 0 && nx < width && ny >= 0 && ny < height) {
                const idx = (ny * width + nx) * 4;
                data[idx] = Math.max(0, Math.min(255, data[idx] + errorR * factor));
                data[idx + 1] = Math.max(0, Math.min(255, data[idx + 1] + errorG * factor));
                data[idx + 2] = Math.max(0, Math.min(255, data[idx + 2] + errorB * factor));
            }
        }
    }

    displayProcessedImage(imageData) {
        if (!this.outputCanvas || !this.outputCtx) return;

        this.outputCtx.putImageData(imageData, 0, 0);
    }

    downloadImage() {
        if (!this.fullSizeProcessedData) {
            this.showError('No processed image to download.');
            return;
        }

        // Create a temporary canvas for the full-size image
        const tempCanvas = document.createElement('canvas');
        const tempCtx = tempCanvas.getContext('2d');
        tempCanvas.width = this.fullSizeProcessedData.width;
        tempCanvas.height = this.fullSizeProcessedData.height;
        tempCtx.putImageData(this.fullSizeProcessedData, 0, 0);

        const link = document.createElement('a');
        link.download = 'dithered-image.png';
        link.href = tempCanvas.toDataURL();
        link.click();
    }

    resetImage() {
        if (this.currentImage) {
            this.displayOriginalImage(this.currentImage);
        }
        
        // Clear full-size processed data
        this.fullSizeProcessedData = null;
        
        // Reset controls
        document.getElementById('contrast-slider').value = 1.0;
        document.getElementById('brightness-slider').value = 0.0;
        document.getElementById('algorithm-select').value = 'floyd-steinberg';
        document.getElementById('color-count-select').value = '4';
    }

    showError(message) {
        console.error(message);
        alert(message);
    }

    showSuccess(message) {
        console.log(message);
        // You could enhance this with a toast notification
    }
}

// Initialize the tool when the page loads
document.addEventListener('DOMContentLoaded', () => {
    new ImageDitheringTool();
});
