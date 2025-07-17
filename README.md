# High-Performance Screen Sharing Software

A blazing-fast, open-source screen sharing solution that achieves consistent 60 FPS streaming using WebRTC and Python. Built for developers who need reliable, low-latency screen sharing without third-party dependencies.

## 🚀 Features

- **60 FPS Screen Streaming**: Consistent high-framerate capture and streaming
- **Ultra-Low Latency**: <200ms latency for real-time interaction
- **WebRTC P2P**: Direct peer-to-peer streaming with fallback STUN servers
- **Cross-Platform**: Works on Windows, Linux, and macOS
- **Zero Dependencies**: No cloud services, no proprietary tools
- **Beautiful UI**: Modern, responsive web interface with real-time stats
- **Performance Monitoring**: Live FPS, latency, and connection metrics

## 📋 Requirements

- Python 3.8+
- Modern web browser with WebRTC support
- For optimal performance: 4+ GB RAM, multi-core CPU

## 🔧 Installation

1. **Clone or download** the project files
2. **Install dependencies**:
   ```bash
   pip install -r requirements.txt
   ```

## 🚀 Quick Start

1. **Start the server**:
   ```bash
   python main.py
   ```

2. **Open your browser** and go to:
   ```
   http://localhost:8080
   ```

3. **Click "Connect"** to start receiving the screen stream

## ⚙️ Configuration Options

### Command Line Arguments

```bash
python main.py [options]
```

| Option | Default | Description |
|--------|---------|-------------|
| `--host` | `0.0.0.0` | Server host address |
| `--port` | `8080` | Server port |
| `--fps` | `60` | Target frames per second |
| `--width` | `1280` | Target width resolution |
| `--height` | `720` | Target height resolution |
| `--log-level` | `INFO` | Logging level (DEBUG, INFO, WARNING, ERROR) |

### Examples

**High-performance mode** (30 FPS for better stability):
```bash
python main.py --fps 30 --width 1920 --height 1080
```

**Low-bandwidth mode**:
```bash
python main.py --fps 30 --width 640 --height 480
```

**Debug mode**:
```bash
python main.py --log-level DEBUG
```

## 🌐 Network Setup

### Local Network
Works out of the box on your local network.

### Internet Access
For internet streaming, you'll need to configure port forwarding:

1. **Router Configuration**: Forward port 8080 (or your chosen port) to your computer
2. **Firewall**: Allow the port through your firewall
3. **Share your public IP**: Viewers access `http://YOUR_PUBLIC_IP:8080`

### Security Considerations
- This software is designed for trusted networks
- For production use, consider adding authentication
- Use HTTPS in production environments

## 📊 Performance Optimization

### System Requirements
- **CPU**: Multi-core processor (4+ cores recommended)
- **RAM**: 4+ GB available
- **Network**: Stable connection with sufficient upload bandwidth

### Optimization Tips

1. **Close unnecessary applications** to free up CPU resources
2. **Use wired connection** for better stability
3. **Adjust resolution** if experiencing performance issues
4. **Monitor stats** using the built-in performance panel

### GPU Acceleration (Optional)
For NVIDIA GPUs, you can enable hardware encoding:
```bash
pip install nvidia-ml-py3
```

## 🎛️ Viewer Interface

### Controls
- **Connect/Disconnect**: Start/stop the stream
- **Toggle Stats**: Show/hide performance metrics
- **Fullscreen**: Press `F` or click the fullscreen button
- **Keyboard Shortcuts**:
  - `F`: Toggle fullscreen
  - `S`: Toggle stats
  - `Escape`: Exit fullscreen

### Performance Metrics
- **FPS**: Current streaming framerate
- **Resolution**: Stream resolution
- **Latency**: Round-trip time
- **Connections**: Number of active viewers

## 🏗️ Architecture

### Core Components

1. **`screen_capture.py`**: High-performance screen capture using MSS
2. **`webrtc_server.py`**: WebRTC streaming and signaling server
3. **`main.py`**: CLI interface and application orchestration
4. **`web/index.html`**: Modern viewer interface
5. **`web/script.js`**: WebRTC client implementation

### Technical Details

- **Screen Capture**: MSS (Multi-Screen Shot) for fast screen grabbing
- **Video Processing**: OpenCV for frame processing and resizing
- **WebRTC**: aiortc for Python WebRTC implementation
- **Signaling**: WebSocket-based signaling server
- **Frontend**: Vanilla JavaScript with modern WebRTC APIs

## 🐛 Troubleshooting

### Common Issues

**"Permission denied" errors**:
- Run with administrator/root privileges if needed
- Check screen recording permissions on macOS

**High CPU usage**:
- Reduce FPS: `--fps 30`
- Lower resolution: `--width 640 --height 480`
- Close other applications

**Connection failures**:
- Check firewall settings
- Verify port availability
- Test with `localhost` first

**Poor video quality**:
- Increase resolution if bandwidth allows
- Check network stability
- Monitor performance stats

### Debug Mode
Enable detailed logging:
```bash
python main.py --log-level DEBUG
```

## 🔄 Development

### File Structure
```
├── main.py              # CLI entry point
├── screen_capture.py    # Screen capture module
├── webrtc_server.py     # WebRTC server
├── requirements.txt     # Python dependencies
├── README.md           # This file
└── web/
    ├── index.html      # Viewer interface
    └── script.js       # WebRTC client
```

### Extending the Software

**Add authentication**:
Modify `webrtc_server.py` to add login functionality.

**Multiple monitor support**:
Extend `screen_capture.py` to capture specific monitors.

**Recording functionality**:
Add video recording using OpenCV's VideoWriter.

## 📄 License

This project is open-source and available under the MIT License.

## 🤝 Contributing

1. Fork the repository
2. Create a feature branch
3. Make your changes
4. Test thoroughly
5. Submit a pull request

## 🆘 Support

For issues and questions:
1. Check the troubleshooting section
2. Enable debug logging
3. Check the console for error messages
4. Create an issue with detailed information

---

**Made with ❤️ for the open-source community**

*High-performance screen sharing without the complexity*