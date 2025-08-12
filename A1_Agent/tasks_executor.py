from agent import A1Agent
from env_api.api import evaluate_slay, evaluate_craft, move
from env_api.api_calls_ext import create_character_2


def missing_items_names(missing_items_list_raw: dict) -> list:
    """
    Convert raw missing items dictionary to formatted item names list.
    
    This function takes a dictionary of missing items and converts the item codes
    to properly formatted item names by replacing underscores with spaces and
    applying title case formatting.
    
    Args:
        missing_items_list_raw: Dictionary containing missing item codes as values
        
    Returns:
        List of formatted item names with quotes around each name
    """
    missing_items_list = []
    for item in list(missing_items_list_raw.values()):
        item_name = item.replace("_", " ")
        item_name = item_name.title()
        missing_items_list.append(f'"{item_name}"')
    return missing_items_list

def autotask_exec(task_json: dict, model: str, env_eval: bool) -> tuple[list,tuple[bool,bool],str]:
    """
    Execute a single automated task using the A1Agent.
    
    This function creates a character, initializes an agent, and attempts to
    complete a task (crafting or fighting) with retry logic. It handles both
    environment evaluation and action execution modes.
    
    Args:
        task_json: Dictionary containing task information with keys:
                   - character: Character configuration with name and prompt
                   - item: Item to craft (for crafting tasks)
                   - monster_name: Monster to fight (for fighting tasks)
                   - missing_items: Optional dictionary of missing items
        model: LLM model name to use for the agent
        env_eval: Whether to evaluate task completion in the environment
        
    Returns:
        Tuple containing:
            - List of action chains executed
            - Tuple of (agent_success, environment_success) booleans
            - Task target name or error message
    """
    character_data = task_json['character']
    character_name = character_data['name']
    task_type = ''
    task_target = ''
    quantity = '1'
    if 'item' in task_json:
        task_target = task_json['item']
        task_type = 'Craft'
    elif 'monster_name' in task_json:
        task_target = task_json['monster_name']
        task_type = 'Fight'
    else:
        return [], (False,False), 'Invalid task target'
    create_character_2(character_name,character_data['prompt'])

    agent = A1Agent(character_name=character_name, model = model, load_from_json=True)
    task = {
        'type': task_type,
        'target': task_target,
        'quantity': quantity,
        'previous_plan': '',
        'critique': ''
    }
    if 'missing_items' in task_json:
        missing_items_list = missing_items_names(task_json['missing_items'])
    else:
        missing_items_list = ['No missing items']
    agent.set_missing_items(missing_items_list)
    for i in range(1000): # Fill logs to avoid false-positive environment validation
        move(character_name, 0, 0)
    if env_eval is False:
        agent.execute_actions_chains = False
    num_attempts = 5
    current_attempts = 0
    completed = False
    checks = (False, False)
    action_chain = []
    while not completed and current_attempts < num_attempts:
        try:
            action_chain, checks = agent.run(task, eval_on_env=env_eval)
            completed = True
        except Exception as e:
            print(f'During agent work encountered unexpected error: \n {e}')
            current_attempts += 1
    if not completed:
        return [], (False,False), task_target
    try:
        if env_eval is False:
            for chain in action_chain:
                for action in chain['subtasks']:
                    agent.action_agent.execute_action(action, force_execution=True)
            env_check = False
            if task_type == 'Fight':
                env_check = evaluate_slay(character_name, task_target, 20)
            if task_type == 'Craft':
                env_check = evaluate_craft(character_name, task_target, 20)
            checks = (True, env_check)

    except Exception as e: return [], (False, False), task_target

    return action_chain, checks, task_target

def autotask_run_by_groups(task_json: dict, prompts_json: dict, model: str, experiment_groups: list,
                           ignore_tasks_indexes: list=None, env_eval:bool = True, monsters_tasks: bool = True,
                           crafting_tasks: bool = True) -> dict:
    """
    Execute multiple automated tasks organized by groups.
    
    This function processes a collection of tasks organized by groups (typically
    difficulty levels), applying prompts and executing tasks with the specified
    configuration. It supports filtering by task type and ignoring specific tasks.
    
    Args:
        task_json: Dictionary containing tasks organized by groups
        prompts_json: Dictionary containing prompts organized by groups
        model: LLM model name to use for agents
        experiment_groups: List of group names to process
        ignore_tasks_indexes: Optional list of task indexes to skip
        env_eval: Whether to evaluate task completion in the environment
        monsters_tasks: Whether to include monster fighting tasks
        crafting_tasks: Whether to include item crafting tasks
        
    Returns:
        Dictionary containing results for each executed task with keys:
            - actions: List of action chains executed
            - agent_check: Boolean indicating agent success
            - env_check: Boolean indicating environment validation success
            - group: Group name
            - task_num: Task number within group
            - task_target: Target of the task
            - task_difficulty: Difficulty level
            - task_type: Type of task ('monster' or 'item')
    """
    if ignore_tasks_indexes is None:
        ignore_tasks_indexes = []
    tasks_run_data = {}
    for group in task_json:
        for task_num, task in enumerate(task_json[group]):
            if group not in experiment_groups:
                continue
            else:
                task_index = f'{group}_{task_num}'
                task_target = ''
                if not monsters_tasks and 'monster' in task:
                    continue
                if not crafting_tasks and 'item' in task:
                    continue
                if task_index in ignore_tasks_indexes:
                    continue

                task_type = ''
                if 'monster_name' in task:
                    task_target = task['monster_name']
                    task_type = 'monster'
                if 'item' in task:
                    task_target = task['item']
                    task_type = 'item'

                task_prompt = prompts_json[group][task_num]
                task['character']['prompt'] = task_prompt
                chain, checks, task_target = autotask_exec(task, model, env_eval)

                task_result = {
                    'actions': chain,
                    'agent_check': checks[0],
                    'env_check': checks[1],
                    'group': group,
                    'task_num': task_num,
                    'task_target': task_target,
                    'task_difficulty': task['total_difficulty'],
                    'task_type': task_type
                }
                tasks_run_data[task_index] = task_result

    return tasks_run_data