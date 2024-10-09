import logging, os
from flask import Flask, request, jsonify
from pydantic import BaseModel, ValidationError
from kubernetes import client, config

# Configure logging
logging.basicConfig(level=logging.DEBUG, 
                    format='%(asctime)s %(levelname)s - %(message)s',
                    filename='agent.log', filemode='a')

app = Flask(__name__)


class QueryResponse(BaseModel):
    query: str
    answer: str

config_path = os.path.expanduser("~/.kube/config")



# Load kubeconfig from the default location (~/.kube/config) or provide the path
config.load_kube_config(config_file=config_path)
# Create a Kubernetes API client
v1 = client.CoreV1Api()
print("Listing nodes in the cluster:")
nodes = v1.list_node()
for node in nodes.items:
    print(f"Node name: {node.metadata.name}")


@app.route('/query', methods=['POST'])
def create_query():
    try:
        request_data = request.json
        query = request_data.get('query')

        logging.info(f"Received query: {query}")

        answer = get_agent_response(query)
        logging.info(f"Generated answer: {answer}")

        response = QueryResponse(query=query, answer=answer)
        return jsonify(response.dict())

    except ValidationError as e:
        return jsonify({"error": e.errors()}), 400


if __name__ == "__main__":
    app.run(host="0.0.0.0", port=8000)
