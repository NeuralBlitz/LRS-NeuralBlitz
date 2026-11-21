#!/usr/bin/env python3

from flask import Flask, render_template_string, request, jsonify
import time
import json

app = Flask(__name__)

# Simple HTML template
HTML_TEMPLATE = """
<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>OpenCode LRS Pattern Count Demo Hub</title>
    <script src="https://cdn.tailwindcss.com"></script>
</head>
<body class="bg-gray-50 min-h-screen">
    <div class="max-w-6xl mx-auto p-8">
        <div class="text-center mb-8">
            <h1 class="text-4xl font-bold text-gray-900 mb-4">🧠 OpenCode LRS Pattern Count Demo Hub</h1>
            <p class="text-xl text-gray-600 mb-6">Prototype text-pattern counter — no AI model or benchmark</p>
            <div class="flex justify-center space-x-4 mb-8">
                <div class="bg-purple-100 text-purple-800 px-4 py-2 rounded-full text-sm font-medium">Unbenchmarked demonstration</div>
                <div class="bg-blue-100 text-blue-800 px-4 py-2 rounded-full text-sm font-medium">Pattern Count Demo</div>
                <div class="bg-green-100 text-green-800 px-4 py-2 rounded-full text-sm font-medium">On-demand keyword counts</div>
            </div>
        </div>

        <div class="grid grid-cols-1 lg:grid-cols-2 gap-8">
            <div class="bg-white rounded-lg shadow-lg p-6">
                <h2 class="text-2xl font-semibold text-gray-900 mb-4">📝 Code Analysis</h2>
                <p class="text-gray-600 mb-4">Paste your Python, JavaScript, or Java code below for AI analysis.</p>

                <textarea id="codeInput" rows="15" class="w-full p-4 border border-gray-300 rounded-lg font-mono text-sm focus:ring-2 focus:ring-purple-500 focus:border-transparent" placeholder="# Enter your code here for cognitive analysis...
def fibonacci(n):
    if n <= 1:
        return n
    return fibonacci(n-1) + fibonacci(n-2)

# The AI will analyze patterns, performance, and provide insights!"></textarea>

                <div class="mt-6 flex space-x-4">
                    <button onclick="analyzeCode()" class="bg-purple-600 hover:bg-purple-700 text-white px-6 py-3 rounded-lg font-medium transition duration-200 flex items-center">
                        <span class="mr-2">🧠</span> Analyze with Pattern Count Demo
                    </button>
                    <button onclick="clearCode()" class="bg-gray-600 hover:bg-gray-700 text-white px-4 py-3 rounded-lg font-medium transition duration-200">Clear</button>
                    <button onclick="loadSample()" class="bg-blue-600 hover:bg-blue-700 text-white px-4 py-3 rounded-lg font-medium transition duration-200">Load Sample</button>
                </div>
            </div>

            <div class="bg-white rounded-lg shadow-lg p-6">
                <h2 class="text-2xl font-semibold text-gray-900 mb-4">🎯 AI Insights</h2>

                <div class="mb-6 p-4 bg-gradient-to-r from-purple-50 to-blue-50 rounded-lg">
                    <div class="flex items-center justify-between">
                        <div class="flex items-center space-x-2">
                            <div id="statusIndicator" class="w-3 h-3 bg-gray-400 rounded-full"></div>
                            <span id="statusText" class="text-sm font-medium text-gray-700">Ready for analysis</span>
                        </div>
                        <div class="text-right">
                            <div class="text-xs text-gray-500">Analysis Time</div>
                            <div id="analysisTime" class="text-sm font-medium text-green-600">-- ms</div>
                        </div>
                    </div>
                </div>

                <div class="mb-6 grid grid-cols-2 gap-4">
                    <div class="bg-blue-50 p-3 rounded-lg text-center">
                        <div id="linesAnalyzed" class="text-lg font-bold text-blue-600">--</div>
                        <div class="text-xs text-blue-700">Lines Analyzed</div>
                    </div>
                    <div class="bg-green-50 p-3 rounded-lg text-center">
                        <div id="patternsFound" class="text-lg font-bold text-green-600">--</div>
                        <div class="text-xs text-green-700">Patterns Found</div>
                    </div>
                </div>

                <div id="resultsContainer">
                    <div class="text-center text-gray-500 py-12">
                        <div class="text-6xl mb-4">🧠</div>
                        <h3 class="text-lg font-medium mb-2">Ready for pattern counting</h3>
                        <p class="text-sm">Enter code and click "Analyze with Pattern Count Demo" to see literal keyword counts without AI inference.</p>
                    </div>
                </div>
            </div>
        </div>

        <div class="mt-8 bg-blue-50 rounded-lg p-6">
            <h2 class="text-2xl font-semibold text-gray-900 mb-3">What this demo actually does</h2>
            <p class="text-sm text-gray-700">This is a local keyword-count demonstration, not AI inference, code-quality assessment, benchmark proof, authentication, or production deployment.</p>
            <p class="text-sm text-gray-700 mt-2">The server counts a few literal programming tokens and measures only the time needed for those counts. Results may be inaccurate for comments, strings, or other programming languages.</p>
        </div>
    </div>

    <script>
        async function analyzeCode() {
            const code = document.getElementById('codeInput').value;
            if (!code.trim()) {
                alert('Please enter code to count');
                return;
            }
            document.getElementById('statusIndicator').className = 'w-3 h-3 bg-yellow-500 rounded-full';
            document.getElementById('statusText').textContent = 'Counting text patterns...';
            try {
                const response = await fetch('/api/analyze', {
                    method: 'POST',
                    headers: { 'Content-Type': 'application/json' },
                    body: JSON.stringify({ code: code })
                });
                const result = await response.json();
                if (!response.ok || result.success !== true) {
                    throw new Error(result.error || 'Request failed');
                }
                displayAnalysisResults(result);
            } catch (error) {
                document.getElementById('statusIndicator').className = 'w-3 h-3 bg-red-500 rounded-full';
                document.getElementById('statusText').textContent = 'Pattern count failed';
                document.getElementById('resultsContainer').textContent = String(error);
            }
        }

        function displayAnalysisResults(result) {
            document.getElementById('statusIndicator').className = 'w-3 h-3 bg-green-500 rounded-full';
            document.getElementById('statusText').textContent = 'Keyword counting complete';
            document.getElementById('analysisTime').textContent = String(result.analysis_time_ms) + ' ms';
            document.getElementById('linesAnalyzed').textContent = String(result.lines_analyzed);
            document.getElementById('patternsFound').textContent = String(result.patterns_found);

            // Never interpret server or user text as HTML.
            const container = document.getElementById('resultsContainer');
            container.replaceChildren();
            const heading = document.createElement('h3');
            heading.textContent = 'Text-only pattern counts (not AI inference)';
            const note = document.createElement('p');
            note.textContent = 'Counts can include comments and string literals; no correctness, speedup or code quality is claimed.';
            const list = document.createElement('ul');
            for (const pair of Object.entries(result.insights || {})) {
                const item = document.createElement('li');
                item.textContent = pair[0] + ': ' + String(pair[1]);
                list.appendChild(item);
            }
            container.append(heading, note, list);
        }

        function clearCode() {
            document.getElementById('codeInput').value = '';
            document.getElementById('resultsContainer').innerHTML = `
                <div class="text-center text-gray-500 py-12">
                    <div class="text-6xl mb-4">🧠</div>
                    <h3 class="text-lg font-medium mb-2">Ready for pattern counting</h3>
                    <p class="text-sm">Enter code and click "Analyze with Pattern Count Demo" to see approximate keyword counts.</p>
                </div>
            `;
            document.getElementById('statusIndicator').className = 'w-3 h-3 bg-gray-400 rounded-full';
            document.getElementById('statusText').textContent = 'Ready for analysis';

            // Reset metrics
            document.getElementById('analysisTime').textContent = '-- ms';
            document.getElementById('linesAnalyzed').textContent = '--';
            document.getElementById('patternsFound').textContent = '--';
        }

        function loadSample() {
            const sampleCode = `import asyncio
import json
from typing import List, Dict, Optional
from dataclasses import dataclass

@dataclass
class Task:
    id: int
    title: str
    completed: bool = False
    priority: str = "medium"

class TaskManager:
    def __init__(self):
        self.tasks: Dict[int, Task] = {}
        self.next_id = 1

    def add_task(self, title: str, priority: str = "medium") -> Task:
        task = Task(id=self.next_id, title=title, priority=priority)
        self.tasks[self.next_id] = task
        self.next_id += 1
        return task

    def get_task(self, task_id: int) -> Optional[Task]:
        return self.tasks.get(task_id)

    def complete_task(self, task_id: int) -> bool:
        task = self.tasks.get(task_id)
        if task:
            task.completed = True
            return True
        return False

    def get_pending_tasks(self) -> List[Task]:
        return [task for task in self.tasks.values() if not task.completed]

    def get_high_priority_tasks(self) -> List[Task]:
        return [task for task in self.tasks.values()
                if task.priority == "high" and not task.completed]

# Example usage
if __name__ == "__main__":
    manager = TaskManager()

    # Add some tasks
    task1 = manager.add_task("Review code changes", "high")
    task2 = manager.add_task("Update documentation", "medium")
    task3 = manager.add_task("Run tests", "high")

    # Complete a task
    manager.complete_task(1)

    # Get pending tasks
    pending = manager.get_pending_tasks()
    print(f"Pending tasks: {len(pending)}")

    # Get high priority tasks
    urgent = manager.get_high_priority_tasks()
    print(f"Urgent tasks: {len(urgent)}")`;

            document.getElementById('codeInput').value = sampleCode;
        }

        // Initialize status
        document.addEventListener('DOMContentLoaded', function() {
            document.getElementById('statusText').textContent = 'Ready for analysis';
        });
    </script>
</body>
</html>
"""

