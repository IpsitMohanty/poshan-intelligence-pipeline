import os
import ast
from pathlib import Path
import json

PROJECT_ROOT = Path(__file__).parent
REPORT_PATH = PROJECT_ROOT / "project_report.md"
GRAPH_PATH = PROJECT_ROOT / "dependency_graph.json"


def analyze_python_file(file_path):
    """Extract imports, functions, and class names from a Python file."""
    try:
        tree = ast.parse(file_path.read_text(encoding="utf-8"))
    except Exception:
        return {"imports": [], "functions": [], "classes": []}

    imports, functions, classes = [], [], []

    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            imports.extend([alias.name for alias in node.names])

        elif isinstance(node, ast.ImportFrom):
            if node.module:
                imports.append(node.module)

        elif isinstance(node, ast.FunctionDef):
            functions.append(node.name)

        elif isinstance(node, ast.ClassDef):
            classes.append(node.name)

    return {
        "imports": sorted(set(imports)),
        "functions": functions,
        "classes": classes,
    }


def scan_project(root: Path):
    project_info = {}
    dependency_graph = {}

    for path, dirs, files in os.walk(root):
        folder = Path(path)
        rel_folder = folder.relative_to(root)
        project_info[str(rel_folder)] = []

        for file in files:
            file_path = folder / file

            if file_path.suffix == ".py":
                analysis = analyze_python_file(file_path)
                project_info[str(rel_folder)].append({
                    "file": file,
                    "type": "python",
                    "imports": analysis["imports"],
                    "functions": analysis["functions"],
                    "classes": analysis["classes"]
                })

                dependency_graph[file] = analysis["imports"]

            else:
                project_info[str(rel_folder)].append({
                    "file": file,
                    "type": "other"
                })

    return project_info, dependency_graph


def generate_markdown_report(project_info):
    """Write a Markdown file summarizing the project structure."""
    lines = ["# 📦 Project Structure Report — poshan_intelligence\n"]

    for folder, files in project_info.items():
        lines.append(f"\n## 📁 Folder: `{folder}`\n")

        if not files:
            lines.append("_No files_\n")
            continue

        for info in files:
            if info["type"] == "python":
                lines.append(f"### `{info['file']}`\n")
                lines.append("**Imports:** " + ", ".join(info["imports"]) + "\n")
                lines.append("**Functions:** " + ", ".join(info["functions"]) + "\n")
                lines.append("**Classes:** " + ", ".join(info["classes"]) + "\n")
            else:
                lines.append(f"### `{info['file']}` (non-python file)\n")

    REPORT_PATH.write_text("\n".join(lines), encoding="utf-8")
    print(f"✔ Report generated: {REPORT_PATH}")


def save_dependency_graph(graph):
    GRAPH_PATH.write_text(json.dumps(graph, indent=4), encoding="utf-8")
    print(f"✔ Dependency graph saved: {GRAPH_PATH}")


if __name__ == "__main__":
    print("🔍 Scanning project…")

    project_info, dependency_graph = scan_project(PROJECT_ROOT)

    print("📄 Generating Markdown report…")
    generate_markdown_report(project_info)

    print("🔗 Saving dependency graph…")
    save_dependency_graph(dependency_graph)

    print("\n✨ Completed! Open `project_report.md` to explore the full analysis.")
