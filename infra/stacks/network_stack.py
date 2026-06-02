from aws_cdk import Stack, aws_ec2 as ec2
from constructs import Construct


class NetworkStack(Stack):
    def __init__(self, scope: Construct, construct_id: str, config: dict, **kwargs):
        super().__init__(scope, construct_id, **kwargs)

        nat_type = config["network"]["nat_type"]
        az_count = config["network"]["availability_zones"]

        if nat_type == "gateway":
            nat_provider = ec2.NatProvider.gateway()
        else:
            # NAT Instance (t4g.nano) — ~$4/mes vs $35/mes para NAT Gateway
            # Sin SLA de AWS, acceptable para dev/bootstrapping
            instance_type = ec2.InstanceType(config["network"]["nat_instance_type"])
            nat_provider = ec2.NatProvider.instance_v2(
                instance_type=instance_type,
                default_allowed_traffic=ec2.NatTrafficDirection.OUTBOUND_ONLY,
            )

        self.vpc = ec2.Vpc(
            self, "Vpc",
            vpc_name=f"codelabs-billing-{config['env']}-vpc",
            max_azs=az_count,
            nat_gateways=az_count,
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

        # VPC Endpoints para servicios AWS frecuentes — evita tráfico por NAT
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
