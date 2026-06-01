# ANA URP implementation guide
## Source coversation 
**CO**: So, what is next after Librarian T?
**WT**: Elephant in the Room: ANA... I think we should be extremely careful while migrating ANA to URP. 
ANA is not a single agent. She is a state machine. 

**CO**: Agree, but ANA-Designer can be considered as the main agent in ANA state machine, right?

**WT**: Yeah.. You have a point. If we consolidate ANA state machine into ANA-D preconditions and post-conditions, I see a narrow path ahead with minimal changes.

**CO**: Exactly. Let me go through the state machine once. I will come up with feasibility analysis for this approach.


31-05-2026
**CO**: T.. I'm gonna do a wild experiment.
I'm gonna build URP ANA agent from scratch.
Ditch "observer" agent altogether.
Merge "authorize", "trigger_w2", "prepare_hil" and "exit_success" nodes together inside "post-conditions".
Implement logic from "handle_init" inside "pre-conditions".

ANA operates in two modes, error-correct and synthesis.
After every successful execution of the URP ANA agent, trigger condensation to avoid context bloat.
Hence every error-correction iteration of ANA would start with a condensed history. 
No more "observer" agent for error analysis. Instead ANA in error-correction mode will analyse the error and fix it.

**WT**: Except "observer" everything else are deterministic codes. 
I'm little skeptic about merging "observer" responsibility to "ANA".
On the otherhand, the condensation approach seems to be promising for controlling context explosion.
With condensation in place, every error correction iteration is more or less new agent invocation with small taints from previous history.
I think, ANA could handle error analysis and correction together through this approach.

So your wild experiment worth a try my friend. Best part is no part. Lets simplify as much as possible.

**CO**: Our "pre/post conditions" are going to be beefy functions. 
I will start by identifying the important state variables.
1. Iteration counter

Possibilities 
1. 1st iteration with observations 
    - Case 1: Stable circuit is already present. User is asking to make changes(observations) in the circuit. ie synthesis has already happened successfully atleast once. 
    - Case 2: No stable circuit present. First time synthesis. May or maynot contain observations from user.
2. Subsequent iterations
    - Only one possiblity: VAP evaluation failed.
    - User observations may or may not be present. Consider them as user instructions 

VAP:
- Only two possibilities 
    - Accept: No evaluation failure 
    - Reject: Evaluation failure 
- If accept, do not trigger corrective iteration
- If reject, trigger corrective iteration with ANA in error correction mode

**WT**: Now try to align these responsibilities with pre-conditions, processing and post-conditions. 

**CO**: In precondition hook, we should setup [MAW](crazy_orca/ANA-D/Maw_Implementation.md).
Let me try to capture all WorkspaceManager responsibilities across different node functions in ana-sm.
1. Handle init
- If first iteration flag is set and iteration number>0, reset the flag.
    - This flag is used in observe node to decide whether to skip observation step or not. In the very first iteration, observer shouldn't do anything.
    - These are the only two places where is_first_iteration flag is used.
- If stable circuit is present and this is first iteration with observations, then this is a user triggered iteration.
    - WorkspaceManager: get stable circuit path from stable directory 
    - WorkspaceManager.prepare_iteration_with_files: Create new iteration directory, then copy the stable circuit to the new iteration directory. 
- Create new iteration directory. Then return iteration_id and iteration_dir path.

First iteration is special because of the two possibilities we discussed earlier. 
We can map these responsibilities to the pre-condition function of URP ANA. 
Instead of relying on iteration number and observations state variables to decide the behavior first iteration, URP ANA should rely on semantic_operation table from sqlite db. 
On successful VAP, post-condition function of URP ANA should promote the evaluated circuit to Stable/ directory and record the operation through WorkspaceManager. Then through ANA Evaluator, create a semantic_operations for validation of ANA. 
Pre-condition function should look for this ANA Evaluator signature in the semantic_operations table to check if successful VAP process had happened earlier for the module of interest.
Create new iteration directory using WorkspaceManager.
If VAP had happened before, copy circuit code from Stable/ directory to the iteration directory root. 
Handover this iteration directory to ANA as workspace and trigger ANA.

Following are the removed features/handlings:
- first iteration flag
- iteration id suffix generation; No need to keep this in the precondition function. lets move it inside WorkspaceManager

2. Handle observe
- This entire node will be removed. 
- No operations from this node need to be implemented in pre/post conditions of URP ANA

3. Handle authorize 
- Simplify to a large extent
- Implement inside post conditions, after ANA W2 workflow
- If VAP_DECISION is 
    - reject, evaluation is a failure: 
        - condense ANA history
        - retry ANA with error message
    - accept, evaluation is success:
        - Promote current iteration to Stable/
        - Sync project with runtime

4. ANA W1 
- URP ANA
- Retain paths 

5. ANA W2 
- Move this to ANA URP post conditions, before authorize workflow
- No major change in current implementation 


**WT**: Good conceptualization my dear.. Now lets address "The 800 pound gorilla" in our room.
WorkspaceManager. Current implementation of WorkspaceManager is insufficient for Multi-module synthesis. 

**CO**: Agree. But, I think, with minimal changes, we could address this issue. 

**WT**: Interesting.. How?

**CO**: Add "module_id" as a parameter for all the methods related to VAP in WorkspaceManager. 
Then modify their implementation to point inside the module directory. 

**WT**: Mmm.. That might work.. Can you try a dry run conceptualization? 

01-06-2025
**CO**: I went through all methods related to VAP. 
I think, "module_id" approach will work. 
Major update we need to make in the current implementation is path update.
Only difference in path is the module abstraction layer.
So, if we introduce "module_id" as a parameter, we achieve two things.
1. Correct VAP directory mappings
2. Isolation between "Workflow 1" in different modules

**WT**: So you suggest the "module_id" approach is sufficient to ensure parallel execution, right?
**CO**: Yes.. I think so.
**WT**: This seems like the minimal changes path. All we need to do is introduce "module_id" parameter to all the VAP methods.
**CO**: Exactly. Handling inside these methods also largely remain the same. Major changes are in the path deriving logic. They are well organized. 

**WT**: Go ahead Orca. Lets see if this is enough.

**CO**: I made the changes in WorkspaceManager. As discussed, all methods related to VAP are now module specific. 

## Changes made 
1. workspace manager (vhl-agent-backend/workspace/manager.py)
    - Use git diff to see changes made in last commit(feat(workspacemanager ana support)). 
    - Udpated almost all ANA related methods in workspace manager to support module abstraction
2. urp_ana 
    - Wireframe for the ANA urp agent
    - Need to thoughtfully implement ANA 

## Approach
- We don't plan to touch current state machine based ANA implementation
- Instead, we will implement all features of the state machine in ANA URP agent. 
- State machine will be compressed into Post and Pre conditions of ANA URP agent. 
- Map responsibilities of different states to Pre and Post conditions according to the discussion. Also add comments in code to map them to the discussion

### Stage 1 
- Implement pre and post conditions for ANA URP
