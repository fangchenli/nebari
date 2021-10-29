# Minikube

[Minikube](https://minikube.sigs.k8s.io/docs/) is a project allowing you to run a local Kubernetes node simulation for development and testing purposes.

It is possible to run QHub on Minikube, and this can allow quicker feedback loops for development, as well as being less
expensive than running cloud Kubernetes clusters.

Local testing is a great way to test the components of QHub. It is
important to highlight that while it is possible to test most of QHub
with this version, components that are Cloud provisioned such as:
VPCs, managed Kubernetes cluster and managed container registries
cannot be locally tested, due to their Cloud dependencies.

## Compatibility

Currently, **QHub local deployment is primarily compatible with Linux-based
Operating Systems**. The main limitation for the installation on
MacOS relates to [Docker Desktop for
Mac](https://docs.docker.com/docker-for-mac/networking/#known-limitations-use-cases-and-workarounds)
being unable to route traffic to containers.  Theoretically, the
installation of HyperKit Driver could solve the issue, although the
proposed solution has not yet been tested. There some workarounds for running [Minikube on Mac below](#minikube-on-mac).

This guide assumes that you have the QHub repository downloaded, and you are at the root of the repository.

## Dependencies

> NOTE: The following instructions apply **only to Linux OS**.

To deploy QHub locally requires the installation of the following dependencies:
+ [Minikube](https://v1-18.docs.kubernetes.io/docs/tasks/tools/install-minikube/) version 1.10.0-beta and up
+ [Docker Engine driver](https://docs.docker.com/engine/install/ubuntu/#install-using-the-repository) install.

The installation of a hypervisor is **not** necessary.

> NOTE: Minikube requires `kubectl` OR you can use the embedded kubectl appropriate for your Minikube cluster version using `minikube kubectl`.
> To install `kubectl` [follow the instructions](https://v1-18.docs.kubernetes.io/docs/tasks/tools/install-kubectl/) according to your operating system.


## Initialize kubernetes cluster

Before proceeding with the initialization, make sure to add yourself to the
Docker group by executing the command `sudo usermod -aG docker <username> && newgrp docker`.

Testing is done with Minikube.

To confirm successful installation of both Docker and Minikube,
you can run the following command to start up a local Kubernetes
cluster:

```shell
minikube start --cpus 2 --memory 4096 --driver=docker
```
The command will download a Docker image of around 500Mb in size and initialise a cluster with 2 CPUs and 4Gb
of RAM, with Docker as the chosen driver.


Once `minikube start` finishes, run the command below to check the
status of the cluster:

```bash
minikube status
```

If your cluster is running, the output from minikube status should be
similar to:

```bash
minikube
type: Control Plane
host: Running
kubelet: Running
apiserver: Running
kubeconfig: Configured
timeToStop: Nonexistent
```

After you have confirmed that Minikube is working, you can either continue to
use, or you can stop your cluster. To stop your cluster, run:

```bash
minikube stop
```

Next, we will install `nfs-common` drivers. This is required by the JupyterLab instances, which require NFS mount for
`PersistentVolumeClaims` (PVCs). To install it, run:

```shell
minikube ssh "sudo apt update; sudo apt install nfs-common -y"
```
For more details on PVs and PVCs, read the [JupyterHub documentation](https://zero-to-jupyterhub.readthedocs.io/en/latest/jupyterhub/customizing/user-storage.html).

## Optional pre-pulling and caching of docker images
<details>
  <summary>Click to expand note</summary>

### Why Pre-pull Docker Images

As part of deployment, Minikube will download docker images that have a combined size of several Gigabytes. Each time minikube is destroyed and created it will re-pull these images. Also, terraform will timeout on slower internet connections if it takes longer than 10 minutes to pull the images.

Images can be pre-pulled and added to the Minikube cache. This greatly reduce the time required for future deployments and reduces the data requiring download during deployment.

### Pre-pulling and Caching

The following assumes that docker is currently installed.

The first step is to configure the minikube home directory environment variable. To set this to the home directory of the current user, run:

```bash
export MINIKUBE_HOME=$HOME/.minikube
```

The current list of docker images can be seen in `qhub-config.yaml`
under the `default_images` key. Each image will need to be pulled like
so:

```bash
docker pull quansight/qhub-jupyterhub:v0.x.x
docker pull quansight/qhub-jupyterlab:v0.x.x
docker pull quansight/qhub-dask-worker:v0.x.x
docker pull quansight/qhub-dask-gateway:v0.x.x
docker pull quansight/qhub-conda-store:v0.x.x
```

Replacing `v0.x.x` with the current version that is listed. Note this may take several minutes.

After the images are pulled, they can be copied to the Minikube cache like so:

```bash
minikube image load quansight/qhub-jupyterhub:v0.x.x
minikube image load quansight/qhub-jupyterlab:v0.x.x
minikube image load quansight/qhub-dask-worker:v0.x.x
minikube image load quansight/qhub-dask-gateway:v0.x.x
minikube image load quansight/qhub-conda-store:v0.x.x
```

Again, adding the correct version. With this completed local Minikube deployment will no longer require pulling the above docker images.

The above process will need to be repeated with the updated tags when a new version of QHub is being deploy.

</details>


## MetalLB

[MetalLB](https://metallb.universe.tf/) is the load balancer for bare-metal Kubernetes clusters. We will need to configure
MetalLB to match the QHub configuration.

## Automation of MetalLB with Python Script
*Skip to next section for configuration without python*

Minikube does not provide a simple interactive way to configure addons,
([as shown in this repository issue](https://github.com/kubernetes/minikube/issues/8283)). It is recommended to set load balancer start/stop IP address using a Python script with pre-established values. This recommendation is due to an existing DNS name that uses some addresses.

To do so, paste
[this Python script](https://github.com/Quansight/qhub/blob/main/tests/scripts/minikube-loadbalancer-ip.py) in a text file named `minikube-loadbalancer-ip.py` and then run:
```shell
python minikube-loadbalancer-ip.py
```

### Manually Configure MetalLB
*Skip this section if above python script was used*

First we need to obtain the Docker image ID:
```shell
$ docker ps --format "{{.Names}} {{.ID}}"
minikube <image-id>
```

Copy the output image id and use it in the following command to obtain the Docker interface subnet CIDR range:

```shell
$ docker inspect --format='{{range .NetworkSettings.Networks}}{{.IPAddress}}/{{.IPPrefixLen}}{{end}}' <image-id>
```

A example subnet range will look like `192.168.49.2/24`. This CIDR range will have a starting IP of `192.168.49.0` and ending address of `192.168.49.255`. The `metallb` load balancer needs to be given a range of IP addresses that are contained in the docker CIDR range. If your CIDR is different, you can determine your range IP addresses from a CIDR address at [this website](https://www.ipaddressguide.com/cidr).

For this example case, we will assign `metallb` a start IP address of
`192.168.49.100` and an end of `192.168.49.150`.

We can the `metallb` below CLI interface which will prompt for the start and stop IP range:

```shell
minikube addons configure metallb
-- Enter Load Balancer Start IP: 192.168.49.100
-- Enter Load Balancer End IP: 192.168.49.150
```

If successful, the output should be `✅  metallb was successfully configured`.

### Enable MetalLB

After configuration enable MetalLB by running
```shell
minikube addons enable metallb
```
The output should be `The 'metallb' addon is enabled`.

---

## Note for Development on Windows Subsystem for Linux 2 (WSL2)
<details>
  <summary>Click to expand note</summary>

The browser can have trouble reaching the load balancer running on WSL2. A workaround is to port forward the proxy-... pod to the host (ip 0.0.0.0). Get the ip address of the WSL2 machine via ```ip a```, it should be a 127.x.x.x address. To change the port forwarding after opening k9s you can type ```:pods <enter>```, hover over the proxy-... pod and type ```<shift-s>```, and enter the ip addresses.
</details>

## Deploy QHub
To deploy QHub handle setup dependencies and create a new sub-directory by running:
```bash
pip install -e .
mkdir -p data
cd data
```
## Initialize configuration
Then, initialize the configuration file `qhub-config.yaml` with:
```shell
python -m qhub init local --project=thisisatest  --domain github-actions.qhub.dev --auth-provider=password --terraform-state=local
```
## Generate user password
Each user on the `qhub-config.yaml` file will need a password.
A random password is auto generated for the user `example-user` when
the auth provider `password` is run, the value is then printed to the standard output (stdout).

In case you would like to change the generated password (optional), You can use
[bcrypt](https://pypi.org/project/bcrypt/) to generate your own salted password by using the following _Python command_
script:

```bash
python -c "import bcrypt; print(bcrypt.hashpw(b'admin', bcrypt.gensalt()).decode('utf-8'))"
```
Where `<password>` can be changed to any desired value.

This requires the Python package `bcrypt` to be
installed in your virtual environment. The password must then be added to the `qhub-config.yaml` in the users
section, as illustrated below:

```yaml
  users:
    example-user:
      uid: 1000
      ...
      password: '$2b$12$lAk2Bhw8mu0QJkSecPiABOX2m87RF8N7vv7rBw9JksOgewI2thUuO'
      ...
      primary_group: users

```

## Deploy and render the infrastructure
Next, we will render the infrastructure files from `qhub-config.yaml` running

```shell
python -m qhub deploy --config qhub-config.yaml --disable-prompt
```

To ease development, we have already pointed the DNS record
`github-actions.qhub.dev` to `192.168.49.100` so the next step
is optional unless you end up with the load-balancer giving you
a different IP address.

Make sure to point the DNS domain `github-actions.qhub.dev` to
`192.168.49.100` from the previous commands. This can be done in many
ways, the easiest one is by modifying `/etc/hosts` and adding the
line below. The command will override any DNS server.

```ini
192.168.49.100 github-actions.qhub.dev
```

## Verify the local deployment

Finally, if everything is set properly you should be able to `cURL` the JupyterHub Server. Run
```bash
curl -k https://github-actions.qhub.dev/hub/login
```

It is also possible to visit `https://github-actions.qhub.dev` in your web
browser to check the deployment.

Since this is a local deployment, hence not visible to the internet;
`https` certificates will not be signed by [Let's
Encrypt](https://letsencrypt.org/). Thus, the certificates will be
[self-signed by Traefik](https://en.wikipedia.org/wiki/Self-signed_certificate).

Several
browsers will make it difficult to view a self-signed certificate that
has not been added to your certificate registry.

Each web browser handles this differently. A workaround for Firefox:

 - Visit `about:config` and change the `network.stricttransportsecurity.preloadlist` to `false`

And a workaround for Chrome:

 - Type `badidea` or `thisisunsafe` while viewing the rendered page (this has to do with [how Chrome preloads some domains for its HTTP Strict Transport Security](https://hstspreload.org/) list in a way that cannot be manually removed)

## Cleanup

To delete all the QHub resources run the `destroy` command. Note that
this will not delete your `qhub-config.yaml` and related rendered
files thus a re-deployment via `deploy` is possible afterwards.

```shell
python -m qhub destroy --config qhub-config.yaml
```

To delete the Minikube Kubernetes cluster run the following command:

```shell
minikube delete
```
The command will delete all instances of QHub, cleaning up the deployment environment.

---

# Minikube on Mac

The earlier instructions for minikube on Linux should work on Mac except:

1 - When working out the IP addresses to configure metallb try this:
```
docker ps --format "{{.Names}} {{.ID}}"
docker inspect --format='{{range .NetworkSettings.Networks}}{{.IPAddress}}/{{.IPPrefixLen}}{{end}}' <ID of minikube from previous cmd>
```

This will display something like `192.168.49.2/24`, in which case a suitable IP range would be on the same subnet, e.g. start IP 192.168.49.100, end IP 192.168.49.150.

2 - This load balancer won't actually work, so you need to port-forward directly to the JupyterHub service:
```
minikube kubectl -- --namespace=dev port-forward svc/proxy-public 8000:80
```
Then you can access QHub on http://127.0.0.1:8000/

---

# Minikube on AWS

It is possible to run Minikube on AWS (and probably the other clouds). This is useful where you don't have enough memory to run QHub in a local Minikube cluster on your laptop, or if you are using Mac or Windows and struggling to get Minikube to work.

Please understand that running Minikube on an AWS EC2 instance is not the same as 'proper' deployment of QHub to AWS EKS (Kubernetes service). You might prefer Minikube on AWS over full AWS EKS deployment for testing purposes if you find Minikube easier to debug, cheaper to run, or if you want to replicate the Minikube setup directly - for example, if trying to fix the automated Cypress tests which use Minikube within a GitHub actions workflow.

There are some tricks that can make allow Minikube on AWS to feel much like local Minikube for development.

The instructions below should work for Mac.

## Set up AWS Credentials

Set your environment variables for your AWS account:

```bash
export AWS_PROFILE=quansight
export AWS_DEFAULT_REGION="eu-west-2"
```

This assumes you have a 'quansight' profile in your ~/.aws/config and credentials files, but instead you can set `AWS_ACCESS_KEY_ID` and `AWS_SECRET_ACCESS_KEY` directly.

## Create a Key Pair

You can use a Key Pair that is already registered with AWS, or create one as follows:

```bash
aws ec2 create-key-pair \
    --key-name aws-quansight-mykey \
    --query "KeyMaterial" \
    --output text > ~/.ssh/aws-quansight-mykey.pem

chmod 400 ~/.ssh/aws-quansight-mykey.pem
```

## Run the EC2 Instance

The image we want is an Ubuntu 20.04 with Docker installed. We want to run it on a 16 GB/4 Core image, and also increase EBS disk space to 48 GB or so, up from the standard 8 GB.

```bash
aws ec2 run-instances --image-id ami-0cd5fb602c264fbd6 --instance-type t3a.xlarge --count 1 --key-name aws-quansight-mykey --block-device-mappings 'DeviceName=/dev/sda1,Ebs={VolumeSize=48}'
```

Once running, get the instance ID and public DNS:

```bash
aws ec2 describe-instances --query "Reservations[*].Instances[*].{InstanceId:InstanceId,Host:PublicDnsName}"
```

This should show all instances, so work out which one you need if there are multiple.

## Open SSH port access

Using the instance ID you obtained just above (e.g. `i-01bd8a4ee6016e1fe`), use that to first query for the 'security GroupSet ID' (e.g. `sg-96f73feb`).

Then use that to open up port 22 for the security group (and hence for the instance). Note if you have multiple instances running in this security group, all of them will now be exposed on port 22.

```bash
aws ec2 describe-instance-attribute --instance-id i-01bd8a4ee6016e1fe --attribute groupSet

aws ec2 authorize-security-group-ingress --group-id sg-96f73feb --protocol tcp --port 22 --cidr 0.0.0.0/0
```

## SSH into the instance

Using the Public DNS obtained a couple of steps back, you can now SSH into the instance:

```bash
ssh -i ~/.ssh/aws-quansight-mykey.pem ubuntu@ec2-18-130-21-222.eu-west-2.compute.amazonaws.com
```

## Install Minikube etc

Install Minikube and Kubectl:

```bash
curl -LO https://github.com/kubernetes/minikube/releases/download/v1.22.0/minikube-linux-amd64
sudo install minikube-linux-amd64 /usr/local/bin/minikube

curl -LO https://storage.googleapis.com/kubernetes-release/release/v1.19.0/bin/linux/amd64/kubectl
chmod +x kubectl

sudo usermod -aG docker ubuntu && newgrp docker
```

Obtain QHub repo

```bash
git clone https://github.com/Quansight/qhub
```

Set up Minikube - very similar to setup for local Minikube:

```bash
minikube start --cpus 4 --memory 12288 --driver=docker
minikube ssh "sudo apt update; sudo apt install nfs-common -y"

python3 ./qhub/tests/scripts/minikube-loadbalancer-ip.py

minikube addons enable metallb
```

## Init and Deploy QHub

Install Virtualenv and Pip:

```bash
sudo apt install python3-virtualenv
sudo apt install python3-pip
```

Create and activate a virtualenv, install QHub dev:

```bash
cd qhub
virtualenv ./data-venv
. ./data-venv/bin/activate

pip3 install -e .[dev]
```

Create and modify qhub-config.yaml:

```bash
mkdir data-test
cd data-test

export QHUB_GH_BRANCH=main
qhub init local --project=thisisatest  --domain github-actions.qhub.dev --auth-provider=password

sed -i -E 's/(cpu_guarantee):\s+[0-9\.]+/\1: 1/g' "qhub-config.yaml"
sed -i -E 's/(mem_guarantee):\s+[A-Za-z0-9\.]+/\1: 1G/g' "qhub-config.yaml"
```

The last two commands above reduce slightly the memory and CPU requirements of JupyterLab sessions etc. Make any other changes needed to the qhub-config.yaml file.

Then deploy:

```bash
qhub deploy --config qhub-config.yaml --disable-prompt
```

## Enable Minikube access from Mac

On your Mac laptop:

```bash
cd ~
mkdir .minikube_remote
```

Copy these files from the remote instance (home folder):
- .minikube/ca.crt to .minikube_remote/ca.crt
- .minikube/profiles/minikube/client.crt to .minikube_remote/client.crt
- .minikube/profiles/minikube/client.key to .minikube_remote/client.key

For example:
```bash
cd .minikube_remote
scp -i ~/.ssh/aws-quansight-mykey.pem ubuntu@ec2-35-177-109-173.eu-west-2.compute.amazonaws.com:~/.minikube/ca.crt .
scp -i ~/.ssh/aws-quansight-mykey.pem ubuntu@ec2-35-177-109-173.eu-west-2.compute.amazonaws.com:~/.minikube/profiles/minikube/client.crt .
scp -i ~/.ssh/aws-quansight-mykey.pem ubuntu@ec2-35-177-109-173.eu-west-2.compute.amazonaws.com:~/.minikube/profiles/minikube/client.key .
```

Merge the following into your ~/.kube/config file, or just run the command in full to overwrite it:

```bash
cat <<EOF > ~/.kube/config
apiVersion: v1
clusters:
- cluster:
    certificate-authority: ../.minikube_remote/ca.crt
    server: https://127.0.0.1:8443
  name: minikube
contexts:
- context:
    cluster: minikube
    user: minikube
  name: minikube
current-context: minikube
kind: Config
preferences: {}
users:
- name: minikube
  user:
    client-certificate: ../.minikube_remote/client.crt
    client-key: ../.minikube_remote/client.key
EOF
```

Now SSH into the AWS instance, enabling port forwarding so you can access the Minikube cluster as though it is running on your Mac:

```bash
ssh -i ~/.ssh/aws-quansight-mykey.pem ubuntu@ec2-18-130-21-222.eu-west-2.compute.amazonaws.com -L 127.0.0.1:8443:192.168.49.2:8443
```

You should now find that `kubectl` and `k9s` work for the Minikube cluster if you run them on your Mac! This can include `kubectl port-forward` to access Kubernetes services individually.

## Access the full QHub website

However, the way Traefik works will not allow you to port forward to that since it will not see the right domain name and port.

We can trick it by setting up a hostname alias. Run `sudo vi /etc/hosts` on the Mac and add:

```bash
127.0.0.1 github-actions.qhub.dev
```

And then we add an extra port forward when we SSH into the AWS instance:

```bash
sudo ssh -i ~/.ssh/aws-quansight-mykey.pem ubuntu@ec2-35-177-109-173.eu-west-2.compute.amazonaws.com -L 127.0.0.1:8443:192.168.49.2:8443 -L github-actions.qhub.dev:443:192.168.49.100:443
```

This has to be run with sudo because we want to forward a low-numbered port (443) and this is not allowed without sudo.

Now you can access https://github-actions.qhub.dev/ in a browser and you should be able to use your QHub. You will have to bypass the self-signed cert warnings though - see [verify the local deployment](#verify-the-local-deployment) for instructions.