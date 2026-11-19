/**
 * Face Authenticity & Deepfake Detection - Client-side Controller
 */
document.addEventListener('DOMContentLoaded', () => {
    const dropzone = document.getElementById('dropzone');
    const imageInput = document.getElementById('imageInput');
    const uploadPrompt = document.getElementById('uploadPrompt');
    const previewArea = document.getElementById('previewArea');
    const previewImage = document.getElementById('previewImage');
    const previewFilename = document.getElementById('previewFilename');
    
    const analyzeBtn = document.getElementById('analyzeBtn');
    const btnSpinner = document.getElementById('btnSpinner');
    const btnIcon = document.getElementById('btnIcon');
    const btnText = document.getElementById('btnText');
    const resetBtn = document.getElementById('resetBtn');

    const placeholderView = document.getElementById('placeholderView');
    const resultView = document.getElementById('resultView');
    const statusBadge = document.getElementById('statusBadge');
    
    const verdictBanner = document.getElementById('verdictBanner');
    const verdictText = document.getElementById('verdictText');
    const confidenceText = document.getElementById('confidenceText');
    const realProbText = document.getElementById('realProbText');
    const realProgressBar = document.getElementById('realProgressBar');
    const fakeProbText = document.getElementById('fakeProbText');
    const fakeProgressBar = document.getElementById('fakeProgressBar');
    
    const annotatedResultImg = document.getElementById('annotatedResultImg');
    const faceCropResultImg = document.getElementById('faceCropResultImg');
    const analysisStatusText = document.getElementById('analysisStatusText');

    let selectedFile = null;

    // Handle File Selection
    function handleFile(file) {
        if (!file) return;

        const validTypes = ['image/jpeg', 'image/jpg', 'image/png', 'image/webp'];
        if (!validTypes.includes(file.type)) {
            alert('Please select a valid image file (JPG, JPEG, PNG, or WEBP).');
            return;
        }

        if (file.size > 16 * 1024 * 1024) {
            alert('Image size exceeds 16MB limit.');
            return;
        }

        selectedFile = file;

        // Display Preview
        const reader = new FileReader();
        reader.onload = (e) => {
            previewImage.src = e.target.result;
            previewFilename.textContent = `${file.name} (${(file.size / 1024).toFixed(1)} KB)`;
            uploadPrompt.classList.add('d-none');
            previewArea.classList.remove('d-none');
            analyzeBtn.disabled = false;
            statusBadge.textContent = 'Image Ready for Analysis';
            statusBadge.className = 'badge bg-info bg-opacity-25 text-info';
        };
        reader.readAsDataURL(file);
    }

    // Drag & Drop Listeners
    ['dragenter', 'dragover'].forEach(eventName => {
        dropzone.addEventListener(eventName, (e) => {
            e.preventDefault();
            e.stopPropagation();
            dropzone.classList.add('drag-active');
        }, false);
    });

    ['dragleave', 'drop'].forEach(eventName => {
        dropzone.addEventListener(eventName, (e) => {
            e.preventDefault();
            e.stopPropagation();
            dropzone.classList.remove('drag-active');
        }, false);
    });

    dropzone.addEventListener('drop', (e) => {
        const dt = e.dataTransfer;
        const file = dt.files[0];
        handleFile(file);
    });

    dropzone.addEventListener('click', (e) => {
        if (e.target !== imageInput && !previewArea.contains(e.target)) {
            imageInput.click();
        }
    });

    imageInput.addEventListener('change', (e) => {
        handleFile(e.target.files[0]);
    });

    // Reset Action
    function resetForm() {
        selectedFile = null;
        imageInput.value = '';
        previewImage.src = '';
        previewFilename.textContent = '';
        previewArea.classList.add('d-none');
        uploadPrompt.classList.remove('d-none');
        analyzeBtn.disabled = true;

        placeholderView.classList.remove('d-none');
        resultView.classList.add('d-none');

        statusBadge.textContent = 'Awaiting Input';
        statusBadge.className = 'badge bg-secondary bg-opacity-25 text-secondary';
    }

    resetBtn.addEventListener('click', resetForm);

    // Analyze Action (AJAX)
    analyzeBtn.addEventListener('click', async () => {
        if (!selectedFile) return;

        // UI Loading State
        analyzeBtn.disabled = true;
        btnSpinner.classList.remove('d-none');
        btnIcon.classList.add('d-none');
        btnText.textContent = 'Scanning Facial Artifacts...';
        statusBadge.textContent = 'Analyzing Features...';
        statusBadge.className = 'badge bg-warning bg-opacity-25 text-warning';

        const formData = new FormData();
        formData.append('image', selectedFile);

        try {
            const response = await fetch('/predict', {
                method: 'POST',
                body: formData
            });

            const data = await response.json();

            if (!response.ok || !data.success) {
                throw new Error(data.error || 'Server returned an error.');
            }

            // Render Results
            placeholderView.classList.add('d-none');
            resultView.classList.remove('d-none');

            const isReal = data.prediction.toUpperCase() === 'REAL';
            verdictText.textContent = isReal ? 'REAL FACE' : 'FAKE / AI-GENERATED';
            confidenceText.textContent = `Confidence: ${data.confidence}%`;

            verdictBanner.className = `verdict-banner p-4 rounded-4 text-center mb-4 ${isReal ? 'verdict-real' : 'verdict-fake'}`;

            realProbText.textContent = `${data.real_probability}%`;
            realProgressBar.style.width = `${data.real_probability}%`;

            fakeProbText.textContent = `${data.fake_probability}%`;
            fakeProgressBar.style.width = `${data.fake_probability}%`;

            // Update Forensic Metrics
            const metricSensor = document.getElementById('metricSensor');
            const metricFFT = document.getElementById('metricFFT');
            const metricChroma = document.getElementById('metricChroma');
            if (data.forensics) {
                if (metricSensor) metricSensor.textContent = data.forensics.sensor_noise_variance;
                if (metricFFT) metricFFT.textContent = data.forensics.frequency_fft_ratio;
                if (metricChroma) metricChroma.textContent = data.forensics.chromatic_coherence;
            }

            annotatedResultImg.src = data.annotated_image_url;
            faceCropResultImg.src = data.face_image_url;
            analysisStatusText.textContent = data.analysis_status;

            statusBadge.textContent = `Completed (${data.prediction})`;
            statusBadge.className = `badge ${isReal ? 'bg-success' : 'bg-danger'} bg-opacity-25 ${isReal ? 'text-success' : 'text-danger'}`;

        } catch (err) {
            alert('Analysis Error: ' + err.message);
            statusBadge.textContent = 'Analysis Failed';
            statusBadge.className = 'badge bg-danger bg-opacity-25 text-danger';
        } finally {
            analyzeBtn.disabled = false;
            btnSpinner.classList.add('d-none');
            btnIcon.classList.remove('d-none');
            btnText.textContent = 'Analyse Face Authenticity';
        }
    });
});
