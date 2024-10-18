# import logging
# import os
# from flask import Flask, request, jsonify
# from kubernetes import config, client
# from pydantic import BaseModel, ValidationError
#
# # Configure logging
# logging.basicConfig(level=logging.DEBUG,
#                     format='%(asctime)s %(levelname)s - %(message)s',
#                     filename='agent.log', filemode='a')
#
# app = Flask(__name__)
#
#
# class QueryResponse(BaseModel):
#     query: str
#     answer: str
#
#
# def get_kubeconfig_path():
#     """
#     Determines the location of the kubeconfig file.
#     Checks if the kubeconfig file exists at the default path and logs its location.
#     """
#     kubeconfig_path = os.path.expanduser("~/.kube/config")
#     if os.path.exists(kubeconfig_path):
#         logging.info(f"Kubeconfig found at: {kubeconfig_path}")
#     else:
#         logging.warning(f"Kubeconfig file not found at: {kubeconfig_path}")
#     return kubeconfig_path
#
#
# def load_kube_config():
#     """Load kubeconfig using the dynamically determined path."""
#     config_path = get_kubeconfig_path()
#     config.load_kube_config(config_file=config_path)
#
#
# def log_cluster_details():
#     """Logs the namespaces, pods, ports, and nodes for the entire cluster."""
#     load_kube_config()
#     v1 = client.CoreV1Api()
#
#     # Log Namespaces
#     namespaces = v1.list_namespace()
#     logging.info(f"Namespaces: {[ns.metadata.name for ns in namespaces.items]}")
#
#     # Log Pods Information
#     all_pods = v1.list_pod_for_all_namespaces()
#     pod_info = [{"namespace": pod.metadata.namespace, "name": pod.metadata.name, "status": pod.status.phase} for pod in all_pods.items]
#     logging.info(f"Pods Information: {pod_info}")
#
#     # Log Nodes Information
#     nodes = v1.list_node()
#     node_info = [{"node_name": node.metadata.name, "capacity": node.status.capacity, "addresses": [addr.address for addr in node.status.addresses]} for node in nodes.items]
#     logging.info(f"Nodes Information: {node_info}")
#
#     # Log Service Ports Information
#     services = v1.list_service_for_all_namespaces()
#     service_ports = []
#     for service in services.items:
#         ports = [{"port": port.port, "target_port": port.target_port, "protocol": port.protocol} for port in service.spec.ports]
#         service_ports.append({"service_name": service.metadata.name, "namespace": service.metadata.namespace, "ports": ports})
#     logging.info(f"Service Ports Information: {service_ports}")
#
#
# def cluster_info():
#     """
#     Retrieves basic cluster information, such as Kubernetes version and the number of nodes.
#     """
#     load_kube_config()
#     v1 = client.CoreV1Api()
#     version_info = client.VersionApi().get_code()
#     nodes = v1.list_node()
#
#     cluster_info = {
#         "kubernetes_version": version_info.git_version,
#         "number_of_nodes": len(nodes.items),
#         "nodes": [node.metadata.name for node in nodes.items]
#     }
#
#     logging.info(f"Cluster Information: {cluster_info}")
#     return cluster_info
#
#
# def pod_info(namespace="default"):
#     """
#     Retrieves basic pod information for a given namespace.
#     """
#     load_kube_config()
#     v1 = client.CoreV1Api()
#     pods = v1.list_namespaced_pod(namespace=namespace)
#
#     pod_details = []
#     for pod in pods.items:
#         pod_info = {
#             "pod_name": pod.metadata.name,
#             "namespace": pod.metadata.namespace,
#             "status": pod.status.phase,
#             "node_name": pod.spec.node_name,
#             "containers": [container.name for container in pod.spec.containers]
#         }
#         pod_details.append(pod_info)
#
#     logging.info(f"Pod Information for namespace '{namespace}': {pod_details}")
#     return pod_details
#
#
# @app.route('/query', methods=['POST'])
# def create_query():
#     try:
#         # Extract the question from the request data
#         request_data = request.json
#         query = request_data.get('query')
#
#         # Log the question
#         logging.info(f"Received query: {query}")
#
#         log_cluster_details()
#
#         if "cluster info" in query.lower():
#             answer = cluster_info()
#         elif "pod info" in query.lower():
#             namespace = "default"
#             if "namespace" in query.lower():
#                 try:
#                     namespace = query.lower().split("namespace")[1].strip()
#                 except IndexError:
#                     namespace = "default"
#             answer = pod_info(namespace)
#         else:
#             answer = "Query not recognized. Please specify 'cluster info' or 'pod info'."
#
#         # Log the generated answer
#         logging.info(f"Generated answer: {answer}")
#
#         # Create the response model
#         response = QueryResponse(query=query, answer=str(answer))
#
#         return jsonify(response.dict())
#
#     except ValidationError as e:
#         return jsonify({"error": e.errors()}), 400
#
#
# if __name__ == "__main__":
#     app.run(host="0.0.0.0", port=8000)
import logging
import os
from flask import Flask, request, jsonify
from kubernetes import config, client
from pydantic import BaseModel, ValidationError

# Configure logging
logging.basicConfig(level=logging.DEBUG,
                    format='%(asctime)s %(levelname)s - %(message)s',
                    filename='agent.log', filemode='a')

app = Flask(__name__)


class QueryResponse(BaseModel):
    query: str
    answer: str


def get_kubeconfig_path():
    """
    Determines the location of the kubeconfig file.
    Checks if the kubeconfig file exists at the default path and logs its location.
    """
    kubeconfig_path = os.path.expanduser("~/.kube/config")
    if os.path.exists(kubeconfig_path):
        logging.info(f"Kubeconfig found at: {kubeconfig_path}")
    else:
        logging.warning(f"Kubeconfig file not found at: {kubeconfig_path}")
    return kubeconfig_path


