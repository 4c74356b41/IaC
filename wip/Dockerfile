FROM python:3.6-jessie

RUN curl -fsSL https://get.pulumi.com | sh
RUN PATH="/root/.pulumi/bin:$PATH"; pip install pulumi pulumi-azure pulumi-kubernetes azure azure-graphrbac
# needed because /root/.pulumi/bin is restricted in vsts, pulumi doesnt work
RUN find /root/.pulumi/ -type f | xargs -L 1 -i mv {} /usr/local/bin