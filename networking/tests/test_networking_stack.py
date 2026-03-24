import unittest
from typing import Mapping, Any

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

    def _interface_endpoint_by_id(
        self, interface_endpoint_name: str
    ) -> dict[str, Mapping[str, Any]]:
        endpoint_resources = self.template.find_resources("AWS::EC2::VPCEndpoint")
        return {
            logical_id: resource
            for logical_id, resource in endpoint_resources.items()
            if interface_endpoint_name in logical_id
        }

    def _single_interface_endpoint_with_id(
        self, endpoint_resource: str
    ) -> tuple[str, Mapping[str, Any]]:
        interface_endpoints = self._interface_endpoint_by_id(endpoint_resource)
        self.assertEqual(len(interface_endpoints), 1)
        return next(iter(interface_endpoints.items()))

    @staticmethod
    def _interface_endpoint_subnet_ids(
        interface_endpoint_resource: Mapping[str, Any],
    ) -> set[str]:
        return {
            subnet_id["Ref"]
            for subnet_id in interface_endpoint_resource["Properties"]["SubnetIds"]
        }

    @staticmethod
    def _join_service_name_parts(interface_endpoint: Mapping[str, Any]) -> list[Any]:
        return interface_endpoint["Properties"]["ServiceName"]["Fn::Join"][1]

    def _route_table_ids_for_subnets(self, subnet_ids: set[str]) -> set[str]:
        association_resources = self.template.find_resources(
            "AWS::EC2::SubnetRouteTableAssociation"
        )
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
        private_app_route_table_ids = self._route_table_ids_for_subnets(
            private_app_subnet_ids
        )
        default_route_table_ids = self._default_route_table_ids()
        self.assertEqual(len(private_app_subnet_ids), 2)
        self.assertTrue(default_route_table_ids.isdisjoint(private_app_route_table_ids))

    def test_private_db_address(self) -> None:
        private_db_subnet_ids = self._subnet_ids_by_name("private_db")
        private_db_route_table_ids = self._route_table_ids_for_subnets(
            private_db_subnet_ids
        )
        default_route_table_ids = self._default_route_table_ids()
        self.assertEqual(len(private_db_subnet_ids), 2)
        self.assertTrue(default_route_table_ids.isdisjoint(private_db_route_table_ids))

    def test_vpc_attachment(self) -> None:
        vpc_attachment = self.template.find_resources("AWS::EC2::VPCGatewayAttachment")
        self.assertEqual(len(vpc_attachment), 1)

    def test_vpc_nat_gateway(self) -> None:
        nat_gateway = self.template.find_resources("AWS::EC2::NatGateway")
        self.assertEqual(len(nat_gateway), 0)

    def test_internet_gateway(self) -> None:
        internet_gateway = self.template.find_resources("AWS::EC2::InternetGateway")
        self.assertEqual(len(internet_gateway), 1)

    def test_subnet_route_table_associations(self) -> None:
        subnet_route_table_association = self.template.find_resources(
            "AWS::EC2::SubnetRouteTableAssociation"
        )
        self.assertEqual(len(subnet_route_table_association), 6)

    def test_route_tables(self) -> None:
        route_table = self.template.find_resources("AWS::EC2::RouteTable")
        self.assertEqual(len(route_table), 6)

    def test_subnets(self) -> None:
        subnets = self.template.find_resources("AWS::EC2::Subnet")
        self.assertEqual(len(subnets), 6)

    def test_public_default_route(self) -> None:
        route_resources = self.template.find_resources("AWS::EC2::Route")
        destination_cidrs = [
            resource["Properties"]["DestinationCidrBlock"]
            for resource in route_resources.values()
        ]
        self.assertEqual(len(destination_cidrs), 2)
        self.assertSetEqual(set(destination_cidrs), {"0.0.0.0/0"})
        default_public_route = [
            resource["Properties"]["GatewayId"]["Ref"]
            for resource in route_resources.values()
            if resource["Properties"].get("GatewayId", {}).get("Ref")
            == "InternetGateway"
        ]
        self.assertSetEqual(set(default_public_route), {"InternetGateway"})

    def test_expected_subnet_cidrs(self) -> None:
        subnet_resources = self.template.find_resources("AWS::EC2::Subnet")
        cidr_blocks = sorted(
            resource["Properties"]["CidrBlock"]
            for resource in subnet_resources.values()
        )

        self.assertEqual(
            cidr_blocks,
            [
                "10.0.0.0/20",
                "10.0.16.0/20",
                "10.0.32.0/20",
                "10.0.48.0/20",
                "10.0.64.0/20",
                "10.0.80.0/20",
            ],
        )

    # VPC Interface Endpoint tests
    def test_interface_endpoint(self) -> None:
        interface_endpoint_name = "ECRInterfaceEndpoint"
        private_db_subnets = self._subnet_ids_by_name("private_db")
        private_app_subnets = self._subnet_ids_by_name("private_app")
        public_subnets = self._subnet_ids_by_name("public")
        logical_id, interface_endpoint = self._single_interface_endpoint_with_id(
            interface_endpoint_name
        )
        subnet_ids = self._interface_endpoint_subnet_ids(interface_endpoint)

        self.assertIn(".ecr.api", self._join_service_name_parts(interface_endpoint))
        self.assertEqual(subnet_ids, private_app_subnets)
        self.assertTrue(subnet_ids.isdisjoint(private_db_subnets))
        self.assertTrue(subnet_ids.isdisjoint(public_subnets))
        self.assertIn("ECRInterfaceEndpoint", logical_id)

    def test_dkr_interface_endpoints(self) -> None:
        interface_endpoint_name = "DKRInterfaceEndpoint"
        private_app_subnets = self._subnet_ids_by_name("private_app")
        logical_id, interface_endpoint = self._single_interface_endpoint_with_id(
            interface_endpoint_name
        )
        subnet_ids = self._interface_endpoint_subnet_ids(interface_endpoint)
        self.assertEqual(subnet_ids, private_app_subnets)
        self.assertIn(".ecr.dkr", self._join_service_name_parts(interface_endpoint))
        self.assertIn(interface_endpoint_name, logical_id)

    def test_interface_endpoints_security_groups(self) -> None:
        security_groups = self.template.find_resources("AWS::EC2::SecurityGroup")
        vpc_endpoints = self.template.find_resources("AWS::EC2::VPCEndpoint")
        expected_sg_ids = set(security_groups.keys())

        security_group = next(iter(security_groups.values()))
        ingress_rules = security_group["Properties"]["SecurityGroupIngress"]
        string_cidrs = [
            rule["CidrIp"]
            for rule in ingress_rules
            if isinstance(rule.get("CidrIp"), str)
        ]
        non_string_cidrs = [
            rule["CidrIp"]
            for rule in ingress_rules
            if not isinstance(rule.get("CidrIp"), str)
        ]

        vpc_endpoint_sg_id = {
            sg_ref["Fn::GetAtt"][0]
            for resource in vpc_endpoints.values()
            for sg_ref in resource["Properties"].get("SecurityGroupIds", [])
        }

        self.assertSetEqual(expected_sg_ids, vpc_endpoint_sg_id)

        self.assertIn("10.0.32.0/20", string_cidrs)
        self.assertIn("10.0.48.0/20", string_cidrs)

        self.assertEqual(non_string_cidrs, [])
        self.assertEqual(len(security_groups), 1)
        for rule in ingress_rules:
            self.assertEqual(rule["IpProtocol"], "tcp")
            self.assertEqual(rule["FromPort"], 443)
            self.assertEqual(rule["ToPort"], 443)
