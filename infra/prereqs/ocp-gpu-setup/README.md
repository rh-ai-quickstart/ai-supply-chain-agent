# OCP GPU Setup

Complete setup guide for enabling NVIDIA GPU support in OpenShift Container Platform (OCP) clusters running on AWS.

## Overview

This setup deploys a complete GPU-enabled OpenShift environment with:
- **GPU-enabled worker nodes** with NVIDIA L40S GPUs
- **Node Feature Discovery (NFD)** for hardware detection
- **NVIDIA GPU Operator** for automated GPU resource management
- **Custom configurations** for production GPU workloads


## Step 1: Configure GPU Machine Sets

The machine set script creates AWS EC2 instances with GPU support and configures them as OpenShift worker nodes.

```bash
./machine-set/gpu-machineset.sh
```

**Configuration options:**
1. Select "12) L40S Single GPU" - Creates nodes with NVIDIA L40S GPUs
2. Choose "p" for private - Internal GPU access (vs "s" for shared/external)
3. Enter AWS region, probably "us-east-2" - AWS region for deployment
4. Enter Availability zone e.g. "1" - AZ within the region (1, 2, or 3)
5. Answer "n" for spot instances - Use on-demand instances for stability

**What this does:**
- Creates GPU-enabled EC2 instances (g5.xlarge for L40S)
- Applies `nvidia.com/gpu` taints to GPU nodes
- Adds appropriate accelerator labels for workload scheduling
- Configures networking and security groups

**Note:** Check if you have the default machineset available. If not, run the command twice.

**Scaling configuration:**
- Set the GPU MachineSet to **2 instances** (for GPU workloads)
- Configure the default MachineSet to **6 instances** (for non-GPU workloads)

Wait for nodes to be provisioned (typically 5-10 minutes).

## Step 2: Deploy Node Feature Discovery (NFD)

NFD detects hardware features on cluster nodes and labels them for workload scheduling.

```bash
oc apply -f ./nfd
```

**What this deploys:**
- **Namespace**: `openshift-nfd` with cluster monitoring
- **Operator**: Red Hat NFD operator (v4.18.0)
- **Configuration**: Scans nodes every 60 seconds for PCI devices including GPUs

## Step 3: Deploy NVIDIA GPU Operator

The GPU Operator automates the management of NVIDIA GPU software stack.

```bash
oc apply -f ./gpu-operator
```

**What this deploys:**
- **Namespace**: `nvidia-gpu-operator`
- **Operator**: NVIDIA GPU Operator (v25.3.0) from certified operators
- **Components**: GPU drivers, container runtime, device plugins, monitoring

Wait for both NFD and GPU Operator to be fully installed before proceeding.

## Step 4: Deploy Custom Resources (CRs)

The CRs configure how NFD and the GPU Operator should operate in your cluster.

```bash
oc apply -f ./crs
```

**What this configures:**

### Node Feature Discovery Configuration
- **Hardware Detection**: Identifies NVIDIA GPUs and other PCI devices
- **Node Labeling**: Adds vendor and device information as node labels
- **Scheduling**: Enables GPU-aware pod scheduling

### GPU Cluster Policy
- **Driver Management**: Automatic NVIDIA driver installation and updates
- **Monitoring**: DCGM (Data Center GPU Manager) for GPU metrics
- **Device Plugin**: Exposes GPU resources to Kubernetes scheduler
- **MIG Support**: Multi-Instance GPU configuration capability
- **Validation**: GPU functionality testing and validation

### Driver Configuration
- **Container Image**: Specific NVIDIA driver version with SHA256 verification
- **Registry**: Uses NVIDIA's official container registry
- **Integration**: OpenShift driver toolkit compatibility

## Verification

After deployment, verify your GPU setup:

```bash
# Check GPU nodes
oc get nodes -l nvidia.com/gpu.present=true

# Check GPU operator pods
oc get pods -n nvidia-gpu-operator

# Check NFD labels on GPU nodes
oc describe node <gpu-node-name> | grep nvidia

# Check available GPU resources
oc describe node <gpu-node-name> | grep nvidia.com/gpu
```

## Supported GPU Types

The setup script supports 14 different GPU configurations including:
- Tesla T4, A10G, A100 (various configurations)
- H100 (80GB and 94GB variants)
- L40, L40S (single and multi-GPU)
- V100 and other enterprise GPUs

## Architecture

```
┌─────────────────┐    ┌──────────────────┐    ┌─────────────────┐
│   NFD Operator  │    │  GPU Operator    │    │ Custom Resources│
│                 │    │                  │    │                 │
│ • Node scanning │    │ • Driver mgmt    │    │ • NFD config    │
│ • Hardware      │    │ • Device plugin  │    │ • Cluster policy│
│   detection     │    │ • Monitoring     │    │ • Driver spec   │
│ • Node labeling │    │ • Validation     │    │                 │
└─────────────────┘    └──────────────────┘    └─────────────────┘
         │                       │                       │
         └───────────────────────┼───────────────────────┘
                                 │
                    ┌─────────────────────┐
                    │   GPU Worker Nodes  │
                    │                     │
                    │ • NVIDIA L40S GPUs  │
                    │ • Specialized taints│
                    │ • GPU-ready runtime │
                    │ • Monitoring agents │
                    └─────────────────────┘
```