def load_kube_config():
    """Load kubeconfig using the dynamically determined path."""
    config_path = get_kubeconfig_path()
    config.load_kube_config(config_file=config_path)


def log_cluster_details():
    """Logs the namespaces, pods, ports, and nodes for the entire cluster."""
    load_kube_config()
    v1 = client.CoreV1Api()

    # Log Namespaces
    namespaces = v1.list_namespace()
    logging.info(f"Namespaces: {[ns.metadata.name for ns in namespaces.items]}")

    # Log Pods Information
    all_pods = v1.list_pod_for_all_namespaces()
    pod_info = [{"namespace": pod.metadata.namespace, "name": pod.metadata.name, "status": pod.status.phase} for pod in all_pods.items]
    logging.info(f"Pods Information: {pod_info}")

    # Log Nodes Information
    nodes = v1.list_node()
    node_info = [{"node_name": node.metadata.name, "capacity": node.status.capacity, "addresses": [addr.address for addr in node.status.addresses]} for node in nodes.items]
    logging.info(f"Nodes Information: {node_info}")

    # Log Service Ports Information
    services = v1.list_service_for_all_namespaces()
    service_ports = []
    for service in services.items:
        ports = [{"port": port.port, "target_port": port.target_port, "protocol": port.protocol} for port in service.spec.ports]
        service_ports.append({"service_name": service.metadata.name, "namespace": service.metadata.namespace, "ports": ports})
    logging.info(f"Service Ports Information: {service_ports}")


def cluster_info():
    """
    Retrieves basic cluster information, such as Kubernetes version and the number of nodes.
    """
    load_kube_config()
    v1 = client.CoreV1Api()
    version_info = client.VersionApi().get_code()
    nodes = v1.list_node()

    cluster_info = {
        "kubernetes_version": version_info.git_version,
        "number_of_nodes": len(nodes.items),
        "nodes": [node.metadata.name for node in nodes.items]
    }

    logging.info(f"Cluster Information: {cluster_info}")
    return cluster_info


def pod_info(namespace="default"):
    """
    Retrieves basic pod information for a given namespace.
    """
    load_kube_config()
    v1 = client.CoreV1Api()
    pods = v1.list_namespaced_pod(namespace=namespace)

    pod_details = []
    for pod in pods.items:
        pod_info = {
            "pod_name": pod.metadata.name,
            "namespace": pod.metadata.namespace,
            "status": pod.status.phase,
            "node_name": pod.spec.node_name,
            "containers": [container.name for container in pod.spec.containers]
        }
        pod_details.append(pod_info)

    logging.info(f"Pod Information for namespace '{namespace}': {pod_details}")
    return pod_details


def generate_response(combined_info, query):
    """
    Generates a concise response for a given query using combined Kubernetes cluster information.
    """
    # Extract necessary details from the combined cluster information
    cluster_info = combined_info.get("Cluster Information", {})
    node_info = combined_info.get("Node Information", {})
    namespace_info = combined_info.get("Namespace Information", {})
    workload_info = combined_info.get("Workload Information", {})
    service_info = combined_info.get("Service Information", {})
    pod_info = combined_info.get("Pod Information", {})
    container_info = combined_info.get("Container Information", {})

    node_info_str = ", ".join([node for node in node_info.keys()])
    namespace_info_str = ", ".join([namespace for namespace in namespace_info.keys()])
    workload_info_str = ", ".join([f"{workload_type}: {len(items)} items" for workload_type, items in workload_info.items()])
    service_info_str = ", ".join([f"{namespace}: {', '.join([svc['service_name'] for svc in services])}" for namespace, services in service_info.items()])
    pod_info_str = ", ".join([f"{namespace}: {', '.join([pod['pod_name'] for pod in pods])}" for namespace, pods in pod_info.items()])
    container_info_str = ", ".join([f"{pod}: {', '.join([container['container_name'] for container in containers])}" for pod, containers in container_info.items()])

    response_template = f"""
    You are a Kubernetes assistant. The user asked: '{query}'. You must answer the query based on the information without any explanations.
    Here is the cluster information:
    - Kubernetes Version: {cluster_info.get('kubernetes_version')}
    - Number of Nodes: {cluster_info.get('number_of_nodes')}
    - Nodes: {node_info_str}
    - Namespaces: {namespace_info_str}
    - Workloads: {workload_info_str}
    - Services: {service_info_str}
    - Pods: {pod_info_str}
    - Containers: {container_info_str}

    Answer the query in just one word. Provide only the necessary information without any technical identifiers, suffixes, or justifications. Return only the answer.
    """

    return response_template.strip()


@app.route('/query', methods=['POST'])
def create_query():
    try:
        # Extract the question from the request data
        request_data = request.json
        query = request_data.get('query')

        # Log the question
        logging.info(f"Received query: {query}")

        # Retrieve detailed cluster information
        combined_info = {
            "Cluster Information": cluster_info(),
            "Pod Information": pod_info()
            # Add more information as needed
        }

        # Generate a concise response based on the combined information and query
        answer = generate_response(combined_info, query)

        # Log the generated answer
        logging.info(f"Generated answer: {answer}")

        # Create the response model
        response = QueryResponse(query=query, answer=answer)

        return jsonify(response.dict())

    except ValidationError as e:
        return jsonify({"error": e.errors()}), 400


if __name__ == "__main__":
    app.run(host="0.0.0.0", port=8000)
