import tkinter as tk
from tkinter import ttk, messagebox
import subprocess
import threading
import time
import datetime
import os
import shutil
from mcrcon import MCRcon

# Constants (update these with actual paths and credentials)
SERVER_EXE_PATH = r"C:\Server\Palworld\steamapps\common\PalServer\PalServer.exe"
STEAMCMD_PATH = r"C:\Server\Palworld\steamcmd.exe"
SAVE_GAMES_DIR = r"C:\Server\Palworld\steamapps\common\PalServer\Pal\Saved\SaveGames"
BACKUP_DIR = r"C:\Users\MMCDPapa\Desktop\Palworld\Saves"

RCON_PORT = 25575
RCON_PASSWORD = "1503"
RCON_IP = "localhost"

# Function to execute a shell command and capture output
def run_command(command):
    try:
        # Execute the command with real-time logging of its output
        process = subprocess.Popen(
            command,
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,  # Capture both stdout and stderr
            text=True,
            bufsize=1,
            universal_newlines=True
        )

        output_lines = []
        for line in process.stdout:
            log_message(f"STEAMCMD: {line.strip()}")
            output_lines.append(line)

        process.wait()

        if process.returncode != 0:
            error_msg = f"Command failed with exit code {process.returncode}. Output: {''.join(output_lines)}"
            log_message(error_msg)
            return error_msg

        return ''.join(output_lines)
    except Exception as e:
        log_message(f"Exception while running command: {command}\n{e}")
        return str(e)

# Function to send a command via RCON and log the response
def send_rcon_command(command):
    try:
        with MCRcon(RCON_IP, RCON_PASSWORD, RCON_PORT) as mcr:
            response = mcr.command(command)
            log_message(f"RCON Response: {response}")
            return response
    except Exception as e:
        log_message(f"RCON failed: {e}")

# Function to create a backup of the save games directory
def create_backup():
    timestamp = datetime.datetime.now().strftime("%Y-%m-%d_%H%M%S")
    source_dir = SAVE_GAMES_DIR
    dest_dir = os.path.join(BACKUP_DIR, f"backup_{timestamp}")

    try:
        log_message(f"Creating backup: {source_dir} -> {dest_dir}")

        # Ensure the destination directory exists
        if not os.path.exists(dest_dir):
            os.makedirs(dest_dir)

        # Execute xcopy with proper parameter formatting and detailed logging
        command = [
            "xcopy",
            source_dir,
            dest_dir,
            "/E",  # Copy all subdirectories, including empty ones
            "/I",  # If destination is a directory, copy all files into it
            "/H",  # Copy hidden and system files also
            "/Y"   # Suppress prompting to confirm overwriting an existing file
        ]

        log_message(f"Executing command: {command}")

        result = subprocess.run(command, text=True, capture_output=True)

        if result.returncode != 0:
            error_msg = f"xcopy failed with exit code {result.returncode}. Stdout: {result.stdout}, Stderr: {result.stderr}"
            log_message(error_msg)
            # Try copying individual files as a fallback
            try:
                for root, _, files in os.walk(source_dir):
                    for file in files:
                        src_path = os.path.join(root, file)
                        rel_path = os.path.relpath(root, source_dir)
                        dest_path = os.path.join(dest_dir, rel_path, file)
                        os.makedirs(os.path.dirname(dest_path), exist_ok=True)
                        shutil.copy2(src_path, dest_path)
                log_message("Fallback backup completed successfully.")
            except Exception as e:
                error_msg = f"Fallback backup failed: {e}"
                log_message(error_msg)
        else:
            log_message(f"Backup created successfully. xcopy output: {result.stdout}")
    except Exception as e:
        error_msg = f"Failed to create backup: {e}"
        log_message(error_msg)

# Server status indicator function
def update_server_status(status):
    if status == "Running":
        color = "green"
    elif status == "Updating":
        color = "yellow"
    else:
        color = "red"
    server_label.config(text=f"Server Status: {status}", foreground=color)

