from aws_cdk import aws_ec2 as ec2


def endpoint_security_group(scope, vpc: ec2.IVpc) -> ec2.SecurityGroup:
    security_group = ec2.SecurityGroup(
        scope,
        "InterfaceEndpointSecurityGroup",
        vpc=vpc,
        description="Allow inbound TCP 443 to the endpoint security group "
        "from 'private_app' subnet CIDR ranges for now",
    )
    security_group.add_ingress_rule(
        ec2.Peer.ipv4("10.0.32.0/20"),
        ec2.Port.tcp(443),
        "Allow HTTPS from private_app subnet AZ A",
    )

    security_group.add_ingress_rule(
        ec2.Peer.ipv4("10.0.48.0/20"),
        ec2.Port.tcp(443),
        "Allow HTTPS from private_app subnet AZ B",
    )
    return security_group
