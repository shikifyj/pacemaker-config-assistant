import utils
import time
import re


def modify_cluster_name(cluster_name):
    cmd = f"crm config property cluster-name={cluster_name}"
    utils.exec_cmd(cmd)


def modify_policy(status='stop'):
    cmd = f"crm config property no-quorum-policy={status}"
    utils.exec_cmd(cmd)


def modify_stonith_enabled():
    cmd = "crm config property stonith-enabled=false"
    utils.exec_cmd(cmd)


def modify_stickiness():
    cmd = "crm config rsc_defaults resource-stickiness=1000"
    utils.exec_cmd(cmd)


def restart():
    cmd = "systemctl restart pacemaker"
    utils.exec_cmd(cmd)


def check_crm_conf():
    cmd = 'crm config show | cat'
    data = utils.exec_cmd(cmd)
    data_property = re.search('property cib-bootstrap-options:\s([\s\S]*)', data).group(1)
    # re_cluster_name = re.findall('cluster-name=(\S*)', data_property)
    re_stonith_enabled = re.findall('stonith-enabled=(\S*)', data_property)
    re_policy = re.findall('no-quorum-policy=(\S*)', data_property)
    re_resource_stickiness = re.findall('resource-stickiness=(\d*)', data)

    # 不进行cluster_name 的判断
    # if not re_cluster_name or re_cluster_name[0] != cluster_name:
    #     return

    if not re_stonith_enabled or re_stonith_enabled[0] != 'false':
        return

    if not re_policy or re_policy[0] not in ['ignore', 'stop']:
        return

    if not re_resource_stickiness or re_resource_stickiness[0] != '1000':
        return

    return True


def install():
    cmd = 'apt install -y pacemaker crmsh corosync ntpdate'
    utils.exec_cmd(cmd)


def get_version():
    cmd = 'crm st | grep Current | cat'
    result = utils.exec_cmd(cmd)
    version = re.findall('\(version\s(.*)\)\s', result)
    if version:
        return version[0]


def config_drbd_attr():
    cmd1 = 'crm config primitive drbd-attr ocf:linbit:drbd-attr'
    cmd2 = 'crm config clone drbd-attr-clone drbd-attr'
    utils.exec_cmd(cmd1)
    utils.exec_cmd(cmd2)


def clear_crm_res():
    utils.exec_cmd("crm res stop g_linstor p_fs_linstordb p_linstor-controller")
    utils.exec_cmd("crm res stop ms_drbd_linstordb p_drbd_linstordb")
    utils.exec_cmd("crm res stop drbd-attr")
    utils.exec_cmd("crm res stop vipcontroller")
    time.sleep(2)
    utils.exec_cmd("crm conf del g_linstor p_fs_linstordb p_linstor-controller")
    utils.exec_cmd("crm conf del g_linstor ms_drbd_linstordb p_drbd_linstordb")
    utils.exec_cmd("crm conf del drbd-attr")
    utils.exec_cmd("crm conf del vipcontroller")


def clear_crm_node(node):
    utils.exec_cmd(f"crm conf del {node}")


def uninstall():
    cmd = 'apt purge -y pacemaker crmsh corosync ntpdate'
    utils.exec_cmd(cmd)


def set_vip(ip):
    cmd = f"crm cof primitive vipcontroller IPaddr2 params ip={ip} cidr_netmask=24 op monitor timeout=20 interval=10"
    utils.exec_cmd(cmd)


def colocation_vip_controller():
    cmd = "crm cof colocation c_vip_with_linstor inf: vipcontroller g_linstor"
    utils.exec_cmd(cmd)
