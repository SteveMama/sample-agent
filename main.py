import logging
import os
from flask import Flask, request, jsonify
from kubernetes import config, client
from pydantic import BaseModel, ValidationError
from langchain import OpenAI


# Configure logging
logging.basicConfig(level=logging.DEBUG,
                    format='%(asctime)s %(levelname)s - %(message)s',
                    filename='agent.log', filemode='a')

app = Flask(__name__)

# Get the OpenAI API key from the environment variables
openai_api_key = os.environ.get('OPENAI_API_KEY')



def generate_prompt(combined_info, query):
    """
    Generates a concise prompt for querying Kubernetes cluster information.
    Returns a concise answer without identifiers or justifications.
    """
    # Extract necessary details from the combined cluster information
    cluster_info = combined_info.get("Cluster Information", {})
    node_info = combined_info.get("Node Information", {})
    namespace_info = combined_info.get("Namespace Information", {})
    workload_info = combined_info.get("Workload Information", {})
    service_info = combined_info.get("Service Information", {})
    pod_info = combined_info.get("Pod Information", {})
    container_info = combined_info.get("Container Information", {})

    node_info_str = "\n".join([f"- {node}" for node in node_info.keys()])
    namespace_info_str = "\n".join([f"- {namespace}" for namespace in namespace_info.keys()])
    workload_info_str = "\n".join(
        [f"- {workload_type}: {len(items)} items" for workload_type, items in workload_info.items()])
    service_info_str = "\n".join(
        [f"- {namespace}: {', '.join([svc['service_name'] for svc in services])}" for namespace, services in
         service_info.items()])
    pod_info_str = "\n".join(
        [f"- {namespace}: {', '.join([pod['pod_name'] for pod in pods])}" for namespace, pods in pod_info.items()])
    container_info_str = "\n".join(
        [f"- {pod}: {', '.join([container['container_name'] for container in containers])}" for pod, containers in
         container_info.items()])

    prompt_template = f"""
    You are a Kubernetes assistant. The user asked: '{query}'. You must answer the query based on the information without any explainations.
    These are fictional examples you can refer to understand the format of answer. Notice Answer has just the value and no explainations.
    Q: "Which pod is spawned by my-deployment?" A: "my-pod"
    Q: "What is the status of the pod named 'example-pod'?" A: "Running"
    Q: "How many nodes are there in the cluster?" A: "2"
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

    Query:
    Answer: only the answer without any explainations or justifications. just the answer value. 
    """

    return prompt_template


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


def get_agent_response(query):
    """Uses LangChain's OpenAI model to generate a response based on the prompt."""
    try:
        # Aggregate cluster information and generate a prompt
        combined_info = aggregate_info()
        formatted_prompt = generate_prompt(combined_info, query)
        logging.info(f"Formatted Prompt: {formatted_prompt}")

        # Create an OpenAI object using LangChain
        openai_llm = OpenAI(temperature=0.3, openai_api_key=openai_api_key)
        llm_response = openai_llm(formatted_prompt)

        logging.info(f"OpenAI LLM Response: {llm_response}")
        return llm_response.strip()
    except Exception as e:
        logging.error(f"Error in get_agent_response: {str(e)}")
        return "Error generating response from OpenAI."


def aggregate_info():
    """Aggregate various Kubernetes information into a single structure."""
    try:
        load_kube_config()
        # Example of aggregated information, modify with real data as needed
        cluster_info = get_cluster_info()
        node_info = get_node_info()
        namespace_info = get_namespace_info()

        combined_info = {
            "Cluster Information": cluster_info,
            "Node Information": node_info,
            "Namespace Information": namespace_info
        }
        logging.info(f"Aggregated Info: {combined_info}")
        return combined_info
    except Exception as e:
        logging.error(f"Error in aggregate_info: {str(e)}")
        return {"error": "Failed to aggregate cluster information"}


@app.route('/query', methods=['POST'])
def create_query():
    try:
        # Extract the question from the request data
        request_data = request.json
        query = request_data.get('query')

        # Log the question
        logging.info(f"Received query: {query}")

        # Generate the prompt and use OpenAI to get a response
        prompt = generate_prompt(query)
        openai_response = get_agent_response(query)

        # Log the generated answer
        logging.info(f"Generated answer: {openai_response}")

        # Create the response model
        response = QueryResponse(query=query, prompt=prompt, answer=openai_response)

        return jsonify(response.dict())

    except ValidationError as e:
        logging.error(f"Validation error: {e}")
        return jsonify({"error": e.errors()}), 400
    except Exception as e:
        logging.error(f"Unexpected error: {str(e)}")
        return jsonify({"error": "An unexpected error occurred. Please check logs for details."}), 500


if __name__ == "__main__":
    app.run(host="0.0.0.0", port=8000)
