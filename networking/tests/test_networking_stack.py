import unittest

from aws_cdk import App
from aws_cdk.assertions import Template

from networking.networking_stack import NetworkingStack

class TestNetworkingStack(unittest.TestCase):
    def setUp(self) -> None:
        app = App()
        stack = NetworkingStack(app, "NetworkingStack")
        self.template = Template.from_stack(stack)

    def _subnet_ids_by_name(self, subnet_name: str) -> set[str]:
        subnet_resources = self.template.find_resources("AWS::EC2::Subnet")
        return {
            logical_id
            for logical_id, resource in subnet_resources.items()
            if any(
                tag["Key"] == "aws-cdk:subnet-name" and tag["Value"] == subnet_name
                for tag in resource["Properties"].get("Tags", [])
            )
        }

    def _route_table_ids_for_subnets(self, subnet_ids: set[str]) -> set[str]:
        association_resources = self.template.find_resources("AWS::EC2::SubnetRouteTableAssociation")
        return {
            resource["Properties"]["RouteTableId"]["Ref"]
            for resource in association_resources.values()
            if resource["Properties"]["SubnetId"]["Ref"] in subnet_ids
        }

    def _default_route_table_ids(self) -> set[str]:
        route_resources = self.template.find_resources("AWS::EC2::Route")
        return {
            resource["Properties"]["RouteTableId"]["Ref"]
            for resource in route_resources.values()
            if resource["Properties"]["DestinationCidrBlock"] == "0.0.0.0/0"
        }

    def test_private_app_route_tables_have_no_default_route(self) -> None:
        private_app_subnet_ids = self._subnet_ids_by_name("private_app")
        private_app_route_table_ids = self._route_table_ids_for_subnets(private_app_subnet_ids)
        default_route_table_ids = self._default_route_table_ids()
        self.assertEqual(len(private_app_subnet_ids), 2)
        self.assertTrue(default_route_table_ids.isdisjoint(private_app_route_table_ids))

    def test_private_db_address(self) -> None:
        private_db_subnet_ids = self._subnet_ids_by_name("private_db")
        private_db_route_table_ids = self._route_table_ids_for_subnets(private_db_subnet_ids)
        default_route_table_ids = self._default_route_table_ids()
        self.assertEqual(len(private_db_subnet_ids), 2)
        self.assertTrue(default_route_table_ids.isdisjoint(private_db_route_table_ids))


    def test_creates_expected_resource_counts(self)->None:
        expected_resource_counts = {
            "AWS::EC2::VPC": 1,
            "AWS::EC2::Subnet": 6,
            "AWS::EC2::RouteTable": 6,
            "AWS::EC2::SubnetRouteTableAssociation": 6,
            "AWS::EC2::InternetGateway": 1,
            "AWS::EC2::VPCGatewayAttachment": 1,
            "AWS::EC2::Route": 2,
            "AWS::EC2::NatGateway": 0,
        }
        for resource_type, expected_resource_count in expected_resource_counts.items():
            self.template.resource_count_is(resource_type, expected_resource_count)

    def test_public_default_route(self)-> None:
        route_resources = self.template.find_resources("AWS::EC2::Route")
        destination_cidrs = [
            resource["Properties"]["DestinationCidrBlock"]
            for resource in route_resources.values()]
        self.assertEqual(len(destination_cidrs), 2)
        self.assertSetEqual(set(destination_cidrs), {"0.0.0.0/0"})
        default_public_route = [
            resource["Properties"]["GatewayId"]["Ref"]
            for resource in route_resources.values()
            if resource["Properties"].get("GatewayId", {}).get("Ref") == "InternetGateway"
        ]
        self.assertSetEqual(set(default_public_route), {"InternetGateway"})



    def test_expected_subnet_cidrs(self) -> None:
        subnet_resources = self.template.find_resources("AWS::EC2::Subnet")
        cidr_blocks = sorted(
            resource["Properties"]["CidrBlock"]
            for resource in subnet_resources.values())

        self.assertEqual(cidr_blocks, [
            "10.0.0.0/20",
            "10.0.16.0/20",
            "10.0.32.0/20",
            "10.0.48.0/20",
            "10.0.64.0/20",
            "10.0.80.0/20",
        ]
    )

    def test_interface_endpoints_security_groups(self)->None:

        security_groups = self.template.find_resources("AWS::EC2::SecurityGroup")
        security_group = next(iter(security_groups.values()))
        ingress_rules = security_group["Properties"]["SecurityGroupIngress"]
        sg_ingress_rules = [
            ingress_rule["CidrIp"]
            for resource in security_groups.values()
            for ingress_rule in resource["Properties"].get("SecurityGroupIngress", [])
                          ]
        self.assertEqual(sorted(sg_ingress_rules), sorted(['10.0.48.0/20','10.0.32.0/20']))
        self.assertTrue(len(sg_ingress_rules) == 2)
        self.assertNotIn("0.0.0.0/0",sg_ingress_rules)
        self.assertEqual(len(security_groups), 1)
        for rule in ingress_rules:
            self.assertEqual(rule["IpProtocol"], "tcp")
            self.assertEqual(rule["FromPort"], 443)
            self.assertEqual(rule["ToPort"], 443)