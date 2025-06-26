# Mes Explorer - Terminal File Explorer

Mes Explorer is a modern, feature-rich terminal file explorer with intuitive keyboard and mouse controls. Designed for efficiency and ease of use, it brings graphical file management capabilities to your terminal.

## Features

- 🖱️ **Full Mouse Support**: Click, double-click, right-click, and scroll
- 🎨 **Colorful Icons**: Visual file type recognition
- 🔍 **Fast Search**: Instant recursive search as you type
- 📄 **File Previews**: Syntax-highlighted code, image information, and file metadata
- 🛠️ **File Operations**: Create, rename, delete files and directories
- 📋 **Context Menu**: Quick access to common file operations
- 🧩 **Vim Integration**: Open files directly in Vim/Neovim
- ⚙️ **Customizable**: Toggle hidden files, sort options, and other preferences

## Installation

### Prerequisites

- Python 3.7 or higher
- `pip` package manager


### From Source

## Dependencies

- Python 3.7+
- curses (standard library)
- pygments (for syntax highlighting)
- pyperclip (for copying paths)

Install additional dependencies:

```bash
pip install pygments pyperclip
```

```bash
git clone https://github.com/yourusername/mes-explorer.git
cd mes-explorer
pip install .
```

## Usage

Launch the file explorer:

```bash
mes
```

### Keyboard Navigation

- `↑/k`: Move up
- `↓/j`: Move down
- `Enter`: Enter directory or open file
- `b`: Go back one directory
- `q`: Exit

### File Management

- `n`: Create new file
- `m`: Create new directory
- `F2`: Rename file or directory
- `d`: Delete file or directory (with confirmation)
- `Space`: Show context menu

### Searching

- `/`: Start fuzzy search
- `ESC`: Exit search
- Type to filter file list dynamically

### Display Options

- `h`: Toggle visibility of hidden files
- `r`: Reload the current directory
- `?`: Show help overlay

### Mouse Actions

- Left click: Highlight file or directory
- Double-click: Enter directory or open file
- Right click: Reveal context menu
- Mouse wheel: Scroll file list




## License

Mes Explorer is licensed under the MIT License. See LICENSE for details.

