import aws_cdk.aws_ec2 as ec2
from aws_cdk import CfnTag, Stack
from cdk_nag import NagSuppressions
from constructs import Construct

from networking.security_groups import (
    app_service_security_group,
    endpoint_security_group,
    web_alb_security_group,
    db_service_security_group,
)


class NetworkingStack(Stack):
    def __init__(self, scope: Construct, construct_id: str, **kwargs) -> None:
        super().__init__(scope, construct_id, **kwargs)

        self.vpc = ec2.Vpc(
            self,
            "VPC",
            vpc_name="NetworkingVpc",
            ip_addresses=ec2.IpAddresses.cidr("10.0.0.0/16"),
            nat_gateways=0,
            max_azs=2,
            create_internet_gateway=False,
            enable_dns_support=True,
            enable_dns_hostnames=True,
            subnet_configuration=[
                ec2.SubnetConfiguration(
                    name="public", subnet_type=ec2.SubnetType.PUBLIC, cidr_mask=20
                ),
                ec2.SubnetConfiguration(
                    name="private_app",
                    subnet_type=ec2.SubnetType.PRIVATE_ISOLATED,
                    cidr_mask=20,
                ),
                ec2.SubnetConfiguration(
                    name="private_db",
                    subnet_type=ec2.SubnetType.PRIVATE_ISOLATED,
                    cidr_mask=20,
                ),
            ],
        )
        self.web_alb_sg = web_alb_security_group(self, self.vpc, alb_port=80)
        self.app_service_sg = app_service_security_group(
            self, self.vpc, app_port=80, web_alb_sg=self.web_alb_sg
        )
        self.endpoint_sg = endpoint_security_group(
            self, self.vpc, app_sg=self.app_service_sg
        )
        self.db_service_sg = db_service_security_group(
            self, self.vpc, db_port=3306, app_sg=self.app_service_sg
        )
        self.cfn_internet_gateway = ec2.CfnInternetGateway(
            self,
            "InternetGateway",
            tags=[
                CfnTag(key="Name", value="InternetGateway"),
            ],
        )
        self.cfn_vpc_attachment = ec2.CfnVPCGatewayAttachment(
            self,
            "VpcAttachment",
            vpc_id=self.vpc.vpc_id,
            internet_gateway_id=self.cfn_internet_gateway.ref,
        )

        for index, subnet in enumerate(self.vpc.public_subnets, start=1):
            public_default_route = ec2.CfnRoute(
                self,
                f"PublicDefaultRoute{index}",
                route_table_id=subnet.route_table.route_table_id,
                destination_cidr_block="0.0.0.0/0",
                gateway_id=self.cfn_internet_gateway.ref,
            )
            public_default_route.add_dependency(self.cfn_vpc_attachment)

        self.vpc.add_interface_endpoint(
            "ECRInterfaceEndpoint",
            open=False,
            service=ec2.InterfaceVpcEndpointAwsService.ECR,
            subnets=ec2.SubnetSelection(
                subnet_group_name="private_app",
            ),
            security_groups=[self.endpoint_sg],
        )
        self.vpc.add_interface_endpoint(
            "DKRInterfaceEndpoint",
            open=False,
            service=ec2.InterfaceVpcEndpointAwsService.ECR_DOCKER,
            subnets=ec2.SubnetSelection(subnet_group_name="private_app"),
            security_groups=[self.endpoint_sg],
        )
        self.vpc.add_interface_endpoint(
            "CloudWatchLogsInterfaceEndpoint",
            open=False,
            service=ec2.InterfaceVpcEndpointAwsService.CLOUDWATCH_LOGS,
            subnets=ec2.SubnetSelection(
                subnet_group_name="private_app",
            ),
            security_groups=[self.endpoint_sg],
        )
        self.vpc.add_gateway_endpoint(
            "S3GatewayEndpoint",
            service=ec2.GatewayVpcEndpointAwsService.S3,
            subnets=[
                ec2.SubnetSelection(
                    subnet_group_name="private_app",
                )
            ],
        )
        NagSuppressions.add_resource_suppressions(
            construct=self.vpc,
            suppressions=[
                {
                    "id": "AwsSolutions-VPC7",
                    "reason": "Flow Logs are intentionally deferred in this "
                    "personal POC during "
                    "M3 to avoid added logging cost before the runtime "
                    "validation gate.",
                }
            ],
            apply_to_children=True,
        )
        NagSuppressions.add_resource_suppressions(
            self.web_alb_sg,
            [
                {
                    "id": "AwsSolutions-EC23",
                    "reason": "This security group is intentionally attached to a "
                    "public ALB and allows only HTTP ingress on port 80.",
                }
            ],
        )
