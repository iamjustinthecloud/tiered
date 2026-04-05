from aws_cdk import aws_ec2 as ec2


def endpoint_security_group(
    scope, vpc: ec2.IVpc, app_sg: ec2.ISecurityGroup
) -> ec2.SecurityGroup:
    security_group = ec2.SecurityGroup(
        scope,
        "InterfaceEndpointSecurityGroup",
        vpc=vpc,
        description="Allow HTTPS from app security group",
    )
    security_group.add_ingress_rule(
        app_sg,
        ec2.Port.tcp(443),
        "Allow HTTPS from app security group",
    )
    return security_group


def web_alb_security_group(scope, vpc: ec2.IVpc, alb_port: int) -> ec2.SecurityGroup:
    security_group = ec2.SecurityGroup(
        scope,
        "WebAlbSecurityGroup",
        vpc=vpc,
        description="Allow inbound HTTP from the internet to the public ALB",
    )
    security_group.add_ingress_rule(
        ec2.Peer.any_ipv4(),
        ec2.Port.tcp(alb_port),
        "Allow HTTP from the internet",
    )
    return security_group


def app_service_security_group(
    scope, vpc: ec2.IVpc, app_port: int, web_alb_sg: ec2.ISecurityGroup
) -> ec2.SecurityGroup:
    security_group = ec2.SecurityGroup(
        scope,
        "AppSecurityGroup",
        vpc=vpc,
        description="Allow app traffic only from the public ALB",
    )
    security_group.add_ingress_rule(
        web_alb_sg,
        ec2.Port.tcp(app_port),
        "Allow app traffic from the ALB only",
    )
    return security_group


def db_service_security_group(
    scope, vpc: ec2.IVpc, db_port: int, app_sg: ec2.ISecurityGroup
) -> ec2.SecurityGroup:
    security_group = ec2.SecurityGroup(
        scope,
        "DBSecurityGroup",
        vpc=vpc,
        description="Allow database traffic only from the app security group",
    )
    security_group.add_ingress_rule(
        app_sg,
        ec2.Port.tcp(db_port),
        "Allow database traffic from the app security group only",
    )
    return security_group
