# DupFinder - Video Duplicate Detection Tool

## Project Overview

This is a GUI-based intelligent video duplicate detection tool that combines content-aware hashing and machine learning-enhanced comparison techniques. The tool identifies duplicate video files that may have been transcoded, edited, scaled, or have different quality levels, going beyond simple filename and size comparisons.

## Project Status

**Current Phase**: Requirements and Planning
- The project currently contains only the requirements document (需求文档.md)
- No implementation code exists yet
- This is a greenfield project ready for development

## Planned Architecture

Based on the requirements document, the system will follow this architecture:

### Core Components
1. **GUI Layer** - PyQt/PySide or Tkinter interface
2. **Scanning Engine** - Multi-path directory scanning with video format detection
3. **Duplicate Detection Engine** - Hybrid analysis using:
   - Metadata pre-filtering (size, duration, resolution)
   - Content feature extraction (frame signatures, perceptual hashing)
   - Optional ML-enhanced comparison (CNN features)
4. **Result Management** - Grouping, display, and user selection interface
5. **File Operations** - Safe deletion/moving with backup options

### Technology Stack (Planned)
- **Language**: Python
- **GUI**: PyQt/PySide or Tkinter
- **Video Processing**: OpenCV, FFmpeg
- **Hashing**: videohash, imagehash libraries
- **ML (Optional)**: TensorFlow/PyTorch for deep feature extraction
- **Utilities**: NumPy, Pillow

## Development Workflow

### Initial Setup Commands
```bash
# Create virtual environment
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate

# Install dependencies (once requirements.txt is created)
pip install -r requirements.txt

# Development dependencies
pip install pytest black flake8 mypy
```

### Common Development Commands
```bash
# Code formatting
black src/

# Linting
flake8 src/

# Type checking
mypy src/

# Run tests
pytest tests/

# Run application (once implemented)
python src/main.py
```

## Key Implementation Considerations

### Performance Optimization
- Implement multi-threading for UI responsiveness during large directory scans
- Configurable frame sampling rates to balance speed vs accuracy
- Progress tracking and cancellation support

### Safety Features
- Default to moving files to recycle bin rather than permanent deletion
- Confirmation dialogs for destructive operations
- Backup folder options for processed files

### User Experience
- Drag-and-drop path addition
- Real-time progress feedback with ETA
- Configurable similarity thresholds (50%-100%)
- Multiple selection strategies (keep largest, newest, etc.)

### File Format Support
Planned support for: `.mp4`, `.avi`, `.mkv`, `.mov`, `.wmv`, `.flv`

## Project Structure (Planned)

```
DupFinder/
├── src/
│   ├── main.py              # Application entry point
│   ├── gui/                 # GUI components
│   ├── scanner/             # File scanning logic
│   ├── detector/            # Duplicate detection algorithms
│   ├── processor/           # File operation handlers
│   └── utils/               # Shared utilities
├── tests/                   # Test suite
├── requirements.txt         # Python dependencies
├── README.md               # User documentation
└── 需求文档.md             # Requirements specification (Chinese)
```

## Next Steps for Implementation

1. Set up project structure and virtual environment
2. Create requirements.txt with core dependencies
3. Implement basic GUI framework
4. Develop file scanning functionality
5. Add metadata-based pre-filtering
6. Implement content-based duplicate detection
7. Add result display and user selection interface
8. Implement safe file operations
9. Add comprehensive testing
10. Package for distribution

## Cross-Platform Considerations

The tool is designed to support Windows, macOS, and Linux. Pay attention to:
- Path handling differences
- File system permissions
- GUI framework compatibility
- FFmpeg installation and path detection