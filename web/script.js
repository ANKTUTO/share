class ScreenShareClient {
    constructor() {
        this.ws = null;
        this.pc = null;
        this.connected = false;
        this.statsVisible = false;
        this.latencyStart = 0;
        
        this.initElements();
        this.setupEventListeners();
        this.setupWebRTC();
    }
    
    initElements() {
        this.remoteVideo = document.getElementById('remoteVideo');
        this.placeholder = document.getElementById('placeholder');
        this.connectBtn = document.getElementById('connectBtn');
        this.disconnectBtn = document.getElementById('disconnectBtn');
        this.statsBtn = document.getElementById('statsBtn');
        this.fullscreenBtn = document.getElementById('fullscreenBtn');
        this.statusIndicator = document.getElementById('statusIndicator');
        this.statusText = document.getElementById('statusText');
        this.stats = document.getElementById('stats');
        
        // Stats elements
        this.fpsValue = document.getElementById('fpsValue');
        this.resolutionValue = document.getElementById('resolutionValue');
        this.connectionsValue = document.getElementById('connectionsValue');
        this.latencyValue = document.getElementById('latencyValue');
    }
    
    setupEventListeners() {
        this.connectBtn.addEventListener('click', () => this.connect());
        this.disconnectBtn.addEventListener('click', () => this.disconnect());
        this.statsBtn.addEventListener('click', () => this.toggleStats());
        this.fullscreenBtn.addEventListener('click', () => this.toggleFullscreen());
        
        // Video events
        this.remoteVideo.addEventListener('loadedmetadata', () => {
            console.log('Video metadata loaded');
            this.showVideo();
        });
        
        this.remoteVideo.addEventListener('play', () => {
            console.log('Video started playing');
        });
        
        this.remoteVideo.addEventListener('error', (e) => {
            console.error('Video error:', e);
        });
        
        // Keyboard shortcuts
        document.addEventListener('keydown', (e) => {
            if (e.key === 'f' || e.key === 'F') {
                this.toggleFullscreen();
            } else if (e.key === 's' || e.key === 'S') {
                this.toggleStats();
            } else if (e.key === 'Escape') {
                if (document.fullscreenElement) {
                    document.exitFullscreen();
                }
            }
        });
    }
    
    setupWebRTC() {
        // WebRTC configuration with STUN servers
        this.pcConfig = {
            iceServers: [
                { urls: 'stun:stun.l.google.com:19302' },
                { urls: 'stun:stun1.l.google.com:19302' }
            ]
        };
    }
    
    async connect() {
        try {
            this.updateStatus('Connecting...', false);
            this.connectBtn.disabled = true;
            
            // Connect WebSocket
            await this.connectWebSocket();
            
            // Setup WebRTC
            await this.setupPeerConnection();
            
            this.updateStatus('Connected', true);
            this.connectBtn.disabled = true;
            this.disconnectBtn.disabled = false;
            this.connected = true;
            
            // Start stats updates
            this.startStatsUpdates();
            
        } catch (error) {
            console.error('Connection failed:', error);
            this.updateStatus('Connection failed', false);
            this.connectBtn.disabled = false;
            this.disconnectBtn.disabled = true;
        }
    }
    
    async connectWebSocket() {
        return new Promise((resolve, reject) => {
            const wsUrl = `ws://${window.location.host}/ws`;
            this.ws = new WebSocket(wsUrl);
            
            this.ws.onopen = () => {
                console.log('WebSocket connected');
                resolve();
            };
            
            this.ws.onmessage = (event) => {
                this.handleWebSocketMessage(JSON.parse(event.data));
            };
            
            this.ws.onclose = () => {
                console.log('WebSocket disconnected');
                this.connected = false;
                this.updateStatus('Disconnected', false);
                this.connectBtn.disabled = false;
                this.disconnectBtn.disabled = true;
            };
            
            this.ws.onerror = (error) => {
                console.error('WebSocket error:', error);
                reject(error);
            };
            
            // Timeout
            setTimeout(() => {
                if (this.ws.readyState !== WebSocket.OPEN) {
                    reject(new Error('WebSocket connection timeout'));
                }
            }, 5000);
        });
    }
    
    async setupPeerConnection() {
        this.pc = new RTCPeerConnection(this.pcConfig);
        
        // Handle remote stream
        this.pc.ontrack = (event) => {
            console.log('Remote track received');
            this.remoteVideo.srcObject = event.streams[0];
        };
        
        // Handle ICE candidates
        this.pc.onicecandidate = (event) => {
            if (event.candidate) {
                this.sendMessage({
                    type: 'ice-candidate',
                    candidate: event.candidate
                });
            }
        };
        
        // Handle connection state changes
        this.pc.onconnectionstatechange = () => {
            console.log('Connection state:', this.pc.connectionState);
            
            if (this.pc.connectionState === 'connected') {
                this.updateStatus('Streaming', true);
            } else if (this.pc.connectionState === 'disconnected' || 
                      this.pc.connectionState === 'failed') {
                this.updateStatus('Connection lost', false);
            }
        };
        
        // Create offer
        const offer = await this.pc.createOffer();
        await this.pc.setLocalDescription(offer);
        
        this.latencyStart = Date.now();
        
        // Send offer
        this.sendMessage({
            type: 'offer',
            sdp: offer.sdp
        });
    }
    
    async handleWebSocketMessage(message) {
        console.log('Received message:', message.type);
        
        switch (message.type) {
            case 'answer':
                if (this.pc) {
                    const answer = new RTCSessionDescription({
                        type: 'answer',
                        sdp: message.sdp
                    });
                    await this.pc.setRemoteDescription(answer);
                    
                    // Calculate latency
                    const latency = Date.now() - this.latencyStart;
                    this.latencyValue.textContent = `${latency}ms`;
                }
                break;
                
            case 'ice-candidate':
                if (this.pc && message.candidate) {
                    await this.pc.addIceCandidate(new RTCIceCandidate(message.candidate));
                }
                break;
                
            case 'stats':
                this.updateStats(message);
                break;
                
            case 'error':
                console.error('Server error:', message.message);
                this.updateStatus('Error: ' + message.message, false);
                break;
        }
    }
    
    sendMessage(message) {
        if (this.ws && this.ws.readyState === WebSocket.OPEN) {
            this.ws.send(JSON.stringify(message));
        }
    }
    
    async disconnect() {
        this.connected = false;
        
        if (this.pc) {
            this.pc.close();
            this.pc = null;
        }
        
        if (this.ws) {
            this.ws.close();
            this.ws = null;
        }
        
        this.hideVideo();
        this.updateStatus('Disconnected', false);
        this.connectBtn.disabled = false;
        this.disconnectBtn.disabled = true;
        
        // Stop stats updates
        if (this.statsInterval) {
            clearInterval(this.statsInterval);
            this.statsInterval = null;
        }
    }
    
    showVideo() {
        this.remoteVideo.style.display = 'block';
        this.placeholder.style.display = 'none';
    }
    
    hideVideo() {
        this.remoteVideo.style.display = 'none';
        this.placeholder.style.display = 'block';
        this.remoteVideo.srcObject = null;
    }
    
    updateStatus(text, connected) {
        this.statusText.textContent = text;
        this.statusIndicator.classList.toggle('connected', connected);
    }
    
    toggleStats() {
        this.statsVisible = !this.statsVisible;
        this.stats.style.display = this.statsVisible ? 'grid' : 'none';
        this.statsBtn.textContent = this.statsVisible ? 'Hide Stats' : 'Show Stats';
    }
    
    toggleFullscreen() {
        if (!document.fullscreenElement) {
            this.remoteVideo.requestFullscreen().catch(err => {
                console.error('Error attempting to enable fullscreen:', err);
            });
        } else {
            document.exitFullscreen();
        }
    }
    
    updateStats(stats) {
        this.fpsValue.textContent = Math.round(stats.fps);
        this.resolutionValue.textContent = `${stats.resolution[0]}x${stats.resolution[1]}`;
        this.connectionsValue.textContent = stats.connections;
    }
    
    startStatsUpdates() {
        if (this.statsInterval) {
            clearInterval(this.statsInterval);
        }
        
        this.statsInterval = setInterval(() => {
            if (this.connected) {
                this.sendMessage({ type: 'stats-request' });
            }
        }, 1000);
    }
}

// Initialize the client when DOM is loaded
document.addEventListener('DOMContentLoaded', () => {
    new ScreenShareClient();
});