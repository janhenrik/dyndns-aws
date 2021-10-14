from aws_cdk import (
    aws_iam as iam,
    core,
    aws_apigateway as apigateway,
    aws_lambda as lambda_
)
import os


class DynDnsLambdaTemplate(core.Stack):
    def __init__(self, app: core.App, id: str, **kwargs) -> None:
        super().__init__(app, id)
        api = apigateway.RestApi(self, "dyndns-api",
                                 rest_api_name="DynDns Service",
                                 description="This service adjusts domain pointers in route53.")

        zoneArn = 'arn:aws:route53:::hostedzone/' + \
            os.environ["ROUTE_53_ZONE_ID"]
        lambda_policy = iam.ManagedPolicy(scope=self, id='dyndns-managed-policy',
                                          statements=[
                                              iam.PolicyStatement(
                                                  actions=[
                                                      "route53:ListResourceRecordSets",
                                                      "route53:ChangeResourceRecordSets"
                                                  ],
                                                  resources=[
                                                      zoneArn
                                                  ], effect=iam.Effect.ALLOW
                                              )
                                          ])

        lambda_role = iam.Role(scope=self, id='dyndns-lambda-role',
                               assumed_by=iam.ServicePrincipal(
                                   'lambda.amazonaws.com'),
                               role_name='dyndns-lambda-role',
                               managed_policies=[
                                   iam.ManagedPolicy.from_aws_managed_policy_name(
                                       'service-role/AWSLambdaBasicExecutionRole'),
                                   lambda_policy
                               ])

        handler = lambda_.Function(self, "DynDnsHandler",
                                   runtime=lambda_.Runtime.PYTHON_3_9,
                                   code=lambda_.Code.from_asset("resources"),
                                   handler="dyndns.handler",
                                   role=lambda_role,
                                   environment=dict(
                                       ROUTE_53_ZONE_ID=os.environ["ROUTE_53_ZONE_ID"],
                                       SET_HOSTNAME=os.environ["SET_HOSTNAME"],
                                       SHARED_SECRET=os.environ["SHARED_SECRET"]
                                   ))

        get_dyndns_integration = apigateway.LambdaIntegration(handler,
                                                              request_templates={"application/json": '{ "statusCode": "200" }'})

        api.root.add_method("GET", get_dyndns_integration,
                            api_key_required=True)
        plan = api.add_usage_plan('dyndns-usage-plan',
                                  throttle=apigateway.ThrottleSettings(burst_limit=2, rate_limit=10))
        key = api.add_api_key(id='dyndns-api-key')
        plan.add_api_stage(stage=api.deployment_stage)
        plan.add_api_key(key)

app = core.App()
DynDnsLambdaTemplate(app, "DynDnsLambdaTemplate", env={'region': 'us-east-1'})
app.synth()