@app.route('/')
def home():
    return render_template_string(HTML_TEMPLATE)

@app.route('/api/analyze', methods=['POST'])
def analyze():
    """Demonstrate literal token counting without making AI accuracy claims."""
    data = request.get_json(silent=True)
    if not isinstance(data, dict) or not isinstance(data.get('code'), str):
        return jsonify({'success': False, 'error': 'A JSON string code field is required'}), 400
    code = data['code']
    if len(code) > 200_000:
        return jsonify({'success': False, 'error': 'Code input too large'}), 413

    start = time.perf_counter()
    counts = {
        'functions': code.count('def '),
        'classes': code.count('class '),
        'conditionals': code.count('if ') + code.count('elif '),
        'loops': code.count('for ') + code.count('while '),
    }
    duration_ms = (time.perf_counter() - start) * 1000
    return jsonify({
        'success': True,
        'method': 'unvalidated literal text pattern counts',
        'analysis_time_ms': round(duration_ms, 3),
        'lines_analyzed': len(code.splitlines()),
        'patterns_found': sum(counts.values()),
        'insights': counts,
        'limitations': 'Not an AI inference, parser, correctness result or benchmark',
    })


if __name__ == '__main__':
    # Experimental local demo only; never enable Flask's debugger by default.
    app.run(host='127.0.0.1', port=8080, debug=False)
