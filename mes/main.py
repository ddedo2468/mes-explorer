#!/usr/bin/env python3
import os, curses, string, stat, time, subprocess, sys, pyperclip, shutil
from pygments import highlight
from pygments.lexers import guess_lexer_for_filename, TextLexer
from pygments.formatters import NullFormatter

FILE_ICONS = {
    ".py": "🐍", ".js": "🟨", ".ts": "🟦", ".html": "🌐", ".htm": "🌐",
    ".css": "🎨", ".c": "🅲", ".cpp": "➕➕", ".go": "🐹", ".rs": "🦀",
    ".php": "🐘", ".java": "☕", ".rb": "💎", ".md": "📄", ".txt": "📄",
    ".sh": "🐚", ".bash": "🐚", ".json": "📋", ".xml": "📋",
    ".yml": "⚙️", ".yaml": "⚙️", ".sql": "🗃️", ".log": "📜",
    ".conf": "⚙️", ".cfg": "⚙️", ".ini": "⚙️", ".zip": "📦",
    ".tar": "📦", ".gz": "📦", ".7z": "📦", ".rar": "📦",
    ".jpg": "🖼️", ".jpeg": "🖼️", ".png": "🖼️", ".gif": "🖼️",
    ".pdf": "📕", ".doc": "📄", ".docx": "📄", ".mp3": "🎵",
    ".mp4": "🎬", ".avi": "🎬", ".mkv": "🎬"
}

CONFIG = {
    'show_hidden': False,
    'sort_dirs_first': True,
    'preview_max_lines': 50,
    'search_max_depth': 3,
    'confirm_actions': True
}

def file_emoji(path_name):
    if os.path.isdir(path_name):
        return "📂"
    elif os.path.islink(path_name):
        return "🔗"
    ext = os.path.splitext(path_name)[1].lower()
    return FILE_ICONS.get(ext, "📄")

def is_text_file(path_name, max_bytes=1024):
    try:
        with open(path_name, "rb") as f:
            chunk = f.read(max_bytes)
        if not chunk:
            return True
        return all(chr(b) in string.printable or b in b"\n\r\t" for b in chunk)
    except:
        return False



def show_file_properties(stdscr, path_name):
    """Show detailed file properties in a popup"""
    h, w = stdscr.getmaxyx()
    popup_h, popup_w = min(18, h - 4), min(60, w - 4)
    start_y, start_x = (h - popup_h) // 2, (w - popup_w) // 2

    try:
        st = os.stat(path_name)
        size = os.path.getsize(path_name)
        mode = stat.filemode(st.st_mode)
        mtime = time.strftime("%Y-%m-%d %H:%M:%S", time.localtime(st.st_mtime))
        ctime = time.strftime("%Y-%m-%d %H:%M:%S", time.localtime(st.st_ctime))

        props = [
            f"Name: {os.path.basename(path_name)}",
            f"Path: {path_name}",
            f"Size: {format_size(size)} ({size} bytes)",
            f"Type: {'Directory' if os.path.isdir(path_name) else 'File'}",
            f"Permissions: {mode}",
            f"Modified: {mtime}",
            f"Created: {ctime}",
            f"Owner: {st.st_uid}",
            f"Group: {st.st_gid}",
            f"Inode: {st.st_ino}"
        ]

        popup_win = curses.newwin(popup_h, popup_w, start_y, start_x)
        popup_win.box()
        popup_win.addstr(0, 2, " Properties ", curses.A_BOLD)

        for i, line in enumerate(props):
            if i < popup_h - 3:
                popup_win.addstr(i + 1, 2, line[:popup_w - 4])

        popup_win.addstr(popup_h - 2, 2, "Press any key to close...", curses.A_DIM)
        popup_win.refresh()
        popup_win.getch()

    except Exception as e:
        pass

