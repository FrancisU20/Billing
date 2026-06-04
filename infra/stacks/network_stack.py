# v2026.06.04
from aws_cdk import Stack, aws_ec2 as ec2, aws_iam as iam
from constructs import Construct


class NetworkStack(Stack):
    def __init__(self, scope: Construct, construct_id: str, config: dict, **kwargs):
        super().__init__(scope, construct_id, **kwargs)

        net_cfg = config["network"]
        nat_type = net_cfg["nat_type"]
        az_count = net_cfg["availability_zones"]
        # nat_count permite tener 2 AZs pero solo 1 NAT (dev: 1 AZ sin HA)
        nat_count = net_cfg.get("nat_count", az_count)

        if nat_type == "gateway":
            nat_provider = ec2.NatProvider.gateway()
        else:
            # NAT Instance (t4g.nano) — ~$4/mes vs $35/mes para NAT Gateway
            instance_type = ec2.InstanceType(net_cfg["nat_instance_type"])
            nat_provider = ec2.NatProvider.instance_v2(
                instance_type=instance_type,
                default_allowed_traffic=ec2.NatTrafficDirection.OUTBOUND_ONLY,
            )

        self.vpc = ec2.Vpc(
            self, "Vpc",
            vpc_name=f"codelabs-billing-{config['env']}-vpc",
            max_azs=az_count,
            nat_gateways=nat_count,
            nat_gateway_provider=nat_provider,
            subnet_configuration=[
                ec2.SubnetConfiguration(
                    name="Public",
                    subnet_type=ec2.SubnetType.PUBLIC,
                    cidr_mask=24,
                ),
                ec2.SubnetConfiguration(
                    name="Private",
                    subnet_type=ec2.SubnetType.PRIVATE_WITH_EGRESS,
                    cidr_mask=24,
                ),
                ec2.SubnetConfiguration(
                    name="Isolated",
                    subnet_type=ec2.SubnetType.PRIVATE_ISOLATED,
                    cidr_mask=24,
                ),
            ],
        )

        # SSM en NAT instance — permite SSM port forwarding para acceso local a Aurora
        # El role del NAT instance lo crea CDK automáticamente; usamos el construct tree
        # para agregarle AmazonSSMManagedInstanceCore sin cambiar el NatProvider.
        if nat_type == "instance":
            ssm_policy = iam.ManagedPolicy.from_aws_managed_policy_name(
                "AmazonSSMManagedInstanceCore"
            )
            for subnet in self.vpc.public_subnets:
                try:
                    nat_instance_role = (
                        subnet.node.find_child("NatInstance")
                        .node.find_child("InstanceRole")
                    )
                    nat_instance_role.add_managed_policy(ssm_policy)
                except Exception:
                    pass  # Solo aplica cuando nat_type=instance

        # VPC Endpoints — evita tráfico por NAT para servicios AWS internos
        self.vpc.add_gateway_endpoint(
            "S3Endpoint",
            service=ec2.GatewayVpcEndpointAwsService.S3,
        )

        self.vpc.add_interface_endpoint(
            "SecretsManagerEndpoint",
            service=ec2.InterfaceVpcEndpointAwsService.SECRETS_MANAGER,
            private_dns_enabled=True,
        )

        self.vpc.add_interface_endpoint(
            "SqsEndpoint",
            service=ec2.InterfaceVpcEndpointAwsService.SQS,
            private_dns_enabled=True,
        )
