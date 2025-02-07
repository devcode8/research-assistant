from flask import Flask, request
import os
import sys
import json
from fetchai.crypto import Identity
from fetchai.registration import register_with_agentverse
from fetchai.communication import (
    send_message_to_agent, parse_message_from_agent
)
from dotenv import load_dotenv
from langchain_openai import ChatOpenAI
from langchain import  hub
from langchain_community.utilities import WikipediaAPIWrapper
from langchain.tools import Tool
from langchain_community.utilities import ArxivAPIWrapper
from langchain.agents import  (create_openai_tools_agent,AgentExecutor)

load_dotenv()

app = Flask(__name__)


AGENTVERSE_KEY = os.getenv("AGENTVERSE_KEY")
if AGENTVERSE_KEY == "":
    sys.exit("Environment variable AGENTVERSE_KEY not defined")
os.environ['OPENAI_API_KEY'] = os.getenv("OPENAI_API_KEY")

wiki=WikipediaAPIWrapper(top_k_results=1,doc_content_chars_max=200)
wiki_tool = Tool(
    name="Wikipedia",
    func=wiki.run,
    description="Search Wikipedia for information."
)

arxiv=ArxivAPIWrapper(top_k_results=1, doc_content_chars_max=200)
arxiv_tool = Tool(
    name="Arxiv",
    func=arxiv.run,
    description="Search Arxiv for academic papers."
)

# Register agent on Agentverse
@app.route('/register',methods=['GET'])
def registeration():
    ai_identity = Identity.from_seed("my rag",0)
    name = "Research Assistant Agent"
    readme = """
    <description>My AI assists with research by providing insights, summaries, and references from Wikipedia and Arxiv for your projects.</description>
    <use_cases>
        <use_case>My AI retrieves research papers and summaries from Arxiv and Wikipedia for your project needs.</use_case>
    </use_cases>
    <payload_requirements>
    <description>The requirements your AI has for requests</description>
        <payload>
            <requirement>
                <parameter>prompt</parameter>
                <description>It take prompt from user.</description>
            </requirement>
        </payload>
        </payload_requirements>

    """     
    ai_webhook = os.environ.get('RAG_AGENT_WEBHOOK', "http://127.0.0.1:8080/research")

    register_with_agentverse(
        ai_identity,
        ai_webhook,
        AGENTVERSE_KEY,
        name,
        readme,
    )
 
    return {"status": f"{name} got registered"}


@app.route('/research', methods=['POST'])
def getUrl():
    print("---------------------")
    print("Received webhook request")
    print("---------------------")
    
    data = request.json
    print(f"Request data: {json.dumps(data, indent=2)}")
    
    try:
        message = parse_message_from_agent(json.dumps(data))
    except ValueError as e:
        print(f"Error parsing message: {e}")
        return {"status": f"error: {e}"}
    
    sender = message.sender
    payload = message.payload
    
    print("---------------------")
    print(f"Sender: {sender}")
    print(f"Payload: {json.dumps(payload, indent=2)}")
    print("---------------------")

    prompt = payload.get("prompt", None)
    ai_identity = Identity.from_seed("my rag", 0)

    if sender == ai_identity.address:
        print("Self-message detected, ignoring")
        return {"status": "Agent message processed"}
    
    if prompt is None:
        print("Error: No prompt provided")
        payload = {
            "err": "You need to provide valid prompt.",
        }
    else:
        print(f"Processing prompt: {prompt}")
        tools = [wiki_tool, arxiv_tool]
        llm = ChatOpenAI(model="gpt-3.5-turbo-0125", temperature=0)
        prompt_template = hub.pull("hwchase17/openai-functions-agent")
        agent = create_openai_tools_agent(llm, tools, prompt_template)
        agent_executor = AgentExecutor(agent=agent, tools=tools, verbose=True)
        
        print("Executing agent...")
        result = agent_executor.invoke({"input": prompt})
        print(f"Agent result: {json.dumps(result['output'], indent=2)}")
        
        payload = {
            "Response": result['output']
        }

    print("---------------------")
    print(f"Sending response to {sender}")
    print(f"Response payload: {json.dumps(payload, indent=2)}")
    print("---------------------")
    
    send_message_to_agent(
        sender=ai_identity,
        target=sender,
        payload=payload,
        session=data["session"]
    )
    
    return {"status": "Agent message processed"}


if __name__ == "__main__":
    app.run(host='0.0.0.0', port=8080, debug=True)