# Screen Share Pro - Multi-User Edition

A high-performance, multi-user screen sharing solution built with Python that works like Google Meet. Test with multiple browsers as different users!

## 🚀 Features

- **Multi-User Support**: Multiple users can join the same room
- **Presenter System**: Only the presenter can share screen (like Google Meet)
- **Real-Time Chat**: Built-in chat system for all participants
- **60 FPS Streaming**: High-performance screen capture and streaming
- **Monitor Selection**: Choose which monitor to share
- **Quality Controls**: Adjust FPS, quality, and resolution
- **Cross-Browser**: Works in Chrome, Firefox, Safari, Edge
- **No Dependencies**: Pure Python with web interface

## 📋 Requirements

- Python 3.8+
- Modern web browser
- For optimal performance: 4+ GB RAM, multi-core CPU

## 🔧 Installation

1. **Install dependencies**:
   ```bash
   pip install -r requirements.txt
   ```

## 🚀 Quick Start

1. **Start the server**:
   ```bash
   python unified_server.py
   ```

2. **Open multiple browser tabs/windows**:
   ```
   http://localhost:8080
   ```

3. **Test multi-user functionality**:
   - Each tab represents a different user
   - First user becomes presenter automatically
   - Only presenter can start/stop screen sharing
   - Other users can request presenter rights
   - Everyone can use chat

## 🧪 How to Test Multi-User Functionality

### Method 1: Multiple Browser Tabs
1. Open `http://localhost:8080` in multiple tabs
2. Each tab acts as a different user
3. Watch how users appear in the participants list

### Method 2: Different Browsers
1. Open the URL in Chrome: `http://localhost:8080`
2. Open the same URL in Firefox: `http://localhost:8080`
3. Open in Safari, Edge, etc.
4. Each browser represents a different user

### Method 3: Different Devices (Same Network)
1. Find your computer's IP address
2. On other devices, visit: `http://YOUR_IP:8080`
3. Each device joins as a separate user

### Method 4: Incognito/Private Windows
1. Open regular browser window
2. Open incognito/private window
3. Visit the same URL in both
4. Each window is treated as different user

## ⚙️ Configuration Options

```bash
python unified_server.py [options]
```

| Option | Default | Description |
|--------|---------|-------------|
| `--host` | `0.0.0.0` | Server host address |
| `--port` | `8080` | Server port |
| `--fps` | `60` | Target frames per second |
| `--quality` | `85` | JPEG quality (1-100) |

### Examples

**High quality mode**:
```bash
python unified_server.py --fps 60 --quality 95
```

**Performance mode**:
```bash
python unified_server.py --fps 30 --quality 70
```

**Custom port**:
```bash
python unified_server.py --port 9000
```

## 🎛️ User Interface Features

### For Presenters
- **Start/Stop Sharing**: Control screen sharing
- **Monitor Selection**: Choose which monitor to share
- **Quality Settings**: Adjust FPS, quality, resolution
- **Chat**: Communicate with all participants

### For Viewers
- **Request Presenter**: Ask to become presenter
- **View Stream**: Watch the shared screen
- **Chat**: Participate in group chat
- **Fullscreen**: View stream in fullscreen mode

### For Everyone
- **Participants List**: See all connected users
- **Real-time Stats**: FPS, quality, resolution metrics
- **Chat System**: Group messaging
- **Responsive Design**: Works on desktop and mobile

## 🔧 Technical Details

### Architecture
- **Backend**: Python with aiohttp (async web server)
- **Frontend**: Pure HTML/CSS/JavaScript (no frameworks)
- **Communication**: WebSockets for real-time messaging
- **Streaming**: HTTP polling for video frames
- **Screen Capture**: MSS (Multi-Screen Shot) library

### Performance
- **Frame Rate**: Up to 60 FPS
- **Latency**: <200ms on local network
- **Quality**: Adjustable JPEG compression
- **Memory**: Efficient frame buffering

## 🐛 Troubleshooting

### Common Issues

**"Permission denied" errors**:
- Run with administrator/root privileges
- Check screen recording permissions (macOS)

**High CPU usage**:
- Reduce FPS: `--fps 30`
- Lower quality: `--quality 70`
- Close unnecessary applications

**Connection issues**:
- Check firewall settings
- Try different port: `--port 9000`
- Test with `localhost` first

**Multiple users not working**:
- Clear browser cache
- Try incognito/private windows
- Use different browsers
- Check browser console for errors

### Debug Mode
Enable detailed logging by modifying the logging level in the script.

## 🌐 Network Setup

### Local Network
Works out of the box on your local network.

### Internet Access
For internet access:
1. Configure port forwarding on your router
2. Allow port through firewall
3. Share your public IP with users

## 🔒 Security Notes

- Designed for trusted networks
- No built-in authentication (add if needed)
- Consider HTTPS for production use
- Screen sharing requires appropriate permissions

## 📊 Performance Tips

1. **Close unnecessary applications** to free CPU
2. **Use wired connection** for stability
3. **Adjust quality settings** based on network
4. **Monitor system resources** during use
5. **Test with fewer users** if performance issues occur

## 🤝 Contributing

1. Fork the repository
2. Create a feature branch
3. Test thoroughly with multiple users
4. Submit a pull request

## 📄 License

MIT License - feel free to use and modify!

---

**Perfect for testing multi-user screen sharing scenarios! 🎉**

*Experience Google Meet-like functionality with your own Python server*