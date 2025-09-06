class AuthenticationApp {
    constructor() {
        this.isRunning = false;
        this.stream = null;
        this.currentVoter = null;
        this.init();
    }

    init() {
        this.setupEventListeners();
    }

    setupEventListeners() {
        document.getElementById('startBtn').addEventListener('click', () => {
            if (this.isRunning) {
                this.stopAuthentication();
            } else {
                this.startAuthentication();
            }
        });

        document.getElementById('confirmBtn').addEventListener('click', () => {
            this.confirmAuthentication();
        });

        document.getElementById('nextBtn').addEventListener('click', () => {
            this.nextVoter();
        });
    }

    async startAuthentication() {
        try {
            this.stream = await navigator.mediaDevices.getUserMedia({
                video: { width: 640, height: 480 }
            });

            const video = document.getElementById('video');
            video.srcObject = this.stream;

            this.isRunning = true;
            document.getElementById('startBtn').innerHTML = '<i class="fas fa-stop"></i> Stop Authentication';
            document.getElementById('startBtn').classList.remove('btn-success');
            document.getElementById('startBtn').classList.add('btn-danger');

            this.processVideo();

        } catch (error) {
            console.error('Error accessing camera:', error);
            alert('Cannot access camera. Please check permissions.');
        }
    }

    stopAuthentication() {
        if (this.stream) {
            this.stream.getTracks().forEach(track => track.stop());
            this.stream = null;
        }

        this.isRunning = false;
        document.getElementById('startBtn').innerHTML = '<i class="fas fa-play"></i> Start Authentication';
        document.getElementById('startBtn').classList.remove('btn-danger');
        document.getElementById('startBtn').classList.add('btn-success');

        this.hideVoterInfo();
    }

    async processVideo() {
        if (!this.isRunning) return;

        const video = document.getElementById('video');
        const canvas = document.getElementById('canvas');
        const context = canvas.getContext('2d');

        canvas.width = video.videoWidth;
        canvas.height = video.videoHeight;
        context.drawImage(video, 0, 0, canvas.width, canvas.height);

        const imageData = canvas.toDataURL('image/jpeg');
        const officerId = document.getElementById('officerId').value;

        try {
            const response = await fetch('/api/process_frame', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ image: imageData, officer_id: officerId })
            });

            const result = await response.json();

            if (result.success && result.detected) {
                this.displayVoterInfo(result.voter, result.confidence);
            } else {
                this.hideVoterInfo();
            }

        } catch (error) {
            console.error('Error processing frame:', error);
        }

        if (this.isRunning) {
            setTimeout(() => this.processVideo(), 1000);
        }
    }


    displayVoterInfo(voter, confidence) {
        this.currentVoter = voter;

        document.getElementById('noDetection').style.display = 'none';
        document.getElementById('voterInfo').style.display = 'block';

        document.getElementById('infoNIC').textContent = voter.nic;
        document.getElementById('infoName').textContent = voter.full_name;
        document.getElementById('infoAddress').textContent = voter.address || 'N/A';
        document.getElementById('infoDivision').textContent = voter.electoral_division || 'N/A';
        document.getElementById('infoConfidence').textContent = `${(confidence * 100).toFixed(1)}%`;

        if (voter.face_image_path) {
            document.getElementById('voterPhoto').src = voter.face_image_path;
        }

        document.getElementById('confirmBtn').disabled = false;


        const confidenceCell = document.getElementById('infoConfidence');
        confidenceCell.className = '';
        if (confidence > 0.7) {
            confidenceCell.classList.add('text-success', 'fw-bold');
        } else if (confidence > 0.5) {
            confidenceCell.classList.add('text-warning', 'fw-bold');
        } else {
            confidenceCell.classList.add('text-danger', 'fw-bold');
        }
    }

    hideVoterInfo() {
        document.getElementById('noDetection').style.display = 'block';
        document.getElementById('voterInfo').style.display = 'none';
        document.getElementById('confirmBtn').disabled = true;
        this.currentVoter = null;
    }

    async confirmAuthentication() {
        if (!this.currentVoter) return;

        const officerId = document.getElementById('officerId').value;
        const confidence = parseFloat(document.getElementById('infoConfidence').textContent) / 100;

        try {
            const response = await fetch('/api/confirm_auth', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({
                    unique_id: this.currentVoter.unique_id,
                    nic: this.currentVoter.nic,
                    full_name: this.currentVoter.full_name,
                    officer_id: officerId,
                    confidence: confidence
                })
            });

            const result = await response.json();

            if (result.success) {
                alert(result.message);
                this.nextVoter();
            } else {
                alert('Error: ' + result.error);
            }

        } catch (error) {
            console.error('Error confirming authentication:', error);
            alert('Error confirming authentication');
        }
    }

    nextVoter() {
        this.hideVoterInfo();
    }
}


document.addEventListener('DOMContentLoaded', () => {
    window.authApp = new AuthenticationApp();
});