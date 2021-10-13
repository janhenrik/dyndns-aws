from aws_cdk import (
    aws_s3 as s3,
    aws_iam as iam,
    core,
    aws_apigateway as apigateway,
    aws_lambda as lambda_
)
class DynDnsLambdaTemplate(core.Stack):
    def __init__(self, app: core.App, id: str, **kwargs) -> None:
        super().__init__(app, id)
        #create an S3 bucket
        bucket = s3.Bucket(self, "DynDnsStore")

        api = apigateway.RestApi(self, "dyndns-api",
                  rest_api_name="DynDns Service",
                  description="This service adjusts domain pointers in route53.")

        lambda_policy = iam.ManagedPolicy(scope=self, id='dyndns-managed-policy',
                        statements=[
                            iam.PolicyStatement(
                                actions=[
                                    "route53:ListResourceRecordSets",
                                    "route53:ChangeResourceRecordSets" 
                               ],
                                resources=[
                                    'arn:aws:route53:::hostedzone/Z02438639VH134V380MR'
                                ], effect=iam.Effect.ALLOW
                            )
                        ])

        lambda_role = iam.Role(scope=self, id='dyndns-lambda-role',
                        assumed_by =iam.ServicePrincipal('lambda.amazonaws.com'),
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
                    BUCKET=bucket.bucket_name)
                    )
        bucket.grant_read_write(handler)



        get_dyndns_integration = apigateway.LambdaIntegration(handler,
                request_templates={"application/json": '{ "statusCode": "200" }'})

        api.root.add_method("GET", get_dyndns_integration)   # GET /
app = core.App()
DynDnsLambdaTemplate(app, "DynDnsLambdaTemplate", env={'region':'us-east-1'})
app.synth()