#!/usr/bin/env python3

import aws_cdk as cdk
from cdk_nag import AwsSolutionsChecks

from networking.networking_stack import NetworkingStack

app = cdk.App()
NetworkingStack(app, "NetworkingStack")

# Get the CDK aspect manager for my app, create the AWS Solutions cdk-nag checker,
# and register that checker so it runs against the constructs in the app during
# synthesis.

cdk.Aspects.of(app).add(AwsSolutionsChecks(verbose=True))

# cdk.Aspects.of(app).add(AwsSolutionsChecks()) -> AwsSolutionsChecks() is the instance
# of AwsSolutionsChecks !Correct!
# cdk.Aspects.of(app).add(AwsSolutionsChecks) -> AwsSolutionsChecks is the class itself
# !Incorrect!
# Using the class causes: TypeError: Don't know how to convert object to
# JSON: <class 'cdk_nag.AwsSolutionsChecks'>
app.synth()


"""
import aws_cdk as cdk -> the cdk alias for aws_cdk becomes the container for objects
in the aws_cdk library


cdk -> module alias for aws_cdk
Aspects -> a class
of -> a method on that class
app -> an argument

cdk.Aspects -> inside the cdk module, get Aspects class

"""
