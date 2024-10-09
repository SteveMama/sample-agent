import logging
import os
from flask import Flask, request, jsonify
from kubernetes import config, client
from pydantic import BaseModel, ValidationError
from langchain import OpenAI, LLMChain, PromptTemplate

# Configure logging
logging.basicConfig(level=logging.DEBUG,
                    format='%(asctime)s %(levelname)s - %(message)s',
                    filename='agent.log', filemode='a')

app = Flask(__name__)

# Fetch OpenAI API key from environment variables
openai_key_api = os.environ.get('OPENAI_API_KEY')

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


def create_prompt(query, cluster_data):
    """Creates a natural language prompt based on the query and cluster details."""
    prompt_template = f"""
    You are a Kubernetes assistant. The user asked: '{query}'. Here is the cluster information:
    - Kubernetes Version: {cluster_data['kubernetes_version']}
    - Number of Nodes: {cluster_data['number_of_nodes']}
    - Nodes: {', '.join(cluster_data['nodes'])}
    
    Please provide a concise and accurate response.
    """
    return prompt_template


@app.route('/query', methods=['POST'])
def create_query():
    try:
        # Extract the question from the request data
        request_data = request.json
        query = request_data.get('query')

        # Log the question
        logging.info(f"Received query: {query}")

        # Log cluster details irrespective of the query
        log_cluster_details()

        # Get basic cluster information for context
        cluster_data = cluster_info()

        # Create a natural language prompt based on the query and cluster details
        prompt = create_prompt(query, cluster_data)

        # Initialize the LangChain OpenAI agent
        openai_llm = OpenAI(temperature=0.3, openai_api_key=openai_key_api)
        
        # Use LangChain to generate a response
        llm_response = openai_llm(prompt)

        # Log the generated answer
        logging.info(f"Generated answer: {llm_response}")

        # Create the response model
        response = QueryResponse(query=query, answer=llm_response)

        return jsonify(response.dict())

    except ValidationError as e:
        return jsonify({"error": e.errors()}), 400
    except Exception as ex:
        logging.error(f"An unexpected error occurred: {ex}")
        return jsonify({"error": "An internal error occurred"}), 500


if __name__ == "__main__":
    app.run(host="0.0.0.0", port=8000)