def show_context_menu(stdscr, y, x, options):
    """Show a simple context menu at (y,x)"""
    h, w = stdscr.getmaxyx()
    menu_h = len(options) + 2
    menu_w = max(len(opt[0]) for opt in options) + 4
    menu_w = max(menu_w, 25)

    if y + menu_h > h:
        y = h - menu_h
    if x + menu_w > w:
        x = w - menu_w

    menu_win = curses.newwin(menu_h, menu_w, y, x)
    menu_win.keypad(True)
    menu_win.box()
    menu_win.addstr(0, 2, " Actions ", curses.A_BOLD)

    for i, (text, _) in enumerate(options):
        menu_win.addstr(i+1, 2, text)


    menu_win.addstr(menu_h-1, 2, "Esc to close", curses.A_DIM)

    menu_win.refresh()

    while True:
        try:
            key = menu_win.getch()

            if key == 27:
                return None

            elif key == curses.KEY_MOUSE:
                _, mx, my, _, bstate = curses.getmouse()
                if not (y <= my < y + menu_h and x <= mx < x + menu_w):
                    return None

            elif 0 <= key - ord('1') < len(options):
                return options[key - ord('1')][1]

        except curses.error:
            pass

def is_code_file(path_name):
    return os.path.splitext(path_name)[1].lower() in FILE_ICONS

def get_file_size_color(size_bytes):
    """Return color based on file size"""
    if size_bytes > 1024 * 1024 * 100:
        return curses.color_pair(5)
    elif size_bytes > 1024 * 1024 * 10:
        return curses.color_pair(6)
    else:
        return curses.color_pair(3)

def list_dir(path="."):
    try:
        entries = os.listdir(path)


        if not CONFIG['show_hidden']:
            entries = [e for e in entries if not e.startswith('.')]


        if CONFIG['sort_dirs_first']:
            dirs = [e for e in entries if os.path.isdir(os.path.join(path, e))]
            files = [e for e in entries if not os.path.isdir(os.path.join(path, e))]
            return sorted(dirs) + sorted(files)
        else:
            return sorted(entries)
    except PermissionError:
        return []

def search_files_recursive(root_path, query, max_results=100):
    """Enhanced recursive search with better depth control"""
    results = []
    query_lower = query.lower()

    def search_in_dir(current_path, relative_path="", depth=0):
        if len(results) >= max_results or depth > CONFIG['search_max_depth']:
            return

        try:
            entries = os.listdir(current_path)
            for entry in entries:
                if len(results) >= max_results:
                    break

                if not CONFIG['show_hidden'] and entry.startswith('.'):
                    continue

                full_path = os.path.join(current_path, entry)
                display_path = os.path.join(relative_path, entry) if relative_path else entry

                if query_lower in entry.lower():
                    results.append((display_path, full_path))

                if os.path.isdir(full_path):
                    search_in_dir(full_path, display_path, depth + 1)

        except (PermissionError, OSError):
            pass

    search_in_dir(root_path)
    return results

def format_size(size_bytes):
    """Convert bytes to human readable format"""
    if size_bytes < 1024:
        return f"{size_bytes}B"
    elif size_bytes < 1024 * 1024:
        return f"{size_bytes/1024:.1f}K"
    elif size_bytes < 1024 * 1024 * 1024:
        return f"{size_bytes/(1024*1024):.1f}M"
    else:
        return f"{size_bytes/(1024*1024*1024):.1f}G"

def get_file_info(path_name):
    """Get enhanced file information"""
    try:
        st = os.stat(path_name)
        size = format_size(st.st_size)
        mode = stat.filemode(st.st_mode)
        mtime = time.strftime("%Y-%m-%d %H:%M", time.localtime(st.st_mtime))
        return f"{mode} {size:>8} {mtime}"
    except:
        return "Unknown"

