
from netmiko import Netmiko
from netmiko.ssh_autodetect import SSHDetect
from netmiko.ssh_dispatcher import ConnectHandler
from prettytable import PrettyTable
from getpass import getpass

#Functions
def check_os(IP,username, password):

    remote_device = {'device_type': 'autodetect',
                         'host': IP,
                         'username': username,
                         'password': password}

    guesser = SSHDetect(**remote_device)
    best_match = guesser.autodetect()
    print(f'Switch with IP:{IP} is {best_match}')
    return best_match

#Variables
l2ip=input('what is the l2 switch IP?')
l3ip=input('what is the l3 swtich IP?')
username = input('what is the username?')
password = getpass()
ids=[]
devicetypel2=check_os(l2ip,username,password)
devicetypel3=check_os(l3ip,username,password)

#Commands
catosmac='show mac address-table dynamic'
catosarp=''
nxsmac=''
nxsarp='show ip arp'
aristamac=''
aristaarp=''

net_connect = Netmiko(host=l2ip, username=username, password=password, device_type=devicetypel2)

if devicetypel2 == 'cisco_ios':
    mac_table = net_connect.send_command('show mac address-table dynamic', use_textfsm=True)

for idx,entry in enumerate(mac_table):
    if entry['destination_port'][0].startswith('Po'):
        ids.append(idx)

for id in reversed(ids):
    mac_table.pop(id)

mac_data = {'mac': [entry['destination_address'] for entry in mac_table],
            'interface': [entry['destination_port'] for entry in mac_table],
            }

net_connect = Netmiko(host=l3ip, username=username, password=password, device_type=devicetypel3)

if devicetypel3 == 'cisco_nxos':
    arp_table = net_connect.send_command('show ip arp', use_textfsm=True)

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
        i+=1
        
print(table)
