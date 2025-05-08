"""
Banner utility module for displaying fancy banners
"""
from utils.colors import Colors

def print_banner():
    colored_banner = ""
    
    combined_banner = """
         ,                 ██████╗ ██╗███╗   ██╗██╗  ██╗███████╗██╗  ██╗ █████╗ ██████╗ ██╗  ██╗
       .';                 ██╔══██╗██║████╗  ██║██║ ██╔╝██╔════╝██║  ██║██╔══██╗██╔══██╗██║ ██╔╝
   .-'` .'                 ██████╔╝██║██╔██╗ ██║█████╔╝ ███████╗███████║███████║██████╔╝█████╔╝ 
 ,`.-'-.`\\                 ██╔═══╝ ██║██║╚██╗██║██╔═██╗ ╚════██║██╔══██║██╔══██║██╔══██╗██╔═██╗ 
; /     '-'                ██║     ██║██║ ╚████║██║  ██╗███████║██║  ██║██║  ██║██║  ██║██║  ██╗
| \\       ,-,              ╚═╝     ╚═╝╚═╝  ╚═══╝╚═╝  ╚═╝╚══════╝╚═╝  ╚═╝╚═╝  ╚═╝╚═╝  ╚═╝╚═╝  ╚═╝
\\  '-.__   )_`'._     
 '.     ```      ``'--._          
.-' ,                   `'-.   
 '-'`-._           ((   o   )    
        `'--....(`- ,__..--'     
                 '-'`            
    """
    
    # Print combined banner with pink color
    for line in combined_banner.split('\n'):
        colored_banner += f"{Colors.PINK}{line}{Colors.RESET}\n"
    
    colored_banner += f"{Colors.PINK}{Colors.BOLD}{'★'*20} MONAD BOT AUTOMATION SUITE v1.0 {'★'*20}{Colors.RESET}"
    print(colored_banner)

def print_section(title):
    border = "═" * 50
    print(f"\n{Colors.YELLOW}{border}{Colors.RESET}")
    print(f"{Colors.BOLD}{Colors.CYAN}    {title}{Colors.RESET}")
    print(f"{Colors.YELLOW}{border}{Colors.RESET}\n") 