def get_preview(path_name, h, w):
    try:
        if os.path.isdir(path_name):
            contents = list_dir(path_name)[:CONFIG['preview_max_lines']]
            info = get_file_info(path_name)
            preview = f"{file_emoji(path_name)} Directory\n{info}\n\nContents ({len(contents)} items):\n"

            if not contents:
                preview += "(Empty directory)"
            else:
                for f in contents:
                    f_path = os.path.join(path_name, f)
                    size_info = ""
                    try:
                        if not os.path.isdir(f_path):
                            size = os.path.getsize(f_path)
                            size_info = f" ({format_size(size)})"
                    except:
                        pass
                    preview += f"{file_emoji(f_path)} {f}{size_info}\n"

                total_items = len(os.listdir(path_name))
                if total_items > len(contents):
                    preview += f"... and {total_items - len(contents)} more items"
            return preview

        elif path_name.lower().endswith((".jpg", ".jpeg", ".png", ".gif", ".bmp", ".svg")):
            info = get_file_info(path_name)
            return f"{file_emoji(path_name)} Image File\n{info}\n\n(Use external viewer to open)\n\nPath: {path_name}"

        elif path_name.lower().endswith((".pdf", ".doc", ".docx", ".xls", ".xlsx")):
            info = get_file_info(path_name)
            return f"{file_emoji(path_name)} Document\n{info}\n\n(Binary document - no preview)\n\nPath: {path_name}"

        elif is_code_file(path_name) or is_text_file(path_name):
            info = get_file_info(path_name)
            try:
                with open(path_name, 'r', encoding='utf-8', errors='ignore') as f:
                    content = f.read(4000)

                lexer = (
                    guess_lexer_for_filename(path_name, content)
                    if is_code_file(path_name)
                    else TextLexer()
                )

                preview = f"{file_emoji(path_name)} {os.path.basename(path_name)}\n{info}\n\n"
                highlighted = highlight(content, lexer, NullFormatter())

                lines = highlighted.split('\n')
                max_lines = min(h - 6, CONFIG['preview_max_lines'])
                if len(lines) > max_lines:
                    total_lines = len(lines)
                    lines = lines[:max_lines]
                    lines.append(f"... (showing {max_lines} of {total_lines} lines)")

                preview += '\n'.join(lines)
                return preview
            except Exception as e:
                return f"{file_emoji(path_name)} Text File\n{info}\n\nError reading file: {e}"
        else:
            info = get_file_info(path_name)
            return f"{file_emoji(path_name)} Binary File\n{info}\n\nPath: {path_name}"

    except Exception as e:
        return f"{file_emoji(path_name)} Error\n{str(e)}"

def open_file_external(path_name):
    """Open file with system default application"""
    try:
        if sys.platform.startswith('linux'):

            subprocess.run(['xdg-open', path_name], 
                         stdout=subprocess.DEVNULL, 
                         stderr=subprocess.DEVNULL, 
                         check=False)
        elif sys.platform == 'darwin':
            subprocess.run(['open', path_name], 
                         stdout=subprocess.DEVNULL, 
                         stderr=subprocess.DEVNULL, 
                         check=False)
        elif sys.platform == 'win32':
            os.startfile(path_name)
        return True
    except Exception:
        return False

def show_help_popup(stdscr):
    """Show help popup"""
    h, w = stdscr.getmaxyx()
    popup_h, popup_w = min(22, h - 4), min(65, w - 4)
    start_y, start_x = (h - popup_h) // 2, (w - popup_w) // 2

    help_win = curses.newwin(popup_h, popup_w, start_y, start_x)
    help_win.box()
    help_win.addstr(0, 2, " Help ", curses.A_BOLD)

    help_text = [
        "Navigation:",
        "  ↑/k, ↓/j    - Move up/down",
        "  Enter       - Enter directory",
        "  b           - Go back (parent directory)",
        "",
        "Operations:",
        "  n           - Create new file",
        "  m           - Create new directory",
        "  F2          - Rename selected item",
        "  d           - Delete selected item",
        "  o           - Open file with system default",
        "",
        "Mouse Controls:",
        "  Left click  - Select file/directory",
        "  Double click- Open file/enter directory",
        "  Right click - Show context menu",
        "",
        "Context Menu:",
        "  1. Open with default",
        "  2. Open with Vim",
        "  3. Rename",
        "  4. Delete",
        "  5. Copy Path",
        "  6. Properties",
        "",
        "Keyboard Shortcuts:",
        "  Space       - Show context menu",
        "  /           - Start search",
        "  Esc         - Exit search",
        "  h           - Toggle hidden files",
        "  r           - Refresh current directory",
        "  ?           - Show this help",
        "  q           - Quit",
        "",
        "Press any key to close..."
    ]

    for i, line in enumerate(help_text):
        if i < popup_h - 3:
            help_win.addstr(i + 1, 2, line[:popup_w - 4])

    help_win.refresh()
    help_win.getch()