# Function to start the PalServer
def check_server_and_restart():
    """Check if the server process is running, and restart it if it crashed."""
    while getattr(start_server, "monitor_running", True):  # Check flag to control monitoring
        if not hasattr(start_server, "server_process") or start_server.server_process.poll() is not None:
            log_message("Server has crashed. Restarting...")
            time.sleep(5)  # Wait a moment before restarting
            try:
                global server_process
                server_process = subprocess.Popen([SERVER_EXE_PATH])
                start_server.server_process = server_process  # Store process for later checks
                update_server_status("Starting")
                log_message("Server restarted successfully.")
                time.sleep(15)  # Wait for server to start (adjust if needed)
                send_rcon_command("Info")
                get_player_count()  # Update player count
                update_server_status("Running")
            except Exception as e:
                log_message(f"Failed to restart server: {e}")
                update_server_status("Failed to Start")

        time.sleep(10)  # Check status periodically

def start_server():
    global server_process

    log_message("Starting server...")
    update_server_status("Starting")

    # Check if server is already running
    if hasattr(start_server, "server_process") and start_server.server_process.poll() is None:
        log_message("Server is already running")
        return

    try:
        server_process = subprocess.Popen([SERVER_EXE_PATH])
        start_server.server_process = server_process  # Store process for later checks
        update_server_status("Starting")

        # Enable monitoring flag and start the monitor thread
        start_server.monitor_running = True
        threading.Thread(target=check_server_and_restart, daemon=True).start()

        time.sleep(15)  # Wait for server to start (adjust if needed)
        send_rcon_command("Info")
        get_player_count()  # Update player count
        update_server_status("Running")
    except Exception as e:
        log_message(f"Failed to start server: {e}")
        update_server_status("Failed to Start")
# Function to stop the PalServer gracefully with RCON commands
def stop_server():
    log_message("Stopping server...")
    update_server_status("Stopping")

    # Stop monitoring before stopping the server
    if hasattr(start_server, "monitor_running"):
        start_server.monitor_running = False

    send_rcon_command("Save")
    time.sleep(3)
    send_rcon_command("Shutdown 11")
    time.sleep(1)
    send_rcon_command("Broadcast Der Server wird in 10 Sekunden Heruntergefahren")
    time.sleep(5)
    send_rcon_command("Broadcast Der Server wird in 5 Sekunden Heruntergefahren")
    time.sleep(4)
    send_rcon_command("Broadcast Der Server wird jetzt Heruntergefahren")

    # Remove server process attribute
    if hasattr(start_server, "server_process"):
        del start_server.server_process

    time.sleep(15)  # Adjust if needed
    update_server_status("Stopped")
# Function to update the PalServer using Steamcmd
def update_server():
    log_message("Updating server...")
    # Set status to updating
    update_server_status("Updating")

    # Stop the server first and remove monitoring attribute
    stop_server()

    # Ensure monitoring is stopped
    if hasattr(start_server, "monitor_running"):
        start_server.monitor_running = False

    update_server_status("Updating")
    # Create backup before updating
    create_backup()

    try:
        # Launch Steamcmd and monitor its output
        process = subprocess.Popen(
            [STEAMCMD_PATH, "+login anonymous", SERVER_EXE_PATH, "+app_update 2394010 validate", "+quit"],
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            text=True,
            bufsize=1
        )

        log_message("Update initiated. Monitoring Steamcmd process...")

        for line in process.stdout:
            print(f"STEAMCMD: {line.strip()}")  # Print to console for debugging
            log_message(f"STEAMCMD: {line.strip()}")

            # Check if update is complete
            if "Success! App '2394010' fully installed" in line:
                log_message("Update completed. Starting server...")
                start_server()
                break

        process.wait()

        if process.returncode != 0:
            error_msg = f"Steamcmd failed with exit code {process.returncode}"
            log_message(error_msg)
    except Exception as e:
        log_message(f"Failed to initiate update: {e}")

    # Restart server in case we missed the success message
    if not root.winfo_exists():  # Check if GUI is still running
        start_server()
# Function to schedule automatic restarts
def schedule_restart(hour, minute):
    now = datetime.datetime.now()
    scheduled_time = datetime.time(hour=hour, minute=minute)
    next_run = datetime.datetime.combine(now.date(), scheduled_time)

    if next_run < now:
        next_run += datetime.timedelta(days=1)

    delay_seconds = (next_run - now).total_seconds()

    log_message(f"Scheduled restart for {scheduled_time}. Next run in {delay_seconds} seconds.")

    threading.Timer(delay_seconds, lambda: update_server()).start()
    
