#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Command Line Monitor Tool - Records command execution and generates AI-powered reports
"""

import argparse
import subprocess
import sys
import time
import logging
import openai
import json
import threading
import datetime
import os
from typing import Tuple, Optional

# Configure logging settings
def get_daily_log_handler():
    """Create a daily rotating log handler"""
    today = datetime.datetime.now().strftime('%Y-%m-%d')
    return logging.FileHandler(f'logs/cmdmon-{today}.log', encoding='utf-8')

if not os.path.exists('logs'):
    os.makedirs('logs')

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        get_daily_log_handler()
    ]
)

class CmdMonitor:
    """Main class for monitoring command execution and generating reports"""
    
    def __init__(self, config_path: str = 'config.json'):
        """Initialize the monitor with configuration"""
        self.config = self._load_config(config_path)
        self.client = openai.OpenAI(
            api_key=self.config['openai']['api_key'],
            base_url=self.config['openai'].get('base_url', 'https://api.openai.com/v1')
        )
        self.model = self.config['openai'].get('model', 'gpt-4o')
        
    def _load_config(self, path: str) -> dict:
        """Load configuration from JSON file"""
        try:
            with open(path, 'r') as f:
                return json.load(f)
        except FileNotFoundError:
            logging.error(f"Config file {path} not found")
            raise
        except json.JSONDecodeError:
            logging.error(f"Config file {path} has invalid JSON format")
            raise
    
    def execute_command(self, command: str) -> Tuple[float, str, str, int]:
        """
        Execute a shell command and return:
        - execution time
        - stdout output
        - stderr output
        - return code
        """
        start_time = time.time()
        
        stdout_log = []
        stderr_log = []
        
        use_pipes = not any(cmd in command.lower() for cmd in ['python', 'cmd', 'powershell'])
        
        process = subprocess.Popen(
            command,
            shell=True,
            encoding='gbk',  # 使用gbk编码处理中文输出
            errors='replace',
            stdout=subprocess.PIPE if use_pipes else None,
            stderr=subprocess.PIPE if use_pipes else None,
            stdin=sys.stdin,
            universal_newlines=True
        )
        
        if use_pipes and process.stdout and process.stderr:
            def handle_stream(stream, output_type, log_list):
                try:
                    for line in iter(stream.readline, ''):
                        if line:
                            if output_type == 'stdout':
                                sys.stdout.write(line)
                                sys.stdout.flush()
                            else:
                                sys.stderr.write(line)
                                sys.stderr.flush()
                            log_list.append(line)
                except (AttributeError, ValueError):
                    pass
            
            out_thread = threading.Thread(target=handle_stream, args=(process.stdout, 'stdout', stdout_log))
            err_thread = threading.Thread(target=handle_stream, args=(process.stderr, 'stderr', stderr_log))
            out_thread.daemon = True
            err_thread.daemon = True
            out_thread.start()
            err_thread.start()
        try:
            process.wait()
            if use_pipes and process.stdout and process.stderr:
                out_thread.join()
                err_thread.join()
        except KeyboardInterrupt:
            process.terminate()
            if use_pipes and process.stdout and process.stderr:
                out_thread.join()
                err_thread.join()
            raise
        
        end_time = time.time()
        execution_time = end_time - start_time
        
        return_code = process.returncode or 0
        
        if return_code != 0:
            logging.error(f"Command failed with return code: {return_code}")
        
        output = ''.join(stdout_log)
        error = ''.join(stderr_log)
        
        end_time = time.time()
        execution_time = end_time - start_time
        
        return_code = process.returncode or 0
        
        if return_code != 0:
            logging.error(f"Command failed with return code: {return_code}")
        
        return execution_time, output, error, return_code
    
    def summarize_with_gpt(self, text: str) -> Optional[str]:
        """Use GPT to summarize the given text"""
        try:
            response = self.client.chat.completions.create(
                model=self.model,
                messages=[
                    {"role": "system", "content": "You are a command line execution analysis assistant. Please summarize the following content concisely."},
                    {"role": "user", "content": text}
                ],
                max_tokens=500
            )
            return response.choices[0].message.content
        except Exception as e:
            logging.error(f"OpenAI API call failed: {e}")
            return None
    
    def send_pushdeer(self, title: str, content: str) -> bool:
        """Send notification via PushDeer"""
        try:
            import requests
            url = "https://api2.pushdeer.com/message/push"
            params = {
                "pushkey": self.config['pushdeer']['pushkey'],
                "text": title,
                "desp": content,
                "type": "markdown"
            }
            response = requests.get(url, params=params)
            return response.json().get('code') == 0
        except Exception as e:
            logging.error(f"Failed to send PushDeer notification: {e}")
            return False
    
    def run(self, command: str, pushkey: str = None):
        """Main execution flow for monitoring a command"""
        start_time = time.time()
        logging.info(f"Executing command: {command}")
        
        # Execute the command
        exec_time, output, error, return_code = self.execute_command(command)
        end_time = time.time()
        
        # Basic report content
        basic_report = f"""

Command: {command}
Start time: {time.strftime('%Y-%m-%d %H:%M:%S', time.localtime(start_time))}
End time: {time.strftime('%Y-%m-%d %H:%M:%S', time.localtime(end_time))}
Execution time: {exec_time:.2f} seconds
Return code: {return_code}
"""

        output_report = f"""

Standard output:
{output}

Standard error:
{error}

"""

        full_report = basic_report + output_report
        
        # AI analysis based on configuration
        if self.config['features'].get('enable_ai', True):
            summary = self.summarize_with_gpt(full_report)
            if summary:
                full_report = f"\nAI Summary:\n{summary}" + full_report
        
        # Log results
        try:
            if self.config['features'].get('enable_ai', True) or self.config['features'].get('enable_email', True):
                logging.info(f"Command execution completed\n{full_report.encode('utf-8', errors='replace').decode('utf-8')}")
            else:
                logging.info(f"Command execution completed\n{basic_report.encode('utf-8', errors='replace').decode('utf-8')}")
        except UnicodeError:
            logging.info("Command execution completed (output contains non-UTF8 characters)")
        
        # Push notification based on configuration
        if self.config['features'].get('enable_push', True):
            title = f"Command Execution Report: {command[:50]}"
            report_content = full_report if self.config['features'].get('enable_ai', True) else basic_report
            if self.send_pushdeer(title, report_content):
                logging.info("Push notification sent successfully")
            else:
                logging.warning("Failed to send push notification")

def main():
    """Main entry point for the command line interface"""
    parser = argparse.ArgumentParser(
        description='Command Line Monitor - Records command execution with AI-powered reporting',
        add_help=False
    )
    parser.add_argument(
        'command',
        type=str,
        nargs=argparse.REMAINDER,
        help='Command to execute'
    )
    parser.add_argument(
        '--pushkey',
        type=str,
        help='PushDeer pushkey to receive the report'
    )
    parser.add_argument(
        '--config',
        type=str,
        default='config.json',
        help='Path to config file (default: config.json)'
    )
    
    args = parser.parse_args()
    
    try:
        monitor = CmdMonitor(args.config)
        if not args.command:
            parser.print_help()
            exit(1)
        command = ' '.join(args.command)
        monitor.run(command, args.pushkey)
    except Exception as e:
        logging.error(f"Runtime error: {e}")
        sys.exit(1)

if __name__ == '__main__':
    main()