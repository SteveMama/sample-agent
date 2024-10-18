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
    prompt: str
    answer: str


def get_kubeconfig_path():
    """Determines the location of the kubeconfig file."""
    try:
        kubeconfig_path = os.path.expanduser("~/.kube/config")
        if os.path.exists(kubeconfig_path):
            logging.info(f"Kubeconfig found at: {kubeconfig_path}")
        else:
            logging.warning(f"Kubeconfig file not found at: {kubeconfig_path}")
        return kubeconfig_path
    except Exception as e:
        logging.error(f"Error in get_kubeconfig_path: {str(e)}")
        return None


def load_kube_config():
    """Load kubeconfig using the dynamically determined path."""
    try:
        config_path = get_kubeconfig_path()
        if config_path:
            config.load_kube_config(config_file=config_path)
        else:
            logging.error("Kubeconfig path is invalid. Cannot load config.")
    except Exception as e:
        logging.error(f"Error loading kube config: {str(e)}")


def generate_prompt(query):
    """Generates a prompt based on the query."""
    try:
        prompt = f"You asked about: '{query}'. Provide relevant Kubernetes information."
        logging.info(f"Generated Prompt: {prompt}")
        return prompt
    except Exception as e:
        logging.error(f"Error in generate_prompt: {str(e)}")
        return "Error generating prompt."


def log_cluster_details():
    """Logs the namespaces, pods, ports, and nodes for the entire cluster."""
    try:
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

    except Exception as e:
        logging.error(f"Error in log_cluster_details: {str(e)}")


def cluster_info():
    """Retrieves basic cluster information, such as Kubernetes version and the number of nodes."""
    try:
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
    except Exception as e:
        logging.error(f"Error in cluster_info: {str(e)}")
        return {"error": "Failed to retrieve cluster information"}


def pod_info(namespace="default"):
    """Retrieves basic pod information for a given namespace."""
    try:
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
    except Exception as e:
        logging.error(f"Error in pod_info: {str(e)}")
        return {"error": f"Failed to retrieve pod information for namespace '{namespace}'"}


@app.route('/query', methods=['POST'])
def create_query():
    try:
        # Extract the question from the request data
        request_data = request.json
        query = request_data.get('query')

        # Log the question
        logging.info(f"Received query: {query}")

        # Generate and log the prompt
        prompt = generate_prompt(query)

        log_cluster_details()

        if "cluster info" in query.lower():
            answer = cluster_info()
        elif "pod info" in query.lower():
            namespace = "default"
            if "namespace" in query.lower():
                try:
                    namespace = query.lower().split("namespace")[1].strip()
                except IndexError:
                    namespace = "default"
            answer = pod_info(namespace)
        else:
            answer = "Query not recognized. Please specify 'cluster info' or 'pod info'."

        # Log the generated answer
        logging.info(f"Generated answer: {answer}")

        # Create the response model
        response = QueryResponse(query=query, prompt=prompt, answer=str(answer))

        return jsonify(response.dict())

    except ValidationError as e:
        logging.error(f"Validation error: {e}")
        return jsonify({"error": e.errors()}), 400
    except Exception as e:
        logging.error(f"Unexpected error: {str(e)}")
        return jsonify({"error": "An unexpected error occurred. Please check logs for details."}), 500


if __name__ == "__main__":
    app.run(host="0.0.0.0", port=8000)
