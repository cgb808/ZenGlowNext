import os

AGENT_MODE = os.getenv("AGENT_MODE", "dev")

if AGENT_MODE == "prod":
    from agent_prod import run_prod_agent as run_agent
else:
    from agent_dev import run_dev_agent as run_agent

if __name__ == "__main__":
    run_agent()