def draw_status_line(stdscr, path, search_mode, search_query, current_file="", file_count=0):
    """Enhanced status line with more information"""
    try:
        h, w = stdscr.getmaxyx()
        if h < 2 or w < 10:
            return

        status_y = h - 1
        stdscr.move(status_y, 0)
        stdscr.clrtoeol()

        if search_mode:
            status = f"Search: {search_query}"
            cursor_pos = len(status)
            if len(status) > w - 2:
                status = status[:w - 5] + "..."
                cursor_pos = len(status)
            stdscr.addnstr(status_y, 0, status, w - 1, curses.A_REVERSE)
            if cursor_pos < w - 1:
                stdscr.addstr(status_y, cursor_pos, "_", curses.A_REVERSE | curses.A_BLINK)
        else:
            path_display = os.path.basename(path) or path
            status_left = f"📁 {path_display}"
            if file_count > 0:
                status_left += f" ({file_count} items)"

            if current_file:
                status_left += f" | {current_file}"


            help_text = " ?:help q:quit /:search [mouse enabled]"
            available_space = w - len(help_text) - 1

            if len(status_left) > available_space:
                status_left = status_left[:available_space - 3] + "..."

            stdscr.addnstr(status_y, 0, status_left[:available_space], min(available_space, len(status_left)))

            help_start = w - len(help_text)
            if help_start > 0:
                stdscr.addnstr(status_y, help_start, help_text, len(help_text), curses.A_DIM)

    except curses.error:
        pass

def draw_files(stdscr, path, files, current_idx, offset, search_mode=False, clicked_idx=-1):
    """Draw the file list with selection and click feedback"""
    try:
        h, w = stdscr.getmaxyx()
        left_width = w // 2

        for i in range(h - 1):
            stdscr.move(i, 0)
            stdscr.clrtoeol()

        title_text = "🔍 Search Results" if search_mode else f"📁 {os.path.basename(path) or path}"
        if not search_mode and files:
            hidden_count = len([f for f in os.listdir(path) if f.startswith('.')]) if os.path.isdir(path) else 0
            if hidden_count > 0 and not CONFIG['show_hidden']:
                title_text += f" (+{hidden_count} hidden)"

        stdscr.addnstr(0, 1, title_text[:left_width-2], left_width-2, curses.A_BOLD | curses.color_pair(1))
        stdscr.addnstr(1, 1, "─" * (left_width - 3), left_width - 3, curses.color_pair(3))

        if not files:
            empty_text = "(No matches)" if search_mode else "(Empty directory)"
            stdscr.addnstr(3, 3, empty_text, left_width - 6, curses.color_pair(3))
            return offset, {}

        max_visible = h - 4

        if current_idx < offset:
            offset = current_idx
        elif current_idx >= offset + max_visible:
            offset = current_idx - max_visible + 1

        click_areas = {}

        for i, f in enumerate(files[offset:offset + max_visible]):
            y_pos = i + 2
            if y_pos >= h - 2:
                break

            click_areas[y_pos] = i + offset

            if isinstance(f, tuple):
                display_name, full_path = f
                basename = os.path.basename(display_name)
                icon = file_emoji(full_path)
            else:
                display_name = f
                full_path = os.path.join(path, f)
                basename = f
                icon = file_emoji(full_path)

            color = curses.color_pair(3)
            if os.path.isdir(full_path):
                color = curses.color_pair(1)
            elif os.access(full_path, os.X_OK):
                color = curses.color_pair(2)

            if i + offset == current_idx:
                color |= curses.A_REVERSE

            if i + offset == clicked_idx:
                color |= curses.A_BLINK
                stdscr.addnstr(y_pos, 2, ">", 1, color)

            file_display = f"{icon} {basename}"

            if not os.path.isdir(full_path):
                try:
                    size = os.path.getsize(full_path)
                    size_str = format_size(size)
                    name_width = left_width - len(size_str) - 8
                    if len(file_display) > name_width:
                        file_display = file_display[:name_width-3] + "..."
                    file_display = f"{file_display:<{name_width}} {size_str:>6}"
                except:
                    pass

            max_display_width = left_width - 4
            if len(file_display) > max_display_width:
                file_display = file_display[:max_display_width-3] + "..."

            stdscr.addnstr(y_pos, 2, file_display, max_display_width, color)

        return offset, click_areas

    except curses.error:
        return offset, {}

