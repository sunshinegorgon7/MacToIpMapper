from netmiko import Netmiko
from netmiko.ssh_autodetect import SSHDetect
from prettytable import PrettyTable
import PySimpleGUI as sg


def check_os(ip, username, password):
    """Detect and return the Netmiko device_type for *ip*."""
    remote_device = {
        'device_type': 'autodetect',
        'host': ip,
        'username': username,
        'password': password,
    }
    guesser = SSHDetect(**remote_device)
    best_match = guesser.autodetect()
    if not best_match:
        raise ValueError(f'Could not detect OS for {ip}. Check IP or device.')
    return best_match


def normalize_mac(mac):
    """Normalize MAC to lowercase hex digits only for comparison."""
    return mac.replace(':', '').replace('.', '').replace('-', '').lower()


sg.theme('GreenTan')

layout = [
    [sg.Text('Username:',    size=(15, 1)), sg.InputText()],
    [sg.Text('Password:',    size=(15, 1)), sg.InputText('', key='Password', password_char='*')],
    [sg.Text('L2 Switch IP:', size=(15, 1)), sg.InputText()],
    [sg.Text('L3 Switch IP:', size=(15, 1)), sg.InputText()],
    [sg.Text('Uplink:',      size=(15, 1)), sg.InputText()],
    [sg.Submit(), sg.Cancel()],
]

form = sg.Window('Mac2IP', layout)
button, values = form.read()
form.close()

if button in (sg.WIN_CLOSED, 'Cancel'):
    raise SystemExit('Cancelled by user.')

username = values[0]
password = values['Password']
l2ip     = values[1]
l3ip     = values[2]
uplink   = values[3]

# --- Detect OS ---
try:
    devicetype_l2 = check_os(l2ip, username, password)
    devicetype_l3 = check_os(l3ip, username, password)
except ValueError as e:
    sg.popup_error(str(e))
    raise SystemExit(str(e))

# --- L2: Pull MAC table ---
try:
    conn_l2 = Netmiko(host=l2ip, username=username, password=password, device_type=devicetype_l2)
    if devicetype_l2 == 'cisco_ios':
        mac_table = conn_l2.send_command('show mac address-table dynamic', use_textfsm=True)
    else:
        sg.popup_error(f'L2 device type "{devicetype_l2}" not yet supported.')
        raise SystemExit(f'Unsupported L2 type: {devicetype_l2}')
finally:
    conn_l2.disconnect()

# Filter out uplink entries (destination_port is a list in TextFSM output)
mac_table = [
    entry for entry in mac_table
    if not entry['destination_port'][0].lower().startswith(uplink.lower())
]

mac_data = {
    'mac':       [normalize_mac(entry['destination_address']) for entry in mac_table],
    'raw_mac':   [entry['destination_address'] for entry in mac_table],
    'interface': [entry['destination_port'][0] for entry in mac_table],
}

# --- L3: Pull ARP table ---
try:
    conn_l3 = Netmiko(host=l3ip, username=username, password=password, device_type=devicetype_l3)
    if devicetype_l3 in ('cisco_ios', 'cisco_nxos'):
        arp_table = conn_l3.send_command('show ip arp', use_textfsm=True)
    else:
        sg.popup_error(f'L3 device type "{devicetype_l3}" not yet supported.')
        raise SystemExit(f'Unsupported L3 type: {devicetype_l3}')
finally:
    conn_l3.disconnect()

arp_data = {
    'ip':  [entry['address'] for entry in arp_table],
    'mac': [normalize_mac(entry['mac']) for entry in arp_table],
}

# --- Build table ---
table = PrettyTable()
table.field_names = ['MAC', 'IP', 'Interface']

for idx, norm_mac in enumerate(mac_data['mac']):
    if norm_mac in arp_data['mac']:
        arp_idx = arp_data['mac'].index(norm_mac)
        table.add_row([
            mac_data['raw_mac'][idx],
            arp_data['ip'][arp_idx],
            mac_data['interface'][idx],
        ])

# --- Display & Save ---
t2 = sg.Input(visible=False, enable_events=True, key='-T2-', font=('Arial Bold', 10), expand_x=True)
t3 = sg.Multiline(str(table), enable_events=True, key='-INPUT-',
                  expand_x=True, expand_y=True, justification='left')

layout2 = [[t3], [t2, sg.FileSaveAs()]]
window = sg.Window('Mac2IP — Results', layout2, size=(900, 400))

while True:
    event, values = window.read()
    if event == '-T2-' and t2.get():
        with open(t2.get(), 'w') as f:
            f.write(t3.get())
    if event in (sg.WIN_CLOSED, 'Exit'):
        break

window.close()
