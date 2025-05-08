"""
Logger utility module for styled logging
"""
import datetime
from utils.colors import Colors

class Logger:
    @staticmethod
    def timestamp():
        """Get current timestamp in formatted string"""
        return datetime.datetime.now().strftime("%H:%M:%S")
    
    @staticmethod
    def format_line(line_length=80):
        """Format a horizontal line with some style"""
        return f"{Colors.PINK}{Colors.BOLD}{'─' * line_length}{Colors.RESET}"
    
    @staticmethod
    def info(message):
        """Log informational message"""
        timestamp = Logger.timestamp()
        print(f"{Colors.BRIGHT_BLUE}[{timestamp}] {Colors.BLUE}INFO{Colors.RESET} │ {message}")
    
    @staticmethod
    def success(message):
        """Log success message"""
        timestamp = Logger.timestamp()
        print(f"{Colors.BRIGHT_GREEN}[{timestamp}] {Colors.GREEN}SUCCESS{Colors.RESET} │ {message}")
    
    @staticmethod
    def warning(message):
        """Log warning message"""
        timestamp = Logger.timestamp()
        print(f"{Colors.BRIGHT_YELLOW}[{timestamp}] {Colors.YELLOW}WARNING{Colors.RESET} │ {message}")
    
    @staticmethod
    def error(message):
        """Log error message"""
        timestamp = Logger.timestamp()
        print(f"{Colors.BRIGHT_RED}[{timestamp}] {Colors.RED}ERROR{Colors.RESET} │ {message}")
    
    @staticmethod
    def debug(message):
        """Log debug message"""
        timestamp = Logger.timestamp()
        print(f"{Colors.BRIGHT_MAGENTA}[{timestamp}] {Colors.MAGENTA}DEBUG{Colors.RESET} │ {message}")
    
    @staticmethod
    def trace(message):
        """Log trace message (low-level details)"""
        timestamp = Logger.timestamp()
        print(f"{Colors.BRIGHT_CYAN}[{timestamp}] {Colors.CYAN}TRACE{Colors.RESET} │ {message}")
    
    @staticmethod
    def step(number, total, message):
        """Log a step in a multi-step process"""
        timestamp = Logger.timestamp()
        progress = f"({number}/{total})"
        print(f"{Colors.PINK}[{timestamp}] {Colors.PINK}STEP {progress}{Colors.RESET} │ {message}")
    
    @staticmethod
    def header(title):
        """Log a header to separate logical sections"""
        print(f"\n{Colors.PINK}{Colors.BOLD}{'━' * 20} {title.upper()} {'━' * 20}{Colors.RESET}\n")
    
    @staticmethod
    def command(cmd):
        """Log a command being executed"""
        timestamp = Logger.timestamp()
        print(f"{Colors.BRIGHT_WHITE}[{timestamp}] {Colors.WHITE}CMD{Colors.RESET} │ {Colors.BOLD}$ {cmd}{Colors.RESET}")
    
    @staticmethod
    def result(result_text):
        """Log a command result"""
        lines = result_text.strip().split('\n')
        for line in lines:
            print(f"{Colors.BRIGHT_BLACK}  │ {line}{Colors.RESET}")
    
    @staticmethod
    def status(status, message):
        """Log a status update with custom status tag"""
        timestamp = Logger.timestamp()
        print(f"{Colors.CYAN}[{timestamp}] {Colors.BRIGHT_CYAN}{status.upper()}{Colors.RESET} │ {message}")
    
    @staticmethod
    def prompt(message):
        """Display a user prompt message"""
        print(f"{Colors.YELLOW}? {Colors.BRIGHT_YELLOW}{message}{Colors.RESET}")
        
    @staticmethod
    def input(message):
        """Get user input with styled prompt"""
        return input(f"{Colors.PINK}? {Colors.PINK}{message}{Colors.RESET} ")
        
    @staticmethod
    def progress(count, total, prefix='', suffix='', length=30):
        """Show a progress bar"""
        filled_length = int(length * count // total)
        bar = f"{Colors.GREEN}{'█' * filled_length}{Colors.BRIGHT_BLACK}{'░' * (length - filled_length)}{Colors.RESET}"
        percent = f"{Colors.BRIGHT_GREEN}{100 * (count / float(total)):.1f}%{Colors.RESET}"
        print(f"\r{Colors.CYAN}{prefix}{Colors.RESET} │ {bar} │ {percent} {Colors.BRIGHT_CYAN}{suffix}{Colors.RESET}", end='\r')
        if count == total:
            print() 