def draw_preview(stdscr, path, files, current_idx, search_mode=False):
    """Enhanced preview with scroll indicators"""
    try:
        h, w = stdscr.getmaxyx()
        preview_start = w // 2 + 1
        preview_width = w - preview_start - 1

        for i in range(h - 1):
            stdscr.move(i, preview_start)
            stdscr.clrtoeol()

        for i in range(h - 1):
            stdscr.addch(i, w // 2, "│", curses.color_pair(3))

        if not files or current_idx >= len(files):
            return

        if isinstance(files[current_idx], tuple):
            display_name, preview_path = files[current_idx]
        else:
            preview_path = os.path.abspath(os.path.join(path, files[current_idx]))

        preview = get_preview(preview_path, h - 2, preview_width)

        preview_lines = preview.splitlines()
        available_lines = h - 3

        for i, line in enumerate(preview_lines):
            if i >= available_lines:
                stdscr.addstr(h - 2, preview_start + preview_width - 3, "...", curses.A_DIM)
                break
            if len(line) > preview_width:
                line = line[:preview_width - 3] + "..."
            stdscr.addnstr(i + 1, preview_start + 1, line, preview_width - 1)

    except curses.error:
        pass

def handle_mouse_click(x, y, click_areas, files, current_idx, button_state):
    """Handle mouse clicks and return new current_idx and action"""
    if y in click_areas:
        clicked_idx = click_areas[y]

        if button_state & curses.BUTTON1_PRESSED:
            return clicked_idx, "select"
        elif button_state & curses.BUTTON1_DOUBLE_CLICKED:
            return clicked_idx, "enter"
        elif button_state & curses.BUTTON3_PRESSED:
            return clicked_idx, "open_external"

    return current_idx, "none"


def open_with_vim(file_path):
    """Open file in Vim/Neovim, restoring terminal after exit"""
    curses.def_prog_mode()
    curses.endwin()

    try:
        if shutil.which('nvim'):
            subprocess.run(['nvim', file_path])
        elif shutil.which('vim'):
            subprocess.run(['vim', file_path])
        else:
            print("Error: Neither neovim nor vim found in PATH")
            print("Press any key to continue...")
            sys.stdin.read(1)
    except Exception as e:
        print(f"Error opening editor: {e}")
        print("Press any key to continue...")
        sys.stdin.read(1)

    curses.reset_prog_mode()
    curses.curs_set(0)
    curses.noecho()
    curses.cbreak()


def get_input_popup(stdscr, prompt):
    """Show input popup and return user input"""
    h, w = stdscr.getmaxyx()
    popup_h, popup_w = 5, min(60, w - 4)
    start_y, start_x = (h - popup_h) // 2, (w - popup_w) // 2

    popup_win = curses.newwin(popup_h, popup_w, start_y, start_x)
    popup_win.box()
    popup_win.addstr(0, 2, f" {prompt} ", curses.A_BOLD)

    curses.curs_set(1)
    curses.echo()

    popup_win.addstr(1, 2, "> ")
    popup_win.refresh()


    input_str = popup_win.getstr(1, 4, popup_w - 6).decode('utf-8')

    curses.curs_set(0)
    curses.noecho()

    return input_str.strip()

def confirm_popup(stdscr, message):
    """Show confirmation popup, return True if confirmed"""
    h, w = stdscr.getmaxyx()
    popup_h, popup_w = 5, min(60, w - 4)
    start_y, start_x = (h - popup_h) // 2, (w - popup_w) // 2

    popup_win = curses.newwin(popup_h, popup_w, start_y, start_x)
    popup_win.box()
    popup_win.addstr(0, 2, " Confirm ", curses.A_BOLD)

    popup_win.addstr(1, 2, message[:popup_w - 4])
    popup_win.addstr(2, 2, "Press 'y' to confirm, any other key to cancel")

    popup_win.refresh()
    key = popup_win.getch()

    return key == ord('y')

def create_file_or_dir(path, is_file=True):
    """Create a new file or directory"""
    try:
        if is_file:
            with open(path, 'w'):
                pass
        else:
            os.mkdir(path)
        return True
    except Exception as e:
        return False

def rename_file_or_dir(old_path, new_path):
    """Rename a file or directory"""
    try:
        os.rename(old_path, new_path)
        return True
    except Exception as e:
        return False

def delete_file_or_dir(path):
    """Delete a file or directory"""
    try:
        if os.path.isdir(path):
            if CONFIG['confirm_actions']:
                shutil.rmtree(path)
            else:
                os.rmdir(path)
        else:
            os.remove(path)
        return True
    except Exception as e:
        return False



def show_file_context(stdscr, full_path, y=None, x=None):
    """Show context menu for a file"""
    options = [
        ("1. Open with default", "open_default"),
        ("2. Open with Vim", "open_vim"),
        ("3. Rename", "rename"),
        ("4. Delete", "delete"),
        ("5. Copy Path", "copy_path"),
        ("6. Properties", "properties")
    ]

    if y is None or x is None:
        h, w = stdscr.getmaxyx()
        y, x = h//2, w//2

    action = show_context_menu(stdscr, y, x, options)
    if action == "open_default":
        open_file_external(full_path)
    elif action == "open_vim":
        open_with_vim(full_path)
    elif action == "rename":
        new_name = get_input_popup(stdscr, f"Rename '{os.path.basename(full_path)}' to:")
        if new_name:
            new_path = os.path.join(os.path.dirname(full_path), new_name)
            if rename_file_or_dir(full_path, new_path):
                return True
    elif action == "delete":
        if confirm_popup(stdscr, f"Delete '{os.path.basename(full_path)}' permanently?"):
            if delete_file_or_dir(full_path):
                return True
    elif action == "copy_path":
        try:
            pyperclip.copy(full_path)
        except:
            pass
    elif action == "properties":
        show_file_properties(stdscr, full_path)

    return False


def main(stdscr):
    curses.mousemask(curses.ALL_MOUSE_EVENTS | curses.REPORT_MOUSE_POSITION |
                    curses.BUTTON4_PRESSED | curses.BUTTON5_PRESSED)
    curses.mouseinterval(0)

    curses.curs_set(0)
    curses.start_color()
    curses.init_pair(1, curses.COLOR_BLUE, curses.COLOR_BLACK)
    curses.init_pair(2, curses.COLOR_GREEN, curses.COLOR_BLACK)
    curses.init_pair(3, curses.COLOR_WHITE, curses.COLOR_BLACK)
    curses.init_pair(4, curses.COLOR_YELLOW, curses.COLOR_BLACK)
    curses.init_pair(5, curses.COLOR_RED, curses.COLOR_BLACK)

    path = os.getcwd()
    files = list_dir(path)
    all_files = list(files)
    search_results = []
    current_idx = 0
    offset = 0
    search_mode = False
    search_query = ""

    last_click_time = 0
    last_click_idx = -1
    clicked_idx = -1

    while True:
        offset, click_areas = draw_files(stdscr, path, files, current_idx, offset, search_mode, clicked_idx)
        draw_preview(stdscr, path, files, current_idx, search_mode)
        current_file = files[current_idx] if files else ""
        draw_status_line(stdscr, path, search_mode, search_query, current_file, len(files))
        stdscr.refresh()

        try:
            key = stdscr.getch()
        except KeyboardInterrupt:
            break

        if key == curses.KEY_MOUSE:
            try:
                _, x, y, _, button_state = curses.getmouse()
                current_time = time.time()

                if button_state & curses.BUTTON4_PRESSED:
                    current_idx = max(0, current_idx - 3)
                    clicked_idx = -1

                elif button_state & curses.BUTTON5_PRESSED:
                    if files:
                        current_idx = min(len(files) - 1, current_idx + 3)
                    clicked_idx = -1

                elif button_state & curses.BUTTON1_PRESSED and not search_mode:
                    if y in click_areas:
                        clicked_idx = click_areas[y]
                        current_idx = clicked_idx

                        if (current_time - last_click_time < 0.5 and 
                            clicked_idx == last_click_idx):

                            if files and clicked_idx < len(files):
                                if isinstance(files[clicked_idx], tuple):
                                    _, full_path = files[clicked_idx]
                                else:
                                    full_path = os.path.join(path, files[clicked_idx])

                                if os.path.isdir(full_path):
                                    path = full_path
                                    files = list_dir(path)
                                    all_files = list(files)
                                    current_idx, offset = 0, 0
                                else:
                                    open_file_external(full_path)

                        last_click_time = current_time
                        last_click_idx = clicked_idx

                elif button_state & curses.BUTTON3_PRESSED and not search_mode:
                    if y in click_areas:
                        current_idx = click_areas[y]
                        if files and current_idx < len(files):
                            if isinstance(files[current_idx], tuple):
                                _, full_path = files[current_idx]
                            else:
                                full_path = os.path.join(path, files[current_idx])
                            show_file_context(stdscr, full_path, y, x)

            except curses.error:
                pass

        elif search_mode:
            if key in (curses.KEY_BACKSPACE, 127, 8, curses.KEY_DC):
                if search_query:
                    search_query = search_query[:-1]
                    if search_query:
                        search_results = search_files_recursive(path, search_query)
                        files = search_results
                    else:
                        files = list(all_files)
                        search_results = []
                    current_idx = 0
                    offset = 0
            elif key == 27:
                search_mode = False
                search_query = ""
                files = list(all_files)
                current_idx = 0
                offset = 0
            elif key == curses.KEY_ENTER or key == ord("\n") or key == ord("\r"):
                search_mode = False
                if search_results:
                    files = search_results
                current_idx = 0
                offset = 0
            elif 32 <= key <= 126:
                search_query += chr(key)
                search_results = search_files_recursive(path, search_query)
                files = search_results
                current_idx = 0
                offset = 0
        else:
            if key == ord("q"):
                break
            elif key == ord(" "):
                if files and current_idx < len(files):
                    if isinstance(files[current_idx], tuple):
                        _, full_path = files[current_idx]
                    else:
                        full_path = os.path.join(path, files[current_idx])
                    show_file_context(stdscr, full_path)
            elif key == ord("/"):
                search_mode = True
                search_query = ""
                all_files = list(files)
            elif key == ord("?"):
                show_help_popup(stdscr)
                stdscr.clear()
            elif key == ord("b"):
                new_path = os.path.dirname(path) or "/"
                if os.path.isdir(new_path) and new_path != path:
                    path = new_path
                    files = list_dir(path)
                    all_files = list(files)
                    current_idx, offset = 0, 0
            elif key == ord("r"):
                files = list_dir(path)
                all_files = list(files)
                current_idx = min(current_idx, len(files) - 1) if files else 0
            elif key == ord("o"):
                if files and current_idx < len(files):
                    if isinstance(files[current_idx], tuple):
                        _, full_path = files[current_idx]
                    else:
                        full_path = os.path.join(path, files[current_idx])
                    open_file_external(full_path)
            elif key == ord("h"):
                CONFIG['show_hidden'] = not CONFIG['show_hidden']
                files = list_dir(path)
                all_files = list(files)
                current_idx = min(current_idx, len(files) - 1) if files else 0
                offset = 0
            elif key in (curses.KEY_UP, ord("k")):
                if files:
                    current_idx = max(0, current_idx - 1)
            elif key in (curses.KEY_DOWN, ord("j")):
                if files:
                    current_idx = min(current_idx + 1, len(files) - 1)
            elif key == curses.KEY_ENTER or key == ord("\n") or key == ord("\r"):
                if files and current_idx < len(files):
                    if isinstance(files[current_idx], tuple):
                        _, full_path = files[current_idx]
                    else:
                        full_path = os.path.join(path, files[current_idx])

                    if os.path.isdir(full_path):
                        path = full_path
                        files = list_dir(path)
                        all_files = list(files)
                        current_idx, offset = 0, 0
            elif key == ord('n'):
                name = get_input_popup(stdscr, "New file name:")
                if name:
                    full_path = os.path.join(path, name)
                    if create_file_or_dir(full_path, is_file=True):
                        files = list_dir(path)
                        all_files = list(files)

            elif key == ord('m'):
                name = get_input_popup(stdscr, "New directory name:")
                if name:
                    full_path = os.path.join(path, name)
                    if create_file_or_dir(full_path, is_file=False):
                        files = list_dir(path)
                        all_files = list(files)

            elif key == curses.KEY_F2:
                if files and current_idx < len(files):
                    if isinstance(files[current_idx], tuple):
                        _, full_path = files[current_idx]
                    else:
                        full_path = os.path.join(path, files[current_idx])

                    new_name = get_input_popup(stdscr, f"Rename '{os.path.basename(full_path)}' to:")
                    if new_name:
                        new_path = os.path.join(os.path.dirname(full_path), new_name)
                        if rename_file_or_dir(full_path, new_path):
                            files = list_dir(path)
                            all_files = list(files)

            elif key == ord('d'):
                if files and current_idx < len(files):
                    if isinstance(files[current_idx], tuple):
                        _, full_path = files[current_idx]
                    else:
                        full_path = os.path.join(path, files[current_idx])

                    if confirm_popup(stdscr, f"Delete '{os.path.basename(full_path)}' permanently?"):
                        if delete_file_or_dir(full_path):
                            files = list_dir(path)
                            all_files = list(files)
                            current_idx = min(current_idx, len(files) - 1) if files else 0

        if clicked_idx != -1 and time.time() - last_click_time > 0.3:
            clicked_idx = -1

    print("\033[?1003l", end="")