# Function to monitor Steamcmd process for specific keywords
def monitor_steamcmd_process():
    try:
        # Check if there's an active Steamcmd process by looking at running processes
        log_message("Monitoring Steamcmd process...")

        # We'll assume we have a way to read the current output of Steamcmd (this would typically be done via subprocess.PIPE)
        # For simplicity, let's simulate checking for specific keywords in the Steamcmd output

        # Check if Steamcmd is running and verifying install
        verifying_install = False
        update_finished = False

        # Simulate reading lines from the Steamcmd process (in a real scenario, you'd read from process.stdout)
        steamcmd_output_lines = [
            "STEAMCMD: Update state (0x5) verifying install, progress:",
            "STEAMCMD: Success! App '2394010' fully installed."
        ]

        for line in steamcmd_output_lines:
            log_message(line)
            if "verifying install" in line:
                verifying_install = True
                log_message("Detected Steamcmd is verifying install. Preparing to stop server...")
            elif "Success! App '2394010' fully installed" in line:
                update_finished = True
                log_message("Update finished successfully. Starting server...")

        # If we detected that the update is still verifying, stop the server
        if verifying_install and not update_finished:
            log_message("Stopping server for update...")
            send_rcon_command("Save")
            time.sleep(2)
            stop_server()
            update_server_status("Updating")
        elif update_finished:
            # Start the server again after successful update
            start_server()
            update_server_status("Running")
    except Exception as e:
        log_message(f"Error monitoring Steamcmd process: {e}")

# Function to schedule automatic checks of Steamcmd updates every 2 hours
def schedule_steamcmd_check():
    now = datetime.datetime.now()
    next_run = now + datetime.timedelta(hours=2)

    # Calculate delay in seconds until next run
    delay_seconds = (next_run - now).total_seconds()

    log_message(f"Scheduled Steamcmd check every 2 hours. Next run in {delay_seconds} seconds.")

    threading.Timer(delay_seconds, schedule_steamcmd_check).start()
    monitor_steamcmd_process()

# Function to log messages
def log_message(message):
    log_text.insert(tk.END, f"{datetime.datetime.now().strftime('%H:%M:%S')} - {message}\n")
    log_text.yview(tk.END)

# Create main window with improved styling
root = tk.Tk()
root.title("PalServer GUI")
root.geometry("800x900")  # Set default size

style = ttk.Style(root)
style.theme_use("clam")

# Frame for server controls
control_frame = ttk.LabelFrame(root, text="Server Controls", padding=(10, 5))
control_frame.pack(fill=tk.X, padx=20, pady=10)

# Server control buttons with improved styling
start_button = ttk.Button(control_frame, text="Start Server", command=start_server)
start_button.grid(row=0, column=0, padx=5, pady=5, sticky="ew")

stop_button = ttk.Button(control_frame, text="Stop Server", command=stop_server)
stop_button.grid(row=0, column=1, padx=5, pady=5, sticky="ew")

update_button = ttk.Button(control_frame, text="Update Server", command=update_server)
update_button.grid(row=0, column=2, padx=5, pady=5, sticky="ew")

backup_button = ttk.Button(control_frame, text="Create Backup", command=create_backup)
backup_button.grid(row=0, column=3, padx=5, pady=5, sticky="ew")

# Server status label
server_label = ttk.Label(root, text="Server Status: Stopped")
server_label.pack(pady=(10, 20))

# Frame for automatic restart settings
restart_frame = ttk.LabelFrame(root, text="Automatic Restart", padding=(10, 5))
restart_frame.pack(fill=tk.X, padx=20, pady=10)

automatic_restart_label = ttk.Label(restart_frame, text="Schedule (HH:MM):")
automatic_restart_label.grid(row=0, column=0, padx=5, pady=5, sticky="w")

automatic_restart_entry = ttk.Entry(restart_frame)
automatic_restart_entry.insert(0, "05:00")  # Default value
automatic_restart_entry.grid(row=0, column=1, padx=5, pady=5, sticky="ew")

schedule_button = ttk.Button(restart_frame, text="Schedule Restart",
                            command=lambda: schedule_restart(
                                int(automatic_restart_entry.get().split(":")[0]),
                                int(automatic_restart_entry.get().split(":")[1])
                            ))
