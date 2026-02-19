import pulumi
import pulumi_yandex as yc
import os

yc_key_path = os.getenv("YC_KEY_JSON")
if yc_key_path:
    os.environ["YC_SERVICE_ACCOUNT_KEY_FILE"] = yc_key_path

config = pulumi.Config("yandex")

cloud_id = config.require("cloudId")
folder_id = config.require("folderId")
zone = config.require("zone")

# Security Group
sg = yc.VpcSecurityGroup("vm-sg",
    network_id="enp7tav0a2330i6uh850"
)

# SSH rule
yc.VpcSecurityGroupRule("ssh-rule",
    security_group_binding=sg.id,
    direction="ingress",
    protocol="TCP",
    description="SSH",
    v4_cidr_blocks=["0.0.0.0/0"],
    port=22
)

# HTTP rule
yc.VpcSecurityGroupRule("http-rule",
    security_group_binding=sg.id,
    direction="ingress",
    protocol="TCP",
    description="HTTP",
    v4_cidr_blocks=["0.0.0.0/0"],
    port=80
)

# App rule
yc.VpcSecurityGroupRule("app-rule",
    security_group_binding=sg.id,
    direction="ingress",
    protocol="TCP",
    description="App",
    v4_cidr_blocks=["0.0.0.0/0"],
    port=5000
)

# Egress rule
yc.VpcSecurityGroupRule("egress-rule",
    security_group_binding=sg.id,
    direction="egress",
    protocol="ANY",
    v4_cidr_blocks=["0.0.0.0/0"]
)


with open("C:/Users/Admin/.ssh/id_ed25519.pub") as f:
    ssh_key = f.read()

# VM
vm = yc.ComputeInstance("pulumi-vm",
    name="pulumi-vm",
    platform_id="standard-v1",
    zone=zone,
    resources=yc.ComputeInstanceResourcesArgs(
        cores=2,
        memory=1,
        core_fraction=20
    ),
    boot_disk=yc.ComputeInstanceBootDiskArgs(
        initialize_params=yc.ComputeInstanceBootDiskInitializeParamsArgs(
            image_id="fd8v7ru46kt3s4o5f0uo"
        )
    ),
    network_interfaces=[yc.ComputeInstanceNetworkInterfaceArgs(
        subnet_id="e9bf2ea6o6db4rj57f8i",
        nat=True,
        security_group_ids=[sg.id]
    )],
    metadata={
        "ssh-keys": "ubuntu:" + ssh_key
    }
)

pulumi.export("external_ip", vm.network_interfaces[0].nat_ip_address)
