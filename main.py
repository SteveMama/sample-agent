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


# Function to check and log kubeconfig path
def get_kubeconfig_path():
    # Default kubeconfig path
    kubeconfig_path = os.path.expanduser("~/.kube/config")

    # Check if the file exists
    if os.path.exists(kubeconfig_path):
        logging.info(f"Kubeconfig found at: {kubeconfig_path}")
    else:
        logging.warning(f"Kubeconfig file not found at: {kubeconfig_path}")

    return kubeconfig_path


@app.route('/query', methods=['POST'])
def create_query():
    try:
        # Extract the question from the request data
        request_data = request.json
        query = request_data.get('query')
        
        # Log the question
        logging.info(f"Received query: {query}")

        # Check kubeconfig path
        kubeconfig_path = get_kubeconfig_path()

        # Load kubeconfig if present
        if os.path.exists(kubeconfig_path):
            config.load_kube_config(config_file=kubeconfig_path)
            v1 = client.CoreV1Api()

            # Sample Kubernetes query: list namespaces
            namespaces = v1.list_namespace()
            logging.info("Successfully loaded kubeconfig and listed namespaces.")
            logging.info(f"Namespaces: {[ns.metadata.name for ns in namespaces.items]}")
        else:
            logging.warning(f"Kubeconfig file not found. Unable to connect to the cluster.")

        # For simplicity, we'll just echo the question back in the answer
        answer = "This is a sample answer."

        # Log the answer
        logging.info(f"Generated answer: {answer}")

        # Create the response model
        response = QueryResponse(query=query, answer=answer)

        return jsonify(response.dict())

    except ValidationError as e:
        return jsonify({"error": e.errors()}), 400


if __name__ == "__main__":
    app.run(host="0.0.0.0", port=8000)
