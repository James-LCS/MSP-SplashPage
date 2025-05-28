from flask import Flask, render_template, request, redirect, url_for
import sqlite3
import json
from datetime import datetime
from dateutil.relativedelta import relativedelta
import subprocess

app = Flask(__name__)

# Initialize SQLite database
DB_PATH = "clients.db"

def init_db():
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS clients (
            id TEXT PRIMARY KEY,
            name TEXT NOT NULL,
            meetings TEXT NOT NULL,
            services TEXT NOT NULL
        )
    ''')
    # Check if the database is empty and populate with default data if needed
    cursor.execute("SELECT COUNT(*) FROM clients")
    if cursor.fetchone()[0] == 0:
        default_clients = [
            {
                "id": str(i + 1),
                "name": name,
                "meetings": json.dumps([
                    {
                        "type": "TAM",
                        "frequency": "Quarterly",
                        "lastMeetingDate": "2025-01-01",
                        "nextMeetingDueDate": "2025-04-01",
                        "status": "Pending",
                        "history": [{"date": "2025-01-01"}]
                    },
                    {
                        "type": "vCIO",
                        "frequency": "Quarterly",
                        "lastMeetingDate": "2025-01-01",
                        "nextMeetingDueDate": "2025-04-01",
                        "status": "Pending",
                        "history": [{"date": "2025-01-01"}]
                    }
                ]),
                "services": json.dumps(["Managed IT", "DataCenter", "Datto SaaS", "Datto File Protect", "3CX", "Datto DFP", "Veeam Backups", "M365", "Google", "InfoSec LCS", "InfoSec Axiom"])
            }
            for i, name in enumerate([
                "Airport Chevrolet", "American Industrial Door", "Ascentron",
                "Behymer Sorenson & Price", "Bills Glass", "Bob Drake Reproductions",
                "Botts Kau Schulz", "Cascade Eyecare Center", "CBarC",
                "CC Constructors", "Cowhorn Vineyard", "Crater Chiropractic",
                "David M. Trask MD", "Gates Home Furnishings", "Hays Oil Company",
                "Hy-Speed Machining", "Jacqueline Amato MD", "James Hamilton Construction",
                "Lewellyn Wealth", "Lifeline Computer Solutions", "McCully House Inn",
                "McLane Plumbing", "Mountain View Estates", "Neathamer Surveying",
                "NIC Industries", "Norman Peterson & Associates", "Noveske Rifleworks",
                "Oregon Ear Nose and Throat", "Overhead Door Company of Klamath Falls",
                "Retirement Planning Specialists", "Rothfus Family Dental",
                "Southern Oregon Subaru", "Sunday Afternoons", "Superior Athletic Club",
                "TC Chevy", "Walsh Tax Services"
            ])
        ]
        for client in default_clients:
            cursor.execute("INSERT INTO clients (id, name, meetings, services) VALUES (?, ?, ?, ?)",
                           (client["id"], client["name"], client["meetings"], client["services"]))
    conn.commit()
    conn.close()

def load_data():
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM clients")
    rows = cursor.fetchall()
    clients = []
    for row in rows:
        client = {
            "id": row[0],
            "name": row[1],
            "meetings": json.loads(row[2]),
            "services": json.loads(row[3])
        }
        clients.append(client)
    conn.close()
    return clients

def save_data(clients):
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    cursor.execute("DELETE FROM clients")
    for client in clients:
        cursor.execute("INSERT INTO clients (id, name, meetings, services) VALUES (?, ?, ?, ?)",
                       (client["id"], client["name"], json.dumps(client["meetings"]), json.dumps(client["services"])))
    conn.commit()
    conn.close()

def calculate_next_due_date(last_date, frequency):
    last_date_obj = datetime.strptime(last_date, "%Y-%m-%d").date()
    if frequency == "Monthly":
        return (last_date_obj + relativedelta(months=1)).strftime("%Y-%m-%d")
    elif frequency == "Quarterly":
        return (last_date_obj + relativedelta(months=3)).strftime("%Y-%m-%d")
    elif frequency == "Semi-Annually":
        return (last_date_obj + relativedelta(months=6)).strftime("%Y-%m-%d")
    else:
        raise ValueError("Unknown frequency")

@app.route('/')
def index():
    clients = load_data()
    selected_client = None
    today = datetime.today().date()

    # Calculate status for each client's meetings
    for client in clients:
        for meeting in client["meetings"]:
            next_due_date = datetime.strptime(meeting["nextMeetingDueDate"], "%Y-%m-%d").date()
            if next_due_date < today:
                meeting["status_text"] = "Overdue"
                meeting["status_class"] = "overdue"
            elif (next_due_date - today).days <= 30:
                meeting["status_text"] = "Due Soon"
                meeting["status_class"] = "due-soon"
            else:
                meeting["status_text"] = "Upcoming"
                meeting["status_class"] = "upcoming"

    if 'client_id' in request.args:
        client_id = request.args['client_id']
        selected_client = next((client for client in clients if client['id'] == client_id), None)

    # Calculate overdue and upcoming counts
    today_str = today.strftime("%Y-%m-%d")
    overdue_count = sum(1 for client in clients for meeting in client["meetings"] if 
                        meeting["nextMeetingDueDate"] <= today_str or 
                        (datetime.strptime(meeting["nextMeetingDueDate"], "%Y-%m-%d").date() - today).days <= 30)
    overdue_clients = [client for client in clients if any(meeting["nextMeetingDueDate"] < today_str for meeting in client["meetings"])]

    return render_template('index.html', clients=clients, selected_client=selected_client, 
                           overdue_count=overdue_count, overdue_clients=overdue_clients, today=today_str)

@app.route('/add_client', methods=['GET', 'POST'])
def add_client():
    if request.method == 'POST':
        name = request.form['name']
        if not name:
            return "Error: Client name is required", 400
        clients = load_data()
        if name in [client["name"] for client in clients]:
            return "Error: Client name already exists", 400
        selected_services = [service for service in ["Managed IT", "DataCenter", "Datto SaaS", "Datto File Protect", "3CX", "Datto DFP", "Veeam Backups", "M365", "Google", "InfoSec LCS", "InfoSec Axiom"] if request.form.get(service)]
        tam_freq = request.form['tam_freq']
        tam_last = request.form['tam_last']
        vcio_freq = request.form['vcio_freq']
        vcio_last = request.form['vcio_last']
        new_client = {
            "id": str(len(clients) + 1),
            "name": name,
            "meetings": [
                {
                    "type": "TAM",
                    "frequency": tam_freq,
                    "lastMeetingDate": tam_last,
                    "nextMeetingDueDate": calculate_next_due_date(tam_last, tam_freq),
                    "status": "Pending",
                    "history": [{"date": tam_last}]
                },
                {
                    "type": "vCIO",
                    "frequency": vcio_freq,
                    "lastMeetingDate": vcio_last,
                    "nextMeetingDueDate": calculate_next_due_date(vcio_last, vcio_freq),
                    "status": "Pending",
                    "history": [{"date": vcio_last}]
                }
            ],
            "services": selected_services
        }
        clients.append(new_client)
        save_data(clients)
        return redirect(url_for('index', client_id=new_client['id']))
    return render_template('add_client.html')

@app.route('/edit_client/<client_id>', methods=['GET', 'POST'])
def edit_client(client_id):
    clients = load_data()
    client = next((client for client in clients if client['id'] == client_id), None)
    if not client:
        return "Client not found", 404
    if request.method == 'POST':
        new_name = request.form['name']
        if not new_name:
            return "Error: Client name is required", 400
        if new_name != client["name"] and new_name in [c["name"] for c in clients]:
            return "Error: Client name already exists", 400
        selected_services = [service for service in ["Managed IT", "DataCenter", "Datto SaaS", "Datto File Protect", "3CX", "Datto DFP", "Veeam Backups", "M365", "Google", "InfoSec LCS", "InfoSec Axiom"] if request.form.get(service)]
        tam_freq = request.form['tam_freq']
        tam_last = request.form['tam_last']
        vcio_freq = request.form['vcio_freq']
        vcio_last = request.form['vcio_last']
        client["name"] = new_name
        client["services"] = selected_services
        client["meetings"][0]["frequency"] = tam_freq
        client["meetings"][0]["lastMeetingDate"] = tam_last
        client["meetings"][0]["nextMeetingDueDate"] = calculate_next_due_date(tam_last, tam_freq)
        client["meetings"][1]["frequency"] = vcio_freq
        client["meetings"][1]["lastMeetingDate"] = vcio_last
        client["meetings"][1]["nextMeetingDueDate"] = calculate_next_due_date(vcio_last, vcio_freq)
        save_data(clients)
        return redirect(url_for('index', client_id=client_id))
    return render_template('edit_client.html', client=client)

@app.route('/mark_meeting_done/<client_id>/<meeting_type>', methods=['GET', 'POST'])
def mark_meeting_done(client_id, meeting_type):
    clients = load_data()
    client = next((client for client in clients if client['id'] == client_id), None)
    if not client:
        return "Client not found", 404
    meeting_index = 0 if meeting_type == "TAM" else 1
    meeting = client["meetings"][meeting_index]
    if request.method == 'POST':
        date = request.form['date']
        meeting["lastMeetingDate"] = date
        meeting["nextMeetingDueDate"] = calculate_next_due_date(date, meeting["frequency"])
        meeting["history"].append({"date": date})
        save_data(clients)
        return redirect(url_for('index', client_id=client_id))
    return render_template('mark_meeting_done.html', client=client, meeting_type=meeting_type)

@app.route('/scripts')
def scripts():
    return render_template('scripts.html', output=None)

@app.route('/run_script/<script>')
def run_script(script):
    try:
        if script == "admin_creation":
            # Run admin creation commands
            subprocess.run("net user Corporal Corporal /add", shell=True, check=True, capture_output=True, creationflags=subprocess.CREATE_NO_WINDOW)
            subprocess.run("net localgroup Administrators Corporal /add", shell=True, check=True, capture_output=True, creationflags=subprocess.CREATE_NO_WINDOW)
            output = "Admin Creation Successful\nNew admin account 'Corporal' created with password 'Corporal'."
        elif script == "flush_dns":
            # Flush DNS
            subprocess.run("ipconfig /flushdns", shell=True, check=True, capture_output=True, creationflags=subprocess.CREATE_NO_WINDOW)
            output = "Flush DNS Successful\nDNS cache has been flushed."
        elif script == "ip_config":
            # Get IP configuration
            result = subprocess.run("ipconfig /all", shell=True, check=True, capture_output=True, text=True, creationflags=subprocess.CREATE_NO_WINDOW)
            output_lines = result.stdout.splitlines()
            relevant_info = []
            for line in output_lines:
                line = line.strip()
                if "IPv4 Address" in line and "Preferred" in line:
                    relevant_info.append(f"IPv4 Address: {line.split(':')[-1].strip()}")
                elif "Subnet Mask" in line:
                    relevant_info.append(f"Subnet Mask: {line.split(':')[-1].strip()}")
                elif "Default Gateway" in line and line.split(':')[-1].strip():
                    relevant_info.append(f"Default Gateway: {line.split(':')[-1].strip()}")
                elif "DNS Servers" in line:
                    relevant_info.append(f"DNS Servers: {line.split(':')[-1].strip()}")
            output = "\n".join(relevant_info) if relevant_info else "No relevant IP configuration found."
        elif script == "clear_temp":
            # Clear temporary files
            subprocess.run("del /q /f /s %TEMP%\\*", shell=True, check=True, capture_output=True, creationflags=subprocess.CREATE_NO_WINDOW)
            output = "Temporary Files have been cleared."
        elif script == "disk_space":
            # Get disk space
            result = subprocess.run('wmic logicaldisk where "DeviceID=\'C:\'" get FreeSpace,Size', shell=True, check=True, capture_output=True, text=True, creationflags=subprocess.CREATE_NO_WINDOW)
            output_lines = result.stdout.splitlines()
            for line in output_lines:
                if line.strip() and not line.startswith("FreeSpace"):
                    free_space, total_size = map(int, line.split())
                    free_space_gb = free_space / (1024**3)  # Convert bytes to GB
                    total_size_gb = total_size / (1024**3)
                    output = f"Free Space on C: Drive: {free_space_gb:.2f} GB\nTotal Size: {total_size_gb:.2f} GB"
                    break
            else:
                output = "Unable to retrieve disk space information."
        elif script == "group_policy_update":
            # Update Group Policy
            subprocess.run("gpupdate /force", shell=True, check=True, capture_output=True, creationflags=subprocess.CREATE_NO_WINDOW)
            output = "Group Policy Update Successful\nGroup Policy has been updated."
        elif script == "restart_print_spooler":
            # Restart Print Spooler and clear print queue
            subprocess.run("net stop spooler", shell=True, check=True, capture_output=True, creationflags=subprocess.CREATE_NO_WINDOW)
            subprocess.run('del /q /f /s "%systemroot%\\System32\\spool\\PRINTERS\\*"', shell=True, check=True, capture_output=True, creationflags=subprocess.CREATE_NO_WINDOW)
            subprocess.run("net start spooler", shell=True, check=True, capture_output=True, creationflags=subprocess.CREATE_NO_WINDOW)
            output = "Print Spooler Restarted\nPrint queue has been cleared."
        elif script == "check_windows_updates":
            # Check Windows Updates
            subprocess.run("wuauclt /detectnow", shell=True, check=True, capture_output=True, creationflags=subprocess.CREATE_NO_WINDOW)
            output = "Windows Update Check Initiated\nChecking for Windows updates... Check the Windows Update settings for results."
        elif script == "disable_windows_firewall":
            # Disable Windows Firewall
            subprocess.run("netsh advfirewall set allprofiles state off", shell=True, check=True, capture_output=True, creationflags=subprocess.CREATE_NO_WINDOW)
            output = "Windows Firewall Disabled\nWindows Firewall has been disabled."
        elif script == "m365_install":
            # Run M365 Install batch file
            subprocess.run("M365Install.bat", shell=True, check=True, capture_output=True, creationflags=subprocess.CREATE_NO_WINDOW)
            output = "M365 Installation Successful"
        else:
            output = "Invalid script specified."
    except subprocess.CalledProcessError as e:
        output = f"Error executing script: {e.stderr.decode()}"
    except Exception as e:
        output = f"Unexpected error: {str(e)}"

    return render_template('scripts.html', output=output)

if __name__ == "__main__":
    init_db()
    app.run(host="0.0.0.0", port=5000, debug=True)