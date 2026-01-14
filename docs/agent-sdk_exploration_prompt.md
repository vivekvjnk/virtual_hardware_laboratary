We're designing ANA-D agent. ANA-D is a designer of analog circuits. 
Here are her identified responsibilities :
1. Being transparent in first iteration of ANA circuit construction.
    - ANA-D should simply delegate to ANA-W1. Trigger ANA-W1 with `circuit generation` prompt
    - No new information added, no updates to the core artifacts
    - Just orchestration
2. After 1st run of ANA-W1, check the generated circuit artifacts for accuracy.
    - Based on the findings create a document suggesting updates in circuit 
    - Prompt user/human for the inputs. Inlcude the findings in the prompt to human.
    - Based on human feedback and the findings, create the `circuit correction` prompt for ANA-W1
    - Trigger ANA-W1 with this correction prompt
3. Repeat above two iterations until:
    - Human accept the design; If human input in step 2 is to proceed, no further correction is required

Now we need to implement this using openhands-software-agent-sdk. 
Under agent-sdk/examples/, we have many examples explaining various features available in the SDK. Based on the identified responsibilities, we need to identify the minimum set of features required to implement ANA-D agent. I can immediately see the following features required:
1. Ability to pause and resume the agent execution
2. Ability to prompt human for inputs
3. Ability for the agent to control the execution flow based on human inputs
4. Ability to delegate to another agent

Now please explore the agent-sdk/examples/ and prepare a guide for implementing ANA-D agent. agent-sdk folder contain entire SDK codebase. You can explore the whole codebase if necessary. 