from aws_cdk import Stack, aws_ec2 as ec2
from constructs import Construct


class NetworkStack(Stack):
    """
    VPC con NAT Instance t4g.nano para que el Lambda de subscriptions
    pueda alcanzar api.dlocalgo.com desde una IP de EC2 (no hyperplane).

    Arquitectura (single-AZ, costo ~$4/mes):
      Internet Gateway
          └── subnet pública  → NAT Instance t4g.nano + EIP
          └── subnet privada  → subscriptions Lambda

    DynamoDB Gateway Endpoint (gratis): el tráfico a DynamoDB
    no pasa por el NAT, va directo por la red interna de AWS.
    """

    def __init__(
        self,
        scope: Construct,
        construct_id: str,
        *,
        config: dict,
        **kwargs,
    ) -> None:
        super().__init__(scope, construct_id, **kwargs)

        env = config["env"]

        self.vpc = ec2.Vpc(
            self,
            "Vpc",
            vpc_name=f"codelabs-billing-{env}",
            max_azs=1,
            nat_gateways=1,
            nat_gateway_provider=ec2.NatProvider.instance_v2(
                instance_type=ec2.InstanceType("t4g.nano"),
                default_allowed_traffic=ec2.NatTrafficDirection.INBOUND_AND_OUTBOUND,
            ),
            subnet_configuration=[
                ec2.SubnetConfiguration(
                    name="public",
                    subnet_type=ec2.SubnetType.PUBLIC,
                    cidr_mask=24,
                ),
                ec2.SubnetConfiguration(
                    name="private",
                    subnet_type=ec2.SubnetType.PRIVATE_WITH_EGRESS,
                    cidr_mask=24,
                ),
            ],
        )

        # Tráfico a DynamoDB va por red interna de AWS, no por el NAT.
        self.vpc.add_gateway_endpoint(
            "DynamoDbEndpoint",
            service=ec2.GatewayVpcEndpointAwsService.DYNAMODB,
        )