schedule_button.grid(row=0, column=2, padx=5, pady=5, sticky="ew")

# Player count section
player_frame = ttk.LabelFrame(root, text="Player Information", padding=(10, 5))
player_frame.pack(fill=tk.X, padx=20, pady=10)

def get_player_count():
    if not hasattr(get_player_count, "log_text_initialized") or not get_player_count.log_text_initialized:
        print("GUI is not fully initialized. Player count will be updated when the GUI is ready.")
        return 0

    try:
        response = send_rcon_command("ShowPlayers")
        # Check if there are players on the server before counting
        if "name,playeruid,steamid" in response and any(line.count(',') == 2 for line in response.split('\n')):
            lines = response.strip().split('\n')
            player_count = sum(1 for line in lines[1:] if ',' in line and line.count(',') == 2)  # Skip header line
            return player_count
        else:
            # Log if there are no players on the server
            print("No players currently on the server.")
            log_message("No players currently on the server.")
            return 0
    except Exception as e:
        print(f"Error getting player count: {e}")
        log_message(f"Error getting player count: {e}")
        return 0

player_label = ttk.Label(player_frame, text="Players Online:")
player_label.grid(row=0, column=0, padx=5, pady=5, sticky="w")

def update_player_count():
    while True:
        time.sleep(60)  # Update every minute
        player_count_value.config(text=f"{get_player_count()} players")

# Start thread for updating player count
player_thread = threading.Thread(target=update_player_count, daemon=True)
player_thread.start()

player_count_value = ttk.Label(player_frame, text=f"{get_player_count()} players")
player_count_value.grid(row=0, column=1, padx=5, pady=5, sticky="w")

# Broadcast message section
broadcast_frame = ttk.LabelFrame(root, text="Broadcast Message", padding=(10, 5))
broadcast_frame.pack(fill=tk.X, padx=20, pady=10)

broadcast_label = ttk.Label(broadcast_frame, text="Message:")
broadcast_label.grid(row=0, column=0, padx=5, pady=5, sticky="w")

broadcast_entry = ttk.Entry(broadcast_frame, width=40)
broadcast_entry.grid(row=0, column=1, padx=5, pady=5, sticky="ew")

def send_broadcast():
    message = broadcast_entry.get()
    if message:
        send_rcon_command(f'broadcast "{message}"')
        broadcast_entry.delete(0, tk.END)  # Clear the entry field

send_broadcast_button = ttk.Button(broadcast_frame, text="Send", command=send_broadcast)
send_broadcast_button.grid(row=0, column=2, padx=5, pady=5)

# Custom RCON command section
command_frame = ttk.LabelFrame(root, text="Custom Command", padding=(10, 5))
command_frame.pack(fill=tk.X, padx=20, pady=10)

custom_command_label = ttk.Label(command_frame, text="Command:")
custom_command_label.grid(row=0, column=0, padx=5, pady=5, sticky="w")

custom_command_entry = ttk.Entry(command_frame, width=40)
custom_command_entry.grid(row=0, column=1, padx=5, pady=5, sticky="ew")

def execute_custom_command():
    command = custom_command_entry.get()
    if command:
        send_rcon_command(command)
        custom_command_entry.delete(0, tk.END)  # Clear the entry field

execute_button = ttk.Button(command_frame, text="Execute", command=execute_custom_command)
execute_button.grid(row=0, column=2, padx=5, pady=5)

# Create a notebook (tabbed interface) for the logs
notebook = ttk.Notebook(root)
notebook.pack(fill=tk.BOTH, expand=True, padx=20, pady=10)

# Tab for general logs
general_log_tab = ttk.Frame(notebook)
notebook.add(general_log_tab, text="General Logs")

log_frame = ttk.LabelFrame(general_log_tab, padding=(10, 5))
log_frame.pack(fill=tk.BOTH, expand=True)

log_text = tk.Text(log_frame, wrap=tk.WORD)
log_text.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)

log_scrollbar = ttk.Scrollbar(log_frame, orient=tk.VERTICAL, command=log_text.yview)
log_scrollbar.pack(side=tk.RIGHT, fill=tk.Y)

log_text['yscrollcommand'] = log_scrollbar.set

# Mark the log_text as initialized
get_player_count.log_text_initialized = True

