from netmiko import Netmiko
from netmiko.ssh_autodetect import SSHDetect
from netmiko.ssh_dispatcher import ConnectHandler
from prettytable import PrettyTable
from getpass import getpass
import PySimpleGUI as sg

def check_os(IP,username, password):

    remote_device = {'device_type': 'autodetect',
                         'host': IP,
                         'username': username,
                         'password': password}

    guesser = SSHDetect(**remote_device)
    best_match = guesser.autodetect()
    if best_match is None:
        print('Could not detect OS, please check IP or Device')
        raise ValueError(f"Unable to detect OS for device {IP}")

    #print(f'IP:{IP} OS is {best_match}')
    return best_match

sg.ChangeLookAndFeel('GreenTan')

layout = [
        [sg.Text('username:', size =(15,1)), sg.InputText()],
        [sg.Text('password:', size =(15,1)), sg.InputText('', key='Password', password_char='*')],
        [sg.Text('l2 switch IP:', size =(15,1)), sg.InputText()],
        [sg.Text('l3 switch IP:', size =(15,1)), sg.InputText()],
        [sg.Text('uplink:', size =(15,1)), sg.InputText()],
        [sg.Submit(), sg.Cancel()]
    ]

Form = sg.Window('Mac2IP', layout)
button, values = Form.read()
Form.close()

#Variables
username = values[0]
password = values['Password']

l2ip=values[1]
devicetypel2=check_os(l2ip,username, password)

l3ip=values[2]
devicetypel3=check_os(l3ip,username, password)

ids=[]
uplink=values[3]

#Commands
catosmac='show mac address-table dynamic'
catosarp='show ip arp'
nxosmac=''
nxsarp='show ip arp'
aristamac=''
aristaarp=''
junosmac = ''
junosarp = ''

net_connect = Netmiko(host=l2ip, username=username, password=password, device_type=devicetypel2)

if devicetypel2 == 'cisco_ios':
    mac_table = net_connect.send_command(catosmac, use_textfsm=True)

for idx,entry in enumerate(mac_table):
    if entry['destination_port'][0].startswith(uplink.capitalize()):
        ids.append(idx)

for id in reversed(ids):
    mac_table.pop(id)

mac_data = {'mac': [entry['destination_address'] for entry in mac_table],
            'interface': [entry['destination_port'] for entry in mac_table],
            }

net_connect = Netmiko(host=l3ip, username=username, password=password, device_type=devicetypel3)

if devicetypel3 == 'cisco_nxos' or devicetypel3 == 'cisco_ios':
    arp_table = net_connect.send_command(nxsarp, use_textfsm=True)

arp_data = { 'IP': [entry['address'] for entry in arp_table],
            'mac': [entry['mac'] for entry in arp_table],
    }

table = PrettyTable()
table.field_names = ["MAC", "IP", "Interface"]

for l2entry in mac_data['mac']:
    i=0
    for l3entry in arp_data['mac']:
        if l2entry==l3entry:
            row = [l2entry,arp_data['IP'][i],mac_data['interface'][mac_data['mac'].index(l2entry)]]
            table.add_row(row)
        i+=1

t2 = sg.Input(visible=False, enable_events=True, key='-T2-',
 font=('Arial Bold', 10), expand_x=True)

t3 = sg.Multiline(table, enable_events=True, key='-INPUT-',
 expand_x=True, expand_y=True,
 justification='left')

layout = [[t3], [t2, sg.FileSaveAs()]]
window = sg.Window('FileSaveAs', layout, size=(900, 200))

while True:
 event, values = window.read()

 if event == '-T2-':
    file = open(t2.get(), "w")
    file.write(t3.get())
    file.close()

 if event == sg.WIN_CLOSED or event == 'Exit':
    break

window.close()
