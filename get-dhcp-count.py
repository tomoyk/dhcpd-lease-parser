#!/usr/bin/env python3.6

def parse_file(file_name: str):
    import re
    with open(file_name, "r") as file:
        file_content = file.read()

    file_content = re.sub(r"#.*\n(\n)?|server-duid.+;\n", r'', file_content) 
    lease_logs = [fc for fc in re.split(r"\n}\n*", file_content)]

    logs = []
    for lease_log in lease_logs:
        log_entries = re.split(";\n| {\n", lease_log)
        log_entries = [re.sub(r"^(\n)?\s+|;$", r'', log_entry) for log_entry in log_entries ]

        tmp = {}
        for log_entry in log_entries:
            if not(log_entry):
                continue

            key = log_entry.split(" ")[0]
            val = ' '.join(log_entry.split(" ")[1:])
            tmp[key] = val
            logs.append(tmp)

    return logs


def pickup_fresh_leases(lines: list):
    from datetime import datetime,timezone
    def _is_active(line: str):
        if line is None:
            return False
        try:
            log_date = datetime.strptime(line['ends'], '%w %Y/%m/%d %H:%M:%S')
        except Exception as e:
            print(e)
            return False

        # 'ends' <= now()      
        if log_date < datetime.now(timezone.utc).replace(tzinfo=None):
            return False
        else:
            return True

    active_list = [l for l in lines if _is_active(l)]

    # Get unique list
    printed_ips = set()
    for alog in reversed(active_list):
        if alog.get('lease') in printed_ips:
            # print('del', alog)
            active_list.remove(alog)
            continue
        else:
            printed_ips.add(alog.get('lease'))

    return active_list


def count_up_subnet(lines: list, subnet_list: list):
    import ipaddress as ipa
    # key: ipa.IPv4Network, value: network_address (str)
    net_dict = {ipa.IPv4Network(subnet):ipa.IPv4Network(subnet).network_address for subnet in subnet_list}
    # key: ipa.IPv4Network, value: count (int)
    count_dict = {obj:0 for obj in net_dict.keys()}

    for line in lines:
        myip = ipa.ip_address(line['lease'])
        for ipaobj,netaddr in net_dict.items():
            if myip in ipaobj.hosts():
                count_dict[ipaobj] += 1
     
    return count_dict


def main(table=True):
    parsed_log = parse_file("/var/lib/dhcpd/dhcpd.leases")
    pickuped_log = pickup_fresh_leases(parsed_log)

    subnets = [
        '10.1.1.0/255.255.255.0',
    ]
    result = count_up_subnet(pickuped_log, subnets)
    hostname = 'dhcp'

    for k,v in result.items():
        print(hostname, 'lease-ip.'+str(k.network_address)+'_'+str(k.prefixlen) ,v)

    if not(table):
        from tabulate import tabulate
        ENABLE_LABELS = ["lease", "starts", "ends", "hardware", "client-hostname"]
        log_list = [[v for k,v in list(pl.items()) if k in ENABLE_LABELS] for pl in pickuped_log]
        log_list.sort(key=lambda x: x[0])
        print(tabulate(log_list, headers=ENABLE_LABELS))


if __name__ == '__main__':
    from os import sys
    if len(sys.argv) <= 0:
        main(True)
    else:
        main(False)