# Tab for RCON logs
rcon_log_tab = ttk.Frame(notebook)
notebook.add(rcon_log_tab, text="RCON Logs")

rcon_frame = ttk.LabelFrame(rcon_log_tab, padding=(10, 5))
rcon_frame.pack(fill=tk.BOTH, expand=True)

rcon_text = tk.Text(rcon_frame, wrap=tk.WORD)
rcon_text.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)

rcon_scrollbar = ttk.Scrollbar(rcon_frame, orient=tk.VERTICAL, command=rcon_text.yview)
rcon_scrollbar.pack(side=tk.RIGHT, fill=tk.Y)

rcon_text['yscrollcommand'] = rcon_scrollbar.set

def log_rcon_message(message):
    rcon_text.insert(tk.END, f"{datetime.datetime.now().strftime('%H:%M:%S')} - {message}\n")
    rcon_text.yview(tk.END)

# Tab for online players
players_log_tab = ttk.Frame(notebook)
notebook.add(players_log_tab, text="Online Players")

players_frame = ttk.LabelFrame(players_log_tab, padding=(10, 5))
players_frame.pack(fill=tk.BOTH, expand=True)

players_text = tk.Text(players_frame, wrap=tk.WORD)
players_text.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)

players_scrollbar = ttk.Scrollbar(players_frame, orient=tk.VERTICAL, command=players_text.yview)
players_scrollbar.pack(side=tk.RIGHT, fill=tk.Y)

players_text['yscrollcommand'] = players_scrollbar.set

def log_player(message):
    players_text.insert(tk.END, f"{datetime.datetime.now().strftime('%H:%M:%S')} - {message}\n")
    players_text.yview(tk.END)

# Modify send_rcon_command to also log responses in the RCON log
def send_rcon_command(command):
    try:
        with MCRcon(RCON_IP, RCON_PASSWORD, RCON_PORT) as mcr:
            response = mcr.command(command)
            log_message(f"RCON Response: {response}")
            log_rcon_message(f"Command Sent: {command}")
            log_rcon_message(f"Response Received: {response}")

            # Parse and display online players if the command is ShowPlayers
            if command == "ShowPlayers":
                parse_player_list(response)

            return response
    except Exception as e:
        log_message(f"RCON failed: {e}")
        log_rcon_message(f"Error: {e}")

def parse_player_list(response):
    """Parse the player list response and display in the players log."""
    # Clear previous content
    players_text.delete(1.0, tk.END)

    if "name,playeruid,steamid" not in response:
        log_message("Player list response format unexpected")
        return

    lines = response.split('\n')
    header_line = None

    for line in lines:
        if "name,playeruid,steamid" in line:
            header_line = line
            continue

        # Skip any empty lines or header lines
        if not line.strip() or line == header_line:
            continue

        log_player(line)

    # Update new players after parsing the response
    update_new_players(response)

# Function to check for and welcome new players based on player list responses
def update_new_players(response):
    try:
        # Extract player names from the response
        if "name,playeruid,steamid" in response:
            lines = response.strip().split('\n')
            current_player_lines = set()

            for line in lines:
                if "," in line and len(line.split(',')) == 3:
                    name = line.split(',')[0].strip()
                    if name:  # Make sure we have a valid player name
                        current_player_lines.add(name)

            # If this is our first time seeing players, just save the list for later comparison
            if not hasattr(update_new_players, "previous_player_lines"):
                log_message("Setting initial player list")
                update_new_players.previous_player_lines = current_player_lines
                return

            new_players = current_player_lines - update_new_players.previous_player_lines

            # Update our previous players set
            update_new_players.previous_player_lines = current_player_lines

            if new_players:
                log_message(f"New players detected: {new_players}")
                for player_name in new_players:
                    welcome_message = f'broadcast "Willkommen {player_name} auf dem Palserver von Kommand-Pimperle!"'
                    send_rcon_command(welcome_message)
                    log_message(f"Sent welcome message to: {player_name}")

    except Exception as e:
        log_message(f"Error updating new players list: {e}")

# No longer using the dedicated monitor thread for new players since we're handling it in parse_player_list
#

# Function to schedule automatic checks of Steamcmd updates every 2 hours
schedule_steamcmd_check()

root.mainloop()
