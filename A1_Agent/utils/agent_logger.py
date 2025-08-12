import datetime
import os
from pathlib import Path
from loguru import logger


class AgentLogger:
    """
    Logger class for agent operations with file and console output.
    
    This class provides logging functionality for agent operations, including
    task decomposition steps, plan logging, and general agent activity.
    It supports both file logging and optional console output.
    """

    LOG_DIRECTORY = Path('./agent_logs').resolve()

    def __init__(self, console_verbose: bool = False) -> None:
        """
        Initialize the AgentLogger with console verbosity setting.
        
        Args:
            console_verbose: Whether to print log messages to console in addition to file
        """
        self._initialize_log_directory()
        self.console_verbose = console_verbose
        self.log_started = False

    def print_console(self, text: str) -> None:
        """
        Print text to console if console_verbose is enabled.
        
        Args:
            text: Text to print to console
        """
        if self.console_verbose:
            print(text)

    def _initialize_log_directory(self) -> None:
        """
        Initialize the log directory structure.
        
        Creates the log directory if it doesn't exist and sets up
        the relative path for log file storage.
        """
        os.makedirs(self.LOG_DIRECTORY, exist_ok=True)


    def start_logger(self) -> None:
        """
        Start the logging system with timestamped log file.
        
        Creates a new log file with timestamp in the filename and
        configures the logger to write to this file. Only starts
        once per logger instance.
        """
        if self.log_started: return
        timestamp = datetime.datetime.now().strftime("%Y-%m-%d_%H-%M-%S")
        file_name = f'{timestamp}.log'
        file_path = self.LOG_DIRECTORY / file_name
        logger.remove()
        logger.add(file_path, format='[{time:HH:mm:ss}]: {message}')
        self.log_started = True

    @staticmethod
    def stop_logger() -> None:
        """
        Stop the logging system.
        
        Removes all logger handlers to stop logging operations.
        """
        logger.remove()

    def log(self, message: str) -> None:
        """
        Log a message to both file and console (if enabled).
        
        Args:
            message: Message to log
        """
        getattr(logger, 'info')(message)
        self.print_console(message)

    def decomposition_step_mark(self,decomposition_step: str, finished: bool = False) -> None:
        """
        Log a decomposition step marker with visual formatting.
        
        Creates a visually distinct log entry to mark the beginning
        or end of a decomposition step.
        
        Args:
            decomposition_step: Name of the decomposition step
            finished: Whether this marks the end of the step (True) or beginning (False)
        """
        text = ''
        if not finished:
            text = '#'*30 + f' {decomposition_step} started '  + '#'*30 + '\n'
        else:
            text = '#' * 30 + f' {decomposition_step} ended ' + '#' * 30 + '\n'
        self.log(text)


    def log_plan(self, plan, level) -> None:
        """
        Log a plan with detailed information and formatting.
        
        Extracts and logs plan information including subtasks, critique,
        and plan status with proper formatting.
        
        Args:
            plan: Dictionary containing plan information
            level: Log level for the plan (e.g., 'info', 'debug')
        """

        if 'subtasks' in plan:
            plan_text = plan['subtasks']
        elif 'previous_plan' in plan:
            plan_text = plan['previous_plan']
        else:
            plan_text = f'Failed to read subtasks \n Data: {plan}'

        if 'critique' not in plan:
            plan_critique = 'Critique not available for this plan'
        else:
            plan_critique = plan['critique']
        if 'is_ok' not in plan:
            plan_passed = 'Failed to read plan status'
        else:
            plan_passed = plan['is_ok']
        log_text = f'''
        Current plan ({level}):
        {plan_text}
        Plan critique (last known): 
        {plan_critique}
        PLAN PASSED:
        {plan_passed}
        '''
        getattr(logger, 'info')(log_text)
        self.print_console(log_text